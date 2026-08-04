# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


def callable_evidence(localization: dict[str, Any]) -> dict[str, Any]:
    """Project bounded callable ranking as Agent evidence, never as diagnosis."""
    candidates = records(localization.get("callable_candidates"))
    ranges = range_lookup(records(localization.get("source_ranges")))
    prepared = [compact_candidate(item, ranges) for item in candidates]
    if not prepared:
        return {
            "schema_version": "agent-callable-evidence/v1",
            "certainty": "unavailable",
            "primary": None,
            "alternatives": [],
            "boundary": "retrieval_evidence_not_root_cause",
        }
    primary = prepared[0]
    alternatives = diverse_alternatives(prepared[1:], primary)
    return {
        "schema_version": "agent-callable-evidence/v1",
        "certainty": certainty(primary, alternatives),
        "primary": primary,
        "alternatives": alternatives,
        "boundary": "retrieval_evidence_not_root_cause",
    }


def compact_candidate(item: dict[str, Any], ranges: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    path = str(item.get("file_path") or "")
    symbol = str(item.get("symbol") or "")
    result = {
        "file_path": path,
        "symbol": symbol,
        "owner_name": item.get("owner_name"),
        "owner_kind": item.get("owner_kind"),
        "target_owner_kind_match": item.get("target_owner_kind_match"),
        "file_structural_coverage": item.get("file_structural_coverage"),
        "callable_roles": strings(item.get("callable_roles"))[:4],
        "score": item.get("score"),
        "evidence_score": item.get("evidence_score"),
        "reasons": strings(item.get("reasons"))[:4],
    }
    source_range = ranges.get((path, symbol))
    if source_range:
        result["source_range"] = source_range
    if item.get("artifact_role_competition"):
        result.update({
            "artifact_role": item.get("artifact_role"),
            "artifact_query_intent": item.get("artifact_query_intent"),
            "artifact_role_competition": True,
            "artifact_role_representative": item.get("artifact_role_representative"),
            "artifact_role_shadow": item.get("artifact_role_shadow"),
        })
    return {key: value for key, value in result.items() if value not in (None, "", [])}


def diverse_alternatives(items: list[dict[str, Any]], primary: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen = {(primary.get("file_path"), primary.get("owner_kind"))}
    for item in items:
        identity = (item.get("file_path"), item.get("owner_kind"))
        if identity in seen:
            continue
        seen.add(identity)
        result.append(item)
        if len(result) == 2:
            break
    return result


def certainty(primary: dict[str, Any], alternatives: list[dict[str, Any]]) -> str:
    if not primary.get("source_range"):
        return "uncertain"
    reasons = set(strings(primary.get("reasons")))
    owner_kind = primary.get("owner_kind")
    if (primary.get("target_owner_kind_match") or "structured_owner_kind" in reasons) and all(
        item.get("owner_kind") != owner_kind for item in alternatives
    ):
        return "bounded"
    if primary.get("target_owner_kind_match") and structurally_dominates(
        primary, alternatives,
    ):
        return "bounded"
    if primary.get("target_owner_kind_match"):
        score = float(primary.get("score") or 0.0)
        next_score = float(alternatives[0].get("score") or 0.0) if alternatives else 0.0
    else:
        score = calibrated_evidence_score(primary)
        next_score = calibrated_evidence_score(alternatives[0]) if alternatives else 0.0
    return "bounded" if score >= next_score + 2.0 else "uncertain"


def structurally_dominates(
    primary: dict[str, Any], alternatives: list[dict[str, Any]],
) -> bool:
    coverage = int(primary.get("file_structural_coverage") or 0)
    competing = [
        int(item.get("file_structural_coverage") or 0)
        for item in alternatives if item.get("owner_kind") == primary.get("owner_kind")
    ]
    return coverage > 0 and bool(competing) and coverage > max(competing)


def calibrated_evidence_score(item: dict[str, Any]) -> float:
    return max(0.0, float(item.get("evidence_score") or item.get("score") or 0.0))


def range_lookup(items: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items:
        path = str(item.get("file_path") or "")
        symbol = str(item.get("symbol") or "")
        if path and symbol:
            result[(path, symbol)] = {
                "start_line": item.get("start_line"),
                "end_line": item.get("end_line"),
                "selection_reason": item.get("selection_reason"),
            }
    return result


def records(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def strings(value: object) -> list[str]:
    return [str(item) for item in value if str(item)] if isinstance(value, list) else []
