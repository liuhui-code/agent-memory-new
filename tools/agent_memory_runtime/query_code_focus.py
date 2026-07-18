# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .arkts_ui_behavior import (
    direct_operation_query_terms,
    distinctive_operation_names,
    matching_operation_names,
)


IDENTITY_REASONS = {"exact_symbol", "exact_file_path", "exact_identifier"}
FLOW_REASONS = {"graph_relation:passes_property", "graph_relation:renders_component"}


def score_file_behavior_match(
    summary: str,
    original_query_terms: set[str],
    score: float,
    reasons: list[str],
) -> tuple[float, list[str]]:
    matches = matching_operation_names(
        summary,
        direct_operation_query_terms(original_query_terms),
    )
    if matches:
        score += 6.0 + 2.0 * (len(matches) - 1)
        reasons.append("behavior_operation")
    if distinctive_operation_names(matches):
        score += 12.0
        reasons.append("exact_behavior_operation")
    return score, list(dict.fromkeys(reasons))


def attach_file_source_locations(items: list[dict[str, Any]]) -> None:
    locations: dict[str, dict[str, Any]] = {}
    for item in items:
        if not valid_source_location(item):
            continue
        path = str(item.get("file_path") or "")
        current = locations.get(path)
        if current is None or location_priority(item) < location_priority(current):
            locations[path] = item
    for item in items:
        if valid_source_location(item):
            continue
        location = locations.get(str(item.get("file_path") or ""))
        if location is None:
            continue
        for key in ("symbol", "symbol_type", "start_line", "end_line"):
            item[key] = location.get(key)


def focus_code_candidates(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    behavior = [item for item in items if has_reason(item, "exact_behavior_operation")]
    if len(behavior) == 1:
        return behavior, True
    flow = [item for item in items if has_any_reason(item, FLOW_REASONS)]
    if not flow:
        return items, False
    identity = [item for item in items if has_any_reason(item, IDENTITY_REASONS)]
    if len(unique_paths(identity)) >= 2:
        allowed = {id(item) for item in [*identity, *flow]}
        return [item for item in items if id(item) in allowed], True
    if len(unique_paths(flow)) >= 2:
        seed = next((item for item in items if item not in flow), None)
        allowed = {id(item) for item in flow}
        if seed is not None:
            allowed.add(id(seed))
        return [item for item in items if id(item) in allowed], True
    return items, False


def valid_source_location(item: dict[str, Any]) -> bool:
    return (
        isinstance(item.get("start_line"), int)
        and isinstance(item.get("end_line"), int)
        and int(item["start_line"]) > 0
        and int(item["end_line"]) >= int(item["start_line"])
    )


def location_priority(item: dict[str, Any]) -> tuple[int, int]:
    symbol_type = str(item.get("symbol_type") or "")
    rank = {"component": 0, "class": 1, "function": 2}.get(symbol_type, 3)
    return rank, int(item.get("start_line") or 0)


def is_graph_neighbor(item: dict[str, Any]) -> bool:
    return has_reason(item, "graph_neighbor")


def has_reason(item: dict[str, Any], reason: str) -> bool:
    return reason in {str(value) for value in item.get("match_reasons") or []}


def has_any_reason(item: dict[str, Any], reasons: set[str]) -> bool:
    return bool(reasons & {str(value) for value in item.get("match_reasons") or []})


def unique_paths(items: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("file_path") or "") for item in items if item.get("file_path")}
