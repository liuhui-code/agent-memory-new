# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from .architecture_slice import DEPENDENCY_RELATIONS, infer_layer, unique_paths
from .design_change_plan import build_change_plan
from .design_coverage import evaluate_coverage
from .design_dimensions import evaluate_dimensions
from .design_fitness import evaluate_rules
from .design_protocol import (
    CONTRACT_SCHEMA_V2,
    DELTA_SCHEMA_V2,
    EVALUATION_SCHEMA,
    EVALUATION_SCHEMA_V2,
    apply_intent_to_contract,
    load_contract,
    load_intent,
    load_rules,
    normalize_delta_metadata,
)
from .design_synthesis import build_synthesis_brief
from .models import Project
from .records import output
from .repository_model import architecture_from_model, build_repository_model, public_repository_model
from .storage import ensure_initialized, resolve_project


REQUIRED_LISTS = (
    "anchors", "add_nodes", "modify_nodes", "add_edges", "remove_edges",
    "assumptions", "invariants",
)
EDGE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def design_check_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    proposal = load_proposal(Path(args.proposal))
    contract = load_contract(getattr(args, "contract", None), proposal["goal"])
    intent = load_intent(getattr(args, "intent", None), contract["goal"])
    rules = load_rules(getattr(args, "rules", None))
    payload = check_design_proposal(project, proposal, contract, rules, intent=intent)
    output(payload, args.json)


def load_proposal(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"unable to read design proposal: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"design proposal is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("design proposal must be a JSON object")
    return validate_proposal(value)


def validate_proposal(value: dict[str, Any]) -> dict[str, Any]:
    goal = value.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        raise SystemExit("design proposal requires a non-empty goal")
    proposal = dict(value)
    for field in REQUIRED_LISTS:
        current = proposal.get(field, [])
        if not isinstance(current, list):
            raise SystemExit(f"design proposal field must be a list: {field}")
        proposal[field] = current
    validate_string_list(proposal, "anchors")
    validate_string_list(proposal, "modify_nodes")
    validate_string_list(proposal, "assumptions")
    validate_string_list(proposal, "invariants")
    for field in ("anchors", "modify_nodes"):
        for index, node_id in enumerate(proposal[field]):
            path = path_from_node_id(node_id)
            if path:
                validate_relative_path(path, f"{field}[{index}]")
    seen: set[str] = set()
    for index, node in enumerate(proposal["add_nodes"]):
        if not isinstance(node, dict):
            raise SystemExit(f"add_nodes[{index}] must be an object")
        node_id = node.get("id")
        kind = node.get("kind")
        if not isinstance(node_id, str) or not node_id.strip() or not isinstance(kind, str) or not kind.strip():
            raise SystemExit(f"add_nodes[{index}] requires string id and kind")
        if node_id in seen:
            raise SystemExit(f"duplicate added node id: {node_id}")
        seen.add(node_id)
        if node.get("file_path") is not None:
            validate_relative_path(str(node["file_path"]), f"add_nodes[{index}].file_path")
    for field in ("add_edges", "remove_edges"):
        for index, edge in enumerate(proposal[field]):
            validate_edge(edge, f"{field}[{index}]")
    return normalize_delta_metadata(proposal)


def validate_string_list(proposal: dict[str, Any], field: str) -> None:
    if not all(isinstance(item, str) and item.strip() for item in proposal[field]):
        raise SystemExit(f"design proposal field requires non-empty strings: {field}")


def validate_relative_path(value: str, field: str) -> None:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"{field} must stay inside the project")


def validate_edge(edge: Any, field: str) -> None:
    if not isinstance(edge, dict):
        raise SystemExit(f"{field} must be an object")
    for key in ("source", "relation", "target"):
        if not isinstance(edge.get(key), str) or not edge[key].strip():
            raise SystemExit(f"{field} requires string source, relation, and target")
    if not EDGE_PATTERN.fullmatch(edge["relation"]):
        raise SystemExit(f"{field}.relation must be lowercase snake_case")


def check_design_proposal(
    project: Project,
    proposal: dict[str, Any],
    contract: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
    architecture: dict[str, Any] | None = None,
    repository_model: dict[str, Any] | None = None,
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = contract or load_contract(None, proposal["goal"])
    intent = intent or load_intent(None, contract["goal"])
    contract = apply_intent_to_contract(contract, intent)
    paths = unique_paths([*proposal_paths(proposal), *intent["scope"]])
    repository_model = repository_model or build_repository_model(project, intent["goal"], paths)
    architecture = architecture or architecture_from_model(repository_model)
    current_nodes = {node["id"]: node for node in architecture["nodes"]}
    added_nodes = {node["id"]: added_node_payload(node) for node in proposal["add_nodes"]}
    nodes = {**current_nodes, **added_nodes}
    current_edges = [edge_shape(edge) for edge in architecture["edges"]]
    removed = {edge_key(edge) for edge in proposal["remove_edges"]}
    effective_edges = [edge for edge in current_edges if edge_key(edge) not in removed]
    effective_edges.extend(edge_shape(edge) for edge in proposal["add_edges"])
    findings: list[dict[str, Any]] = []
    findings.extend(unknown_anchor_findings(proposal, nodes))
    findings.extend(cycle_findings(effective_edges, proposal["add_edges"]))
    findings.extend(state_owner_findings(effective_edges))
    findings.extend(boundary_findings(proposal["add_edges"], nodes))
    findings.extend(consumer_findings(proposal, architecture))
    findings.extend(test_findings(proposal, architecture, nodes))
    findings.extend(observability_findings(proposal, effective_edges, nodes))
    coverage = evaluate_coverage(proposal, contract, architecture)
    findings.extend(contract_reference_findings(proposal, contract))
    findings.extend(coverage["findings"])
    findings.extend(evaluate_rules(rules or [], nodes, effective_edges))
    if not proposal["invariants"]:
        findings.append(finding("warning", "missing_invariants", "Proposal does not state behavior that must remain true."))
    errors = [item for item in findings if item["severity"] == "error"]
    warnings = [item for item in findings if item["severity"] == "warning"]
    status = "blocked" if errors else "review" if warnings else "clean"
    dimensions = evaluate_dimensions(proposal, architecture, coverage, findings)
    revision = int(repository_model["snapshot"]["graph_revision"])
    return {
        "schema_version": evaluation_schema(proposal, contract),
        "candidate_id": proposal["id"],
        "contract_id": contract["id"],
        "project_id": project.project_id,
        "goal": proposal["goal"],
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "unverifiable_assumptions": proposal["assumptions"],
        "invariants": proposal["invariants"],
        "baseline_revision": revision,
        "repository_model": public_repository_model(repository_model),
        "synthesis_brief": build_synthesis_brief(repository_model, intent, contract),
        "quality_scenarios": coverage["quality_scenarios"],
        "constraint_coverage": coverage["constraints"],
        "coverage_summary": coverage["summary"],
        "dimensions": dimensions,
        "change_plan": build_change_plan(proposal, architecture, revision),
        "architecture_summary": {
            "entry_points": architecture["entry_points"],
            "node_count": architecture["audit"]["node_count"],
            "edge_count": architecture["audit"]["edge_count"],
            "evidence_gaps": architecture["evidence_gaps"],
        },
        "audit": {
            "proposal_nodes_added": len(added_nodes),
            "proposal_nodes_modified": len(proposal["modify_nodes"]),
            "proposal_edges_added": len(proposal["add_edges"]),
            "proposal_edges_removed": len(proposal["remove_edges"]),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "fitness_rule_count": len(rules or []),
            "contract_constraint_count": len(contract["constraints"]),
            "quality_scenario_count": len(contract["quality_scenarios"]),
            "persisted": False,
            "llm_used": False,
        },
    }


def evaluation_schema(proposal: dict[str, Any], contract: dict[str, Any]) -> str:
    if proposal["schema_version"] == DELTA_SCHEMA_V2 or contract["schema_version"] == CONTRACT_SCHEMA_V2:
        return EVALUATION_SCHEMA_V2
    return EVALUATION_SCHEMA


def contract_reference_findings(proposal: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if proposal["contract_id"] not in {"default", contract["id"]}:
        findings.append(finding("error", "contract_id_mismatch", "Candidate references a different design contract.", [proposal["contract_id"], contract["id"]]))
    covered_constraints = set(proposal["constraint_coverage"])
    findings.extend(
        finding("warning", "unknown_constraint_coverage", f"Candidate claims an unknown contract constraint: {item}", [item])
        for item in covered_constraints - set(contract["constraints"])
    )
    covered_scenarios = set(proposal["quality_coverage"])
    findings.extend(
        finding("warning", "unknown_quality_coverage", f"Candidate claims an unknown quality scenario: {item}", [item])
        for item in covered_scenarios - {scenario["id"] for scenario in contract["quality_scenarios"]}
    )
    return findings


def proposal_paths(proposal: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for node_id in proposal["anchors"] + proposal["modify_nodes"]:
        path = path_from_node_id(node_id)
        if path:
            values.append(path)
    values.extend(str(node.get("file_path")) for node in proposal["add_nodes"] if node.get("file_path"))
    return unique_paths(values)[:12]


def path_from_node_id(node_id: str) -> str | None:
    if node_id.startswith("file:"):
        return node_id[5:]
    if node_id.startswith("symbol:"):
        return node_id[7:].split("::", 1)[0]
    if node_id.startswith("log:"):
        return node_id[4:].rsplit(":", 1)[0]
    return None


def added_node_payload(node: dict[str, Any]) -> dict[str, Any]:
    path = str(node.get("file_path") or path_from_node_id(str(node["id"])) or "")
    kind = str(node["kind"])
    return {
        "id": str(node["id"]),
        "kind": kind,
        "file_path": path,
        "layer": infer_added_layer(kind, path),
    }


def infer_added_layer(kind: str, path: str) -> str:
    normalized = kind.lower()
    if normalized in {"service", "client"}:
        return "service"
    if normalized in {"repository", "storage", "cache", "database"}:
        return "data"
    if normalized in {"component", "page", "view"}:
        return "ui"
    if normalized in {"state", "store", "viewmodel"}:
        return "state"
    if normalized in {"test", "spec"}:
        return "test"
    return infer_layer(path)


def edge_shape(edge: dict[str, Any]) -> dict[str, str]:
    return {key: str(edge[key]) for key in ("source", "relation", "target")}


def edge_key(edge: dict[str, Any]) -> tuple[str, str, str]:
    return str(edge["source"]), str(edge["relation"]), str(edge["target"])


def unknown_anchor_findings(proposal: dict[str, Any], nodes: dict[str, Any]) -> list[dict[str, Any]]:
    added = {str(node["id"]) for node in proposal["add_nodes"]}
    referenced = set(proposal["anchors"] + proposal["modify_nodes"])
    for edge in proposal["add_edges"] + proposal["remove_edges"]:
        referenced.update((str(edge["source"]), str(edge["target"])))
    return [
        finding("warning", "unknown_anchor", f"Node is not present in the learned slice: {node_id}", [node_id])
        for node_id in sorted(referenced - set(nodes) - added)
    ]


def cycle_findings(
    edges: list[dict[str, str]],
    added_edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge["relation"] in DEPENDENCY_RELATIONS:
            graph[edge["source"]].add(edge["target"])
    for edge in added_edges:
        if str(edge["relation"]) not in DEPENDENCY_RELATIONS:
            continue
        source, target = str(edge["source"]), str(edge["target"])
        graph[source].discard(target)
        path = find_path(graph, target, source)
        graph[source].add(target)
        if path:
            return [finding("error", "dependency_cycle", "Proposed dependency edge creates a cycle.", [source, *path])]
    return []


def find_path(graph: dict[str, set[str]], start: str, target: str) -> list[str]:
    frontier: list[tuple[str, list[str]]] = [(start, [start])]
    visited: set[str] = set()
    while frontier:
        node, path = frontier.pop(0)
        if node == target:
            return path
        if node in visited:
            continue
        visited.add(node)
        for next_node in graph.get(node, set()):
            if next_node not in visited:
                frontier.append((next_node, [*path, next_node]))
    return []


def state_owner_findings(edges: list[dict[str, str]]) -> list[dict[str, Any]]:
    owners: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge["relation"] in {"defines_state", "owns_state"}:
            owners[edge["target"]].add(edge["source"])
    return [
        finding("error", "multiple_state_owners", f"State has multiple owners: {state}", sorted(values))
        for state, values in owners.items() if len(values) > 1
    ]


def boundary_findings(edges: list[dict[str, Any]], nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for edge in edges:
        source, target = nodes.get(str(edge["source"])), nodes.get(str(edge["target"]))
        if not source or not target or str(edge["relation"]) not in DEPENDENCY_RELATIONS:
            continue
        if source["layer"] in {"data", "service", "state"} and target["layer"] == "ui":
            findings.append(finding("error", "reverse_boundary_dependency", "Lower-level code depends on the UI layer.", [source["id"], target["id"]]))
        if source["layer"] == "ui" and target["layer"] == "data":
            findings.append(finding("warning", "ui_bypasses_service_boundary", "UI directly depends on a data/storage boundary.", [source["id"], target["id"]]))
    return findings


def consumer_findings(proposal: dict[str, Any], architecture: dict[str, Any]) -> list[dict[str, Any]]:
    modified = set(proposal["modify_nodes"])
    consumers: dict[str, set[str]] = defaultdict(set)
    for edge in architecture["edges"]:
        if edge["relation"] in DEPENDENCY_RELATIONS and edge["target"] in modified:
            consumers[edge["target"]].add(edge["source"])
    return [
        finding("warning", "review_public_consumers", f"Modified node has consumers outside the proposal: {target}", sorted(values - modified))
        for target, values in consumers.items() if values - modified
    ]


def test_findings(
    proposal: dict[str, Any],
    architecture: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    changed = set(proposal["modify_nodes"]) | {str(node["id"]) for node in proposal["add_nodes"]}
    production = [node_id for node_id in changed if nodes.get(node_id, {}).get("layer") not in {"test", "config"}]
    proposed_test = any(nodes.get(node_id, {}).get("layer") == "test" for node_id in changed)
    existing_test = bool(architecture["test_anchors"])
    if production and not proposed_test and not existing_test:
        return [finding("warning", "missing_test_anchor", "Changed production design has no learned or proposed test anchor.", production)]
    return []


def observability_findings(
    proposal: dict[str, Any],
    edges: list[dict[str, str]],
    nodes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    new_high_risk = {
        str(node["id"]) for node in proposal["add_nodes"]
        if str(node.get("kind") or "").lower() in {"service", "repository", "storage", "client"}
    }
    observed = {
        edge["source"] for edge in edges
        if edge["relation"] in {"emits_log", "observed_by_log"} or nodes.get(edge["target"], {}).get("kind") == "log"
    }
    missing = sorted(new_high_risk - observed)
    return [finding("warning", "missing_observability_anchor", "New high-risk boundary has no proposed observability edge.", missing)] if missing else []


def finding(severity: str, code: str, message: str, evidence: list[str] | None = None) -> dict[str, Any]:
    return {"severity": severity, "code": code, "message": message, "evidence": evidence or []}
