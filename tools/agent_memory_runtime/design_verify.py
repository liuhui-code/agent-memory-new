# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .architecture_slice import build_architecture_slice
from .design_check import check_design_proposal, load_proposal, path_from_node_id
from .design_protocol import load_contract, load_rules
from .impact_scope import resolve_changed_files, unique_preserved_paths
from .records import output
from .storage import ensure_initialized, resolve_project


def design_verify_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    proposal = load_proposal(Path(args.proposal))
    contract = load_contract(args.contract, proposal["goal"])
    rules = load_rules(args.rules)
    actual = resolve_changed_files(project, args.base, args.files, args.diff_file)
    payload = verify_design(project, proposal, contract, rules, actual, args.executed_tests or [])
    output(payload, args.json)


def verify_design(
    project: Any,
    proposal: dict[str, Any],
    contract: dict[str, Any],
    rules: list[dict[str, Any]],
    actual_files: list[str],
    executed_tests: list[str] | None = None,
) -> dict[str, Any]:
    evaluation = check_design_proposal(project, proposal, contract, rules)
    planned = planned_change_paths(proposal)
    actual = unique_preserved_paths(actual_files)
    planned_set, actual_set = set(planned), set(actual)
    matched = sorted(planned_set & actual_set)
    missing = sorted(planned_set - actual_set)
    unexpected = sorted(actual_set - planned_set)
    recall = 1.0 if not planned else len(matched) / len(planned_set)
    extra_ratio = 0.0 if not actual else len(unexpected) / len(actual_set)
    test_paths = [path for path in actual if is_test_path(path)]
    required_tests = proposal["verification"]["tests"]
    executed_tests = executed_tests or []
    graph_alignment = compare_learned_graph(project, proposal, contract, planned + actual)
    triggers = []
    if missing:
        triggers.append("planned_changes_missing")
    if unexpected:
        triggers.append("unplanned_files_changed")
    if evaluation["errors"]:
        triggers.append("architecture_gate_failed")
    if required_tests and not test_paths and not executed_tests:
        triggers.append("declared_tests_not_executed_or_visible_in_diff")
    if graph_alignment["status"] == "mismatch":
        triggers.append("refresh_learned_scope_or_replan")
    status = "replan" if triggers else "aligned"
    return {
        "schema_version": "design-verification/v1",
        "project_id": project.project_id,
        "candidate_id": proposal["id"],
        "contract_id": contract["id"],
        "status": status,
        "planned_files": planned,
        "actual_files": actual,
        "matched_files": matched,
        "missing_planned_files": missing,
        "unexpected_files": unexpected,
        "metrics": {
            "planned_file_recall": round(recall, 4),
            "unplanned_file_ratio": round(extra_ratio, 4),
            "architecture_error_count": len(evaluation["errors"]),
            "architecture_warning_count": len(evaluation["warnings"]),
        },
        "verification": {
            "declared_tests": required_tests,
            "executed_tests": executed_tests,
            "changed_test_files": test_paths,
            "declared_observability": proposal["verification"]["observability"],
            "replan_triggers": triggers,
        },
        "graph_alignment": graph_alignment,
        "design_evaluation": evaluation,
        "audit": {"persisted": False, "llm_used": False},
    }


def compare_learned_graph(
    project: Any,
    proposal: dict[str, Any],
    contract: dict[str, Any],
    paths: list[str],
) -> dict[str, Any]:
    structural = bool(proposal["add_nodes"] or proposal["add_edges"] or proposal["remove_edges"])
    if not structural:
        return {"status": "not_applicable", "missing_nodes": [], "missing_edges": [], "remaining_removed_edges": []}
    architecture = build_architecture_slice(project, [], contract["goal"], explicit_paths=paths)
    current_nodes = {node["id"] for node in architecture["nodes"]}
    current_edges = {
        (edge["source"], edge["relation"], edge["target"])
        for edge in architecture["edges"]
    }
    missing_nodes = sorted(str(node["id"]) for node in proposal["add_nodes"] if str(node["id"]) not in current_nodes)
    missing_edges = [edge for edge in proposal["add_edges"] if edge_tuple(edge) not in current_edges]
    remaining = [edge for edge in proposal["remove_edges"] if edge_tuple(edge) in current_edges]
    mismatch = bool(missing_nodes or missing_edges or remaining)
    return {
        "status": "mismatch" if mismatch else "aligned",
        "missing_nodes": missing_nodes,
        "missing_edges": missing_edges,
        "remaining_removed_edges": remaining,
        "evidence_gaps": architecture["evidence_gaps"],
        "action": "refresh the changed learned scope before treating absence as implementation failure" if mismatch else None,
    }


def edge_tuple(edge: dict[str, Any]) -> tuple[str, str, str]:
    return str(edge["source"]), str(edge["relation"]), str(edge["target"])


def planned_change_paths(proposal: dict[str, Any]) -> list[str]:
    paths = [path_from_node_id(node_id) for node_id in proposal["modify_nodes"]]
    paths.extend(
        str(node.get("file_path") or path_from_node_id(str(node["id"])) or "")
        for node in proposal["add_nodes"]
    )
    return unique_preserved_paths([path for path in paths if path])


def is_test_path(path: str) -> bool:
    value = path.lower()
    return "test" in value or "spec" in value
