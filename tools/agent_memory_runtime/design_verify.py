# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .architecture_slice import build_architecture_slice, unique_paths
from .design_check import check_design_proposal, load_proposal, path_from_node_id, proposal_paths
from .design_coverage import evaluate_coverage
from .design_protocol import DELTA_SCHEMA_V2, apply_intent_to_contract, load_contract, load_intent, load_rules
from .design_verification_evidence import (
    failed_test_count,
    load_test_evidence,
    normalize_symbol_values,
    verified_refs,
)
from .graph_quality_snapshot import load_graph_revision
from .impact_scope import resolve_changed_files, unique_preserved_paths
from .records import output
from .repository_model import architecture_from_model, build_repository_model
from .storage import connect, ensure_initialized, resolve_project


def design_verify_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    proposal = load_proposal(Path(args.proposal))
    contract = load_contract(args.contract, proposal["goal"])
    intent = load_intent(getattr(args, "intent", None), contract["goal"])
    rules = load_rules(args.rules)
    actual = resolve_changed_files(project, args.base, args.files, args.diff_file)
    tests = load_test_evidence(getattr(args, "test_evidence", None), args.executed_tests or [])
    symbols = normalize_symbol_values(getattr(args, "actual_symbols", None))
    payload = verify_design(project, proposal, contract, rules, actual, args.executed_tests or [], symbols, tests, intent)
    output(payload, args.json)


def verify_design(
    project: Any,
    proposal: dict[str, Any],
    contract: dict[str, Any],
    rules: list[dict[str, Any]],
    actual_files: list[str],
    executed_tests: list[str] | None = None,
    actual_symbols: list[str] | None = None,
    test_evidence: dict[str, Any] | None = None,
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intent = intent or load_intent(None, contract["goal"])
    contract = apply_intent_to_contract(contract, intent)
    scope_paths = unique_paths([*proposal_paths(proposal), *intent["scope"]])
    repository_model = build_repository_model(project, intent["goal"], scope_paths)
    architecture = architecture_from_model(repository_model)
    evaluation = check_design_proposal(
        project,
        proposal,
        contract,
        rules,
        architecture,
        repository_model=repository_model,
        intent=intent,
    )
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
    actual_symbols = actual_symbols or []
    test_evidence = test_evidence or load_test_evidence(None, executed_tests)
    planned_symbols = sorted(node for node in proposal["modify_nodes"] if node.startswith("symbol:"))
    matched_symbols = sorted(set(planned_symbols) & set(actual_symbols))
    missing_symbols = sorted(set(planned_symbols) - set(actual_symbols)) if actual_symbols else []
    symbol_recall = 1.0 if not planned_symbols else len(matched_symbols) / len(planned_symbols) if actual_symbols else 0.0
    coverage = evaluate_coverage(
        proposal,
        contract,
        architecture,
        verified_refs(test_evidence),
    )
    failed_tests = failed_test_count(test_evidence)
    graph_alignment = compare_learned_graph(project, proposal, contract, planned + actual, architecture)
    with connect(project) as conn:
        current_revision = load_graph_revision(conn, project.project_id)
    baseline_revision = int(evaluation["baseline_revision"])
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
    if current_revision != baseline_revision:
        triggers.append("baseline_revision_changed")
    if failed_tests:
        triggers.append("structured_test_failed")
    if actual_symbols and missing_symbols:
        triggers.append("planned_symbols_missing")
    if proposal["schema_version"] == DELTA_SCHEMA_V2 and any(
        item["coverage_state"] != "verified" for item in coverage["quality_scenarios"]
    ):
        triggers.append("quality_scenario_not_verified")
    status = "replan" if triggers else "aligned"
    return {
        "schema_version": "design-verification/v2" if proposal["schema_version"] == DELTA_SCHEMA_V2 else "design-verification/v1",
        "project_id": project.project_id,
        "candidate_id": proposal["id"],
        "contract_id": contract["id"],
        "baseline_revision": baseline_revision,
        "current_revision": current_revision,
        "status": status,
        "planned_files": planned,
        "actual_files": actual,
        "matched_files": matched,
        "missing_planned_files": missing,
        "unexpected_files": unexpected,
        "planned_symbols": planned_symbols,
        "actual_symbols": actual_symbols,
        "matched_symbols": matched_symbols,
        "missing_planned_symbols": missing_symbols,
        "metrics": {
            "planned_file_recall": round(recall, 4),
            "unplanned_file_ratio": round(extra_ratio, 4),
            "architecture_error_count": len(evaluation["errors"]),
            "architecture_warning_count": len(evaluation["warnings"]),
            "planned_symbol_recall": round(symbol_recall, 4),
            "scenario_verification_rate": verification_rate(coverage["quality_scenarios"]),
            "failed_test_count": failed_tests,
        },
        "verification": {
            "declared_tests": required_tests,
            "executed_tests": executed_tests,
            "test_evidence": test_evidence["tests"],
            "changed_test_files": test_paths,
            "declared_observability": proposal["verification"]["observability"],
            "replan_triggers": triggers,
        },
        "graph_alignment": graph_alignment,
        "quality_scenarios": coverage["quality_scenarios"],
        "verification_capabilities": verification_capabilities(actual_symbols, test_evidence),
        "design_evaluation": evaluation,
        "audit": {"persisted": False, "llm_used": False},
    }


def verification_rate(items: list[dict[str, Any]]) -> float:
    if not items:
        return 1.0
    return round(sum(1 for item in items if item["coverage_state"] == "verified") / len(items), 4)


def verification_capabilities(actual_symbols: list[str], test_evidence: dict[str, Any]) -> list[str]:
    capabilities = ["file_delta", "graph_alignment"]
    if actual_symbols:
        capabilities.append("symbol_delta")
    if test_evidence["source"] == "structured":
        capabilities.append("structured_tests")
    return capabilities


def compare_learned_graph(
    project: Any,
    proposal: dict[str, Any],
    contract: dict[str, Any],
    paths: list[str],
    architecture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    structural = bool(proposal["add_nodes"] or proposal["add_edges"] or proposal["remove_edges"])
    if not structural:
        return {"status": "not_applicable", "missing_nodes": [], "missing_edges": [], "remaining_removed_edges": []}
    architecture = architecture or build_architecture_slice(project, [], contract["goal"], explicit_paths=paths)
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
