# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from typing import Any

from .architecture_slice import DEPENDENCY_RELATIONS
from .design_protocol import apply_intent_to_contract, load_contract, load_intent, load_rules
from .design_synthesis import build_synthesis_brief
from .records import output
from .repository_model import build_repository_model, public_repository_model
from .storage import ensure_initialized, resolve_project


MAX_CATALOG_NODES = 80
MAX_CATALOG_RULES = 50


def design_prepare_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    intent = load_intent(args.intent, "")
    contract = apply_intent_to_contract(load_contract(args.contract, intent["goal"]), intent)
    rules = load_rules(args.rules)
    validate_intent_binding(intent, contract)
    model = build_repository_model(project, intent["goal"], intent["scope"])
    output(build_design_workbench(project.project_id, intent, contract, rules, model), args.json)


def build_design_workbench(
    project_id: str,
    intent: dict[str, Any],
    contract: dict[str, Any],
    rules: list[dict[str, Any]],
    model: dict[str, Any],
) -> dict[str, Any]:
    architecture = model["architecture"]
    gaps = authoring_gaps(intent, contract, model)
    return {
        "schema_version": "design-workbench/v1",
        "project_id": project_id,
        "intent": intent,
        "contract": contract,
        "baseline_revision": model["snapshot"]["graph_revision"],
        "repository_model": public_repository_model(model),
        "synthesis_brief": build_synthesis_brief(model, intent, contract),
        "anchor_catalog": build_anchor_catalog(architecture),
        "fitness_rules": rules[:MAX_CATALOG_RULES],
        "candidate_template": candidate_template(intent, contract, model),
        "authoring_readiness": {
            "status": "needs_input" if blocking_gaps(gaps) else "ready",
            "gaps": gaps,
            "next_steps": next_steps(gaps),
        },
        "audit": {
            "persisted": False,
            "llm_used": False,
            "bounded": True,
            "candidate_independent_baseline": True,
            "catalog_node_limit": MAX_CATALOG_NODES,
            "catalog_rule_limit": MAX_CATALOG_RULES,
            "rules_truncated": len(rules) > MAX_CATALOG_RULES,
        },
    }


def validate_intent_binding(intent: dict[str, Any], contract: dict[str, Any]) -> None:
    contract_intent = contract.get("intent_id")
    if contract_intent and contract_intent not in {"default", intent["id"]}:
        raise SystemExit("design contract references a different intent")


def build_anchor_catalog(architecture: dict[str, Any]) -> dict[str, Any]:
    nodes = sorted(architecture["nodes"], key=lambda item: item["id"])
    relations = DEPENDENCY_RELATIONS | {str(edge["relation"]) for edge in architecture["edges"]}
    return {
        "node_ids": [str(node["id"]) for node in nodes[:MAX_CATALOG_NODES]],
        "nodes": [catalog_node(node) for node in nodes[:MAX_CATALOG_NODES]],
        "relation_vocabulary": sorted(relations),
        "baseline_entry_points": architecture.get("baseline_entry_points", [])[:12],
        "scope_entry_points": architecture.get("scope_entry_points", [])[:12],
        "truncated": len(nodes) > MAX_CATALOG_NODES,
    }


def catalog_node(node: dict[str, Any]) -> dict[str, Any]:
    fields = ("id", "kind", "layer", "file_path", "evidence_class")
    return {field: node[field] for field in fields if node.get(field) is not None}


def candidate_template(
    intent: dict[str, Any],
    contract: dict[str, Any],
    model: dict[str, Any],
) -> dict[str, Any]:
    coverage = [coverage_skeleton("constraint", item) for item in contract["constraints"]]
    coverage.extend(coverage_skeleton("scenario", item["id"]) for item in contract["quality_scenarios"])
    return {
        "schema_version": "design-delta/v2",
        "id": "candidate-1",
        "contract_id": contract["id"],
        "goal": intent["goal"],
        "baseline_revision": model["snapshot"]["graph_revision"],
        "anchors": model["baseline_entry_points"][:12],
        "add_nodes": [],
        "modify_nodes": [],
        "add_edges": [],
        "remove_edges": [],
        "assumptions": [],
        "invariants": [],
        "constraint_coverage": [],
        "quality_coverage": [],
        "coverage_evidence": coverage,
        "verification": {"tests": [], "observability": []},
    }


def coverage_skeleton(target_type: str, target_id: str) -> dict[str, Any]:
    return {
        "target_type": target_type,
        "target_id": target_id,
        "delta_refs": [],
        "repository_refs": [],
        "verification_refs": [],
    }


def authoring_gaps(
    intent: dict[str, Any],
    contract: dict[str, Any],
    model: dict[str, Any],
) -> list[dict[str, Any]]:
    gaps = []
    if not intent["acceptance_criteria"]:
        gaps.append(gap("missing_acceptance_criteria", True, "define observable acceptance criteria"))
    if not contract["quality_scenarios"]:
        gaps.append(gap("missing_quality_scenarios", False, "add measurable quality scenarios when relevant"))
    if not model["baseline_entry_points"]:
        gaps.append(gap("missing_baseline_anchors", True, "learn or scope current code for the design goal"))
    if model["snapshot"]["freshness"] == "stale":
        gaps.append(gap("stale_repository_snapshot", True, "refresh the stale learned scope before authoring"))
    if model["evidence_gaps"]:
        gaps.append({
            **gap("repository_evidence_gaps", False, "treat missing graph coverage as uncertainty"),
            "count": len(model["evidence_gaps"]),
        })
    return gaps


def gap(code: str, blocking: bool, action: str) -> dict[str, Any]:
    return {"code": code, "blocking": blocking, "action": action}


def blocking_gaps(gaps: list[dict[str, Any]]) -> bool:
    return any(item["blocking"] for item in gaps)


def next_steps(gaps: list[dict[str, Any]]) -> list[str]:
    actions = [str(item["action"]) for item in gaps if item["blocking"]]
    actions.extend([
        "author one smallest viable design-delta/v2 candidate",
        "run design-check and compare only materially different candidates",
    ])
    return actions[:8]
