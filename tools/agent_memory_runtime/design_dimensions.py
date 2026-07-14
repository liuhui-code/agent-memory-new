# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any, Callable


DimensionProvider = Callable[[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]], dict[str, Any]]


def evaluate_dimensions(
    proposal: dict[str, Any],
    architecture: dict[str, Any],
    coverage: dict[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        name: provider(proposal, architecture, coverage, findings)
        for name, provider in DIMENSION_PROVIDERS
    }


def coverage_dimension(_proposal: dict[str, Any], _architecture: dict[str, Any], coverage: dict[str, Any], _findings: list[dict[str, Any]]) -> dict[str, Any]:
    summary = coverage["summary"]
    return dimension(
        "risk" if summary["uncovered"] or summary["claimed"] else "satisfied",
        summary["supported"] + summary["verified"],
        summary,
    )


def compatibility_dimension(proposal: dict[str, Any], architecture: dict[str, Any], _coverage: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    consumers = architecture.get("public_consumers") or []
    risks = matching_codes(findings, {"review_public_consumers", "uncovered_contract_constraint"})
    return dimension("risk" if risks else "satisfied", len(consumers), {"consumers": consumers[:12], "findings": risks})


def ownership_dimension(_proposal: dict[str, Any], architecture: dict[str, Any], _coverage: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    risks = matching_codes(findings, {"multiple_state_owners"})
    return dimension("blocked" if risks else "satisfied", len(architecture.get("state_owners") or []), {"findings": risks})


def dependency_dimension(_proposal: dict[str, Any], architecture: dict[str, Any], _coverage: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    risks = matching_codes(findings, {"dependency_cycle", "reverse_boundary_dependency", "ui_bypasses_service_boundary"})
    return dimension("blocked" if any(item["severity"] == "error" for item in risks) else "risk" if risks else "satisfied", len(architecture["edges"]), {"findings": risks})


def failure_dimension(proposal: dict[str, Any], architecture: dict[str, Any], _coverage: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    risks = matching_codes(findings, {"missing_observability_anchor"})
    async_edges = sum(1 for edge in architecture["edges"] if edge["relation"] == "awaits")
    obligations = len(proposal["verification"]["observability"])
    return dimension("risk" if risks else "satisfied", async_edges + obligations, {"findings": risks, "obligations": obligations})


def testability_dimension(proposal: dict[str, Any], architecture: dict[str, Any], _coverage: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    risks = matching_codes(findings, {"missing_test_anchor"})
    evidence = len(proposal["verification"]["tests"]) + len(architecture.get("test_anchors") or [])
    return dimension("risk" if risks else "satisfied", evidence, {"findings": risks})


def uncertainty_dimension(proposal: dict[str, Any], architecture: dict[str, Any], coverage: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    unknowns = len(proposal["assumptions"]) + len(architecture.get("evidence_gaps") or []) + coverage["summary"]["claimed"]
    risks = matching_codes(findings, {"unknown_anchor", "unsupported_coverage_claim"})
    return dimension("risk" if unknowns else "satisfied", unknowns, {"findings": risks})


def change_cost_dimension(proposal: dict[str, Any], _architecture: dict[str, Any], _coverage: dict[str, Any], _findings: list[dict[str, Any]]) -> dict[str, Any]:
    size = sum(len(proposal[field]) for field in ("add_nodes", "modify_nodes", "add_edges", "remove_edges"))
    return dimension("bounded", size, {"explicit_delta_size": size})


def dimension(status: str, score: int, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"status": status, "value": score, "evidence": evidence}


def matching_codes(findings: list[dict[str, Any]], codes: set[str]) -> list[dict[str, Any]]:
    return [item for item in findings if item["code"] in codes]


DIMENSION_PROVIDERS: tuple[tuple[str, DimensionProvider], ...] = (
    ("evidence_coverage", coverage_dimension),
    ("compatibility", compatibility_dimension),
    ("ownership", ownership_dimension),
    ("dependency_direction", dependency_dimension),
    ("failure_flow", failure_dimension),
    ("testability", testability_dimension),
    ("uncertainty", uncertainty_dimension),
    ("change_cost", change_cost_dimension),
)
