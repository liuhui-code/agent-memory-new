# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .architecture_slice import unique_paths
from .design_check import check_design_proposal, load_proposal, proposal_paths
from .design_protocol import MAX_CANDIDATES, apply_intent_to_contract, load_contract, load_intent, load_rules
from .design_synthesis import build_decision
from .records import output
from .repository_model import architecture_from_model, build_repository_model, public_repository_model
from .storage import ensure_initialized, resolve_project


def design_compare_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    proposals = [load_proposal(Path(path)) for path in args.proposal]
    if not 2 <= len(proposals) <= MAX_CANDIDATES:
        raise SystemExit(f"design-compare requires 2 to {MAX_CANDIDATES} proposals")
    contract = load_contract(args.contract, proposals[0]["goal"])
    intent = load_intent(getattr(args, "intent", None), contract["goal"])
    rules = load_rules(args.rules)
    payload = compare_designs(project, proposals, contract, rules, intent=intent)
    output(payload, args.json)


def compare_designs(
    project: Any,
    proposals: list[dict[str, Any]],
    contract: dict[str, Any],
    rules: list[dict[str, Any]],
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ids = [proposal["id"] for proposal in proposals]
    if len(ids) != len(set(ids)):
        raise SystemExit("design proposal ids must be unique for comparison")
    intent = intent or load_intent(None, contract["goal"])
    contract = apply_intent_to_contract(contract, intent)
    paths = unique_paths([*intent["scope"], *[path for proposal in proposals for path in proposal_paths(proposal)]])[:24]
    repository_model = build_repository_model(project, intent["goal"], paths)
    architecture = architecture_from_model(repository_model)
    evaluations = [
        check_design_proposal(
            project,
            proposal,
            contract,
            rules,
            architecture,
            repository_model=repository_model,
            intent=intent,
        )
        for proposal in proposals
    ]
    summaries = [candidate_summary(proposal, evaluation, contract) for proposal, evaluation in zip(proposals, evaluations)]
    ranked = sorted(summaries, key=ranking_key)
    winner = ranked[0]
    reasons = decision_reasons(winner, ranked[1:] if len(ranked) > 1 else [])
    candidate_tradeoffs = tradeoffs(ranked)
    return {
        "schema_version": "design-comparison/v2" if any(item["schema_version"].endswith("/v2") for item in proposals) else "design-comparison/v1",
        "project_id": project.project_id,
        "contract_id": contract["id"],
        "goal": contract["goal"],
        "recommended_candidate": winner["candidate_id"],
        "baseline_revision": repository_model["snapshot"]["graph_revision"],
        "repository_model": public_repository_model(repository_model),
        "decision_reasons": reasons,
        "tradeoffs": candidate_tradeoffs,
        "sensitivity_points": sensitivity_points(summaries),
        "tradeoff_points": tradeoff_points(summaries),
        "decision": build_decision(winner["candidate_id"], summaries, reasons, candidate_tradeoffs),
        "selected_change_plan": next(item["change_plan"] for item in evaluations if item["candidate_id"] == winner["candidate_id"]),
        "candidates": sorted(summaries, key=lambda item: item["candidate_id"]),
        "evaluations": sorted((comparison_evaluation(item) for item in evaluations), key=lambda item: item["candidate_id"]),
        "audit": {
            "candidate_count": len(proposals),
            "fitness_rule_count": len(rules),
            "architecture_node_count": architecture["audit"]["node_count"],
            "architecture_edge_count": architecture["audit"]["edge_count"],
            "architecture_reused": True,
            "persisted": False,
            "llm_used": False,
            "decision_model": "hard-gate-then-lexicographic-v1",
        },
    }


def candidate_summary(
    proposal: dict[str, Any],
    evaluation: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    covered = sum(1 for item in evaluation["quality_scenarios"] if item["covered"])
    high_missing = sum(1 for item in evaluation["quality_scenarios"] if item["priority"] == "high" and not item["covered"])
    change_size = (
        len(proposal["add_nodes"]) + len(proposal["modify_nodes"])
        + len(proposal["add_edges"]) + len(proposal["remove_edges"])
    )
    unknowns = len(proposal["assumptions"]) + sum(
        1 for item in evaluation["warnings"] if item["code"] == "unknown_anchor"
    )
    return {
        "candidate_id": proposal["id"],
        "status": evaluation["status"],
        "hard_violations": len(evaluation["errors"]),
        "warnings": len(evaluation["warnings"]),
        "quality_scenarios_covered": covered,
        "supported_quality_scenarios": sum(
            1 for item in evaluation["quality_scenarios"]
            if item["coverage_state"] in {"supported", "verified"}
        ),
        "verified_quality_scenarios": sum(
            1 for item in evaluation["quality_scenarios"] if item["coverage_state"] == "verified"
        ),
        "quality_scenarios_total": len(contract["quality_scenarios"]),
        "high_priority_scenarios_missing": high_missing,
        "change_size": change_size,
        "uncertainty_count": unknowns,
        "testability_gap": has_finding(evaluation, "missing_test_anchor"),
        "observability_gap": has_finding(evaluation, "missing_observability_anchor"),
        "dimensions": evaluation["dimensions"],
    }


def ranking_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        item["hard_violations"] > 0,
        item["hard_violations"],
        item["high_priority_scenarios_missing"],
        -item["supported_quality_scenarios"],
        -item["quality_scenarios_covered"],
        item["warnings"],
        item["uncertainty_count"],
        item["change_size"],
        item["candidate_id"],
    )


def decision_reasons(winner: dict[str, Any], others: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    if winner["hard_violations"] == 0 and any(item["hard_violations"] for item in others):
        reasons.append("passes hard architecture gates while another candidate is blocked")
    if others and winner["quality_scenarios_covered"] > min(item["quality_scenarios_covered"] for item in others):
        reasons.append("covers more declared quality scenarios")
    if others and winner["uncertainty_count"] < max(item["uncertainty_count"] for item in others):
        reasons.append("contains fewer unsupported assumptions or unknown anchors")
    if others and winner["change_size"] < max(item["change_size"] for item in others):
        reasons.append("requires a smaller explicit design delta")
    return reasons or ["wins the deterministic tie-break after equivalent evaluated dimensions"]


def tradeoffs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(items) < 2:
        return []
    best = items[0]
    result: list[dict[str, Any]] = []
    for item in items[1:]:
        advantages = []
        if item["change_size"] < best["change_size"]:
            advantages.append("smaller_change_size")
        if item["quality_scenarios_covered"] > best["quality_scenarios_covered"]:
            advantages.append("greater_quality_coverage")
        if item["uncertainty_count"] < best["uncertainty_count"]:
            advantages.append("lower_uncertainty")
        if advantages:
            result.append({"candidate_id": item["candidate_id"], "advantages_over_recommendation": advantages})
    return result


def has_finding(evaluation: dict[str, Any], code: str) -> bool:
    return any(item["code"] == code for item in evaluation["errors"] + evaluation["warnings"])


def comparison_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "schema_version",
        "candidate_id",
        "status",
        "errors",
        "warnings",
        "quality_scenarios",
        "constraint_coverage",
        "coverage_summary",
        "dimensions",
        "architecture_summary",
        "audit",
    )
    return {field: evaluation[field] for field in fields}


def sensitivity_points(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(items) < 2:
        return []
    names = sorted(set.intersection(*(set(item["dimensions"]) for item in items)))
    result = []
    for name in names:
        values = {item["candidate_id"]: item["dimensions"][name]["value"] for item in items}
        if len(set(values.values())) > 1:
            result.append({"dimension": name, "candidate_values": values})
    return result


def tradeoff_points(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(items) < 2:
        return []
    result = []
    for name in sorted(items[0]["dimensions"]):
        statuses = {item["candidate_id"]: item["dimensions"][name]["status"] for item in items}
        if len(set(statuses.values())) > 1:
            result.append({"dimension": name, "candidate_statuses": statuses})
    return result
