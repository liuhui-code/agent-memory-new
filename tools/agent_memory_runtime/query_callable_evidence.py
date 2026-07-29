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
        "callable_roles": strings(item.get("callable_roles"))[:4],
        "score": item.get("score"),
        "reasons": strings(item.get("reasons"))[:4],
    }
    source_range = ranges.get((path, symbol))
    if source_range:
        result["source_range"] = source_range
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
    score = float(primary.get("score") or 0.0)
    next_score = float(alternatives[0].get("score") or 0.0) if alternatives else 0.0
    return "bounded" if score >= next_score + 2.0 else "uncertain"


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
