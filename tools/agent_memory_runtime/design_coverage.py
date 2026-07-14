# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


def evaluate_coverage(
    proposal: dict[str, Any],
    contract: dict[str, Any],
    architecture: dict[str, Any],
    verified_refs: set[str] | None = None,
) -> dict[str, Any]:
    evidence = coverage_index(proposal)
    valid_delta = proposal_delta_refs(proposal)
    valid_repository = {node["id"] for node in architecture["nodes"]}
    declared_verification = set(proposal["verification"]["tests"] + proposal["verification"]["observability"])
    verified_refs = verified_refs or set()
    scenarios = [
        coverage_item(
            "scenario",
            scenario["id"],
            scenario["id"] in set(proposal["quality_coverage"]),
            evidence.get(("scenario", scenario["id"])),
            valid_delta,
            valid_repository,
            declared_verification,
            verified_refs,
            scenario,
        )
        for scenario in contract["quality_scenarios"]
    ]
    constraints = [
        coverage_item(
            "constraint",
            constraint,
            constraint in set(proposal["constraint_coverage"]),
            evidence.get(("constraint", constraint)),
            valid_delta,
            valid_repository,
            declared_verification,
            verified_refs,
            {"id": constraint},
        )
        for constraint in contract["constraints"]
    ]
    return {
        "quality_scenarios": scenarios,
        "constraints": constraints,
        "findings": coverage_findings(scenarios, constraints),
        "summary": coverage_summary(scenarios, constraints),
    }


def coverage_index(proposal: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (item["target_type"], item["target_id"]): item
        for item in proposal.get("coverage_evidence", [])
    }


def proposal_delta_refs(proposal: dict[str, Any]) -> set[str]:
    refs = set(proposal["modify_nodes"])
    refs.update(str(node["id"]) for node in proposal["add_nodes"])
    for edge in proposal["add_edges"] + proposal["remove_edges"]:
        refs.update((str(edge["source"]), str(edge["target"])))
    return refs


def coverage_item(
    target_type: str,
    target_id: str,
    claimed: bool,
    evidence: dict[str, Any] | None,
    valid_delta: set[str],
    valid_repository: set[str],
    declared_verification: set[str],
    verified_refs: set[str],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    evidence = evidence or {"delta_refs": [], "repository_refs": [], "verification_refs": []}
    delta_refs = [ref for ref in evidence["delta_refs"] if ref in valid_delta]
    repository_refs = [ref for ref in evidence["repository_refs"] if ref in valid_repository]
    verification_refs = [ref for ref in evidence["verification_refs"] if ref in declared_verification]
    supported = claimed and bool(delta_refs) and bool(repository_refs)
    verified = supported and bool(verification_refs) and bool(set(verification_refs) & verified_refs)
    state = "verified" if verified else "supported" if supported else "claimed" if claimed else "uncovered"
    result = {
        "id": target_id,
        "covered": claimed,
        "coverage_state": state,
        "delta_refs": delta_refs,
        "repository_refs": repository_refs,
        "verification_refs": verification_refs,
        "verification_ready": bool(verification_refs),
        "missing_evidence": missing_evidence(claimed, delta_refs, repository_refs, verification_refs),
    }
    for field in ("attribute", "priority", "measure", "evidence_requirements"):
        if field in metadata:
            result[field] = metadata[field]
    return result


def missing_evidence(
    claimed: bool,
    delta_refs: list[str],
    repository_refs: list[str],
    verification_refs: list[str],
) -> list[str]:
    if not claimed:
        return ["claim"]
    missing = []
    if not delta_refs:
        missing.append("delta")
    if not repository_refs:
        missing.append("repository")
    if not verification_refs:
        missing.append("verification")
    return missing


def coverage_findings(scenarios: list[dict[str, Any]], constraints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in constraints:
        if item["coverage_state"] == "uncovered":
            findings.append(finding("error", "uncovered_contract_constraint", item))
        elif item["coverage_state"] == "claimed":
            findings.append(finding("warning", "unsupported_coverage_claim", item))
    for item in scenarios:
        if item["coverage_state"] == "uncovered":
            findings.append(finding("warning", "uncovered_quality_scenario", item))
        elif item["coverage_state"] == "claimed":
            findings.append(finding("warning", "unsupported_coverage_claim", item))
    return findings


def finding(severity: str, code: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": f"Coverage for {item['id']} lacks required evidence.",
        "evidence": [item["id"], *item["missing_evidence"]],
    }


def coverage_summary(scenarios: list[dict[str, Any]], constraints: list[dict[str, Any]]) -> dict[str, int]:
    items = scenarios + constraints
    return {
        state: sum(1 for item in items if item["coverage_state"] == state)
        for state in ("uncovered", "claimed", "supported", "verified")
    }
