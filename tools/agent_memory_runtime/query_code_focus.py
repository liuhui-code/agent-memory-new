# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from pathlib import PurePosixPath
import re
from typing import Any

from .arkts_ui_behavior import (
    direct_operation_query_terms,
    distinctive_operation_names,
    matching_operation_names,
)
from .query_behavior_concepts import matching_behavior_markers


IDENTITY_REASONS = {"exact_symbol", "exact_file_path", "exact_identifier"}
STRONG_FOCUS_REASONS = {*IDENTITY_REASONS, "exact_path_segment"}
FLOW_REASONS = {"graph_relation:passes_property", "graph_relation:renders_component"}
NAMED_CODE_IDENTITY_RE = re.compile(
    r"\b[A-Z][A-Za-z0-9_$]*(?:Ability|Controller|Model|Page|Record|Repository|Service|View|ViewModel)\b"
)


def score_file_behavior_match(
    summary: str,
    original_query_terms: set[str],
    query: str,
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
    structural = matching_behavior_markers(summary, query)
    if structural:
        score += 4.0 + 2.0 * (len(structural) - 1)
        reasons.append("structural_behavior")
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
    query: str = "",
) -> tuple[list[dict[str, Any]], bool]:
    named = named_identity_candidates(items, query)
    if len(unique_paths(named)) >= 2:
        return named, True
    structural = strongest_structural_candidates(items, query)
    if structural:
        return structural, True
    behavior = [item for item in items if has_reason(item, "exact_behavior_operation")]
    if behavior:
        return behavior, True
    dominant = dominant_shared_owner(items, query)
    if dominant:
        return dominant, True
    strong_identity = strong_identity_candidates(items)
    if strong_identity:
        return strong_identity, True
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


def strong_identity_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if any(has_any_reason(item, FLOW_REASONS) for item in items):
        return []
    strong = [item for item in items if has_any_reason(item, STRONG_FOCUS_REASONS)]
    if len(unique_paths(strong)) < 2:
        return []
    allowed = {id(item) for item in strong}
    return [item for item in items if id(item) in allowed]


def strongest_structural_candidates(
    items: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    matches = [
        (
            item,
            set(matching_behavior_markers(
                f"{item.get('file_path') or ''} {item.get('summary') or ''}",
                query,
            )),
        )
        for item in items
        if has_reason(item, "structural_behavior")
    ]
    ranked = sorted(
        enumerate(matches),
        key=lambda value: (-len(value[1][1]), value[0]),
    )
    selected: list[dict[str, Any]] = []
    covered: set[str] = set()
    for _index, (item, markers) in ranked:
        if not markers - covered:
            continue
        selected.append(item)
        covered.update(markers)
        if len(selected) >= 3:
            break
    selected_ids = {id(item) for item in selected}
    return [item for item in items if id(item) in selected_ids]


def dominant_shared_owner(
    items: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    if len(items) < 2 or "shared" not in query.casefold():
        return []
    first = items[0]
    if not has_reason(first, "multi_concept_coverage"):
        return []
    first_score = float(first.get("score") or 0.0)
    second_score = float(items[1].get("score") or 0.0)
    if first_score <= 0.0 or second_score > first_score * 0.65:
        return []
    return [
        item for item in items
        if has_reason(item, "multi_concept_coverage")
        and float(item.get("score") or 0.0) >= first_score * 0.75
    ]


def named_identity_candidates(
    items: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    identities = set(NAMED_CODE_IDENTITY_RE.findall(query))
    if len(identities) < 2:
        return []
    return [item for item in items if candidate_identities(item) & identities]


def candidate_identities(item: dict[str, Any]) -> set[str]:
    file_path = str(item.get("file_path") or "")
    stem = PurePosixPath(file_path).stem if file_path else ""
    symbol = str(item.get("symbol") or "")
    return {value for value in (stem, symbol) if value}


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
