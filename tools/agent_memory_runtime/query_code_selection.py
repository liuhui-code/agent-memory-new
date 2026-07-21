# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any

from .query_behavior_concepts import behavior_marker_terms
from .query_code_focus import attach_file_source_locations, focus_code_candidates
from .query_language import excluded_result_roles, positive_retrieval_query
from .source_path_policy import (
    filter_explicit_language_candidates,
    filter_generated_candidates,
)
from .text import english_query_variants, identifier_tokens, tokenize


CODE_DIVERSITY_THRESHOLD = 0.3
CODE_DIVERSITY_GENERIC_TERMS = {
    "component", "components", "ets", "features", "home", "main", "pages",
    "src", "view", "viewmodel", "views",
}
EXPLICIT_PATH_GENERIC_TERMS = {
    "chat", "controller", "coordinator", "data", "detail", "login",
    "model", "preferences", "registry", "service", "source", "storage",
    "store",
}
NEGATIVE_PATH_MARKERS = (" not ", "exclude", "excluding", "ignore", "不要", "忽略")
OPAQUE_IDENTIFIER_RE = re.compile(
    r"\b(?=[A-Za-z0-9_]{8,}\b)(?=[A-Za-z0-9_]*[A-Za-z])"
    r"(?=[A-Za-z0-9_]*\d)[A-Za-z0-9_]+\b"
)
DIRECT_GRAPH_OVERRIDE_REASONS = {
    "caller_owner",
    "behavior_operation",
    "exact_behavior_operation",
    "exact_file_path",
    "exact_identifier",
    "exact_path_segment",
    "exact_symbol",
    "structural_behavior",
}


def diverse_code_matches(
    items: list[dict[str, Any]],
    limit: int,
    max_per_file: int = 2,
    query: str = "",
) -> list[dict[str, Any]]:
    explicit_paths = protected_explicit_paths(items, query)
    attach_file_source_locations(items)
    items = filter_query_role_candidates(items, query)
    items = interleave_graph_candidate(items, explicit_paths)
    focused, focused_candidates = focus_code_candidates(items, query)
    if explicit_paths:
        focused_ids = {id(item) for item in focused}
        focused_ids.update(
            id(item) for item in items
            if str(item.get("file_path") or "") in explicit_paths
        )
        items = [item for item in items if id(item) in focused_ids]
        focused_candidates = True
    else:
        items = focused
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    file_counts: dict[str, int] = {}
    selected_terms: list[set[str]] = []
    direct_scores = [
        float(item.get("score") or 0.0)
        for item in items
        if not is_graph_neighbor(item)
    ]
    seed_score = max(direct_scores, default=0.0)
    for index, item in enumerate(items):
        file_path = str(item.get("file_path") or "")
        terms = code_candidate_terms(item)
        reserved_graph_lane = is_graph_neighbor(item) and (
            index == 1 or (index == 2 and is_component_flow_neighbor(item))
        )
        explicit_target = file_path in explicit_paths
        weak_graph_neighbor = (
            limit <= 5
            and is_graph_neighbor(item)
            and (
                seed_score <= 0.0
                or float(item.get("score") or 0.0) < seed_score * 0.5
            )
        )
        if weak_graph_neighbor and (seed_score <= 0.0 or len(selected) >= 2):
            continue
        if (
            file_path and file_counts.get(file_path, 0) >= max_per_file
        ) or (
            not reserved_graph_lane and not explicit_target
            and any(
                code_candidate_similarity(terms, other) >= CODE_DIVERSITY_THRESHOLD
                for other in selected_terms
            )
        ):
            deferred.append(item)
            continue
        selected.append(item)
        selected_terms.append(terms)
        if file_path:
            file_counts[file_path] = file_counts.get(file_path, 0) + 1
        if len(selected) >= limit:
            return selected
    if focused_candidates:
        return selected[:limit]
    selected.extend(deferred[: max(0, limit - len(selected))])
    return selected[:limit]


def filter_query_role_candidates(
    items: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    generated_filtered = filter_generated_candidates(items)
    language_filtered = filter_explicit_language_candidates(
        generated_filtered, positive_retrieval_query(query)
    )
    role_filtered = filter_excluded_example_candidates(language_filtered, query)
    opaque_filtered = filter_opaque_identifier_candidates(role_filtered, query)
    if opaque_filtered != role_filtered:
        return opaque_filtered
    if not behavior_owner_query(query) or entity_definition_query(query):
        return role_filtered
    filtered = [
        item for item in role_filtered
        if not data_entity_path(str(item.get("file_path") or ""))
    ]
    return filtered if filtered else role_filtered


def filter_excluded_example_candidates(
    items: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    if not excluded_result_roles(query):
        return items
    filtered = [
        item for item in items
        if not example_candidate_path(str(item.get("file_path") or ""))
    ]
    return filtered or items


def example_candidate_path(file_path: str) -> bool:
    normalized = f"/{file_path.casefold().strip('/')}"
    name = normalized.rsplit("/", 1)[-1]
    directories = ("/example/", "/examples/", "/sample/", "/samples/")
    return any(marker in normalized for marker in directories) or any(
        marker in name for marker in ("demo", "example", "sample")
    )


def filter_opaque_identifier_candidates(
    items: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    identifiers = {value.casefold() for value in OPAQUE_IDENTIFIER_RE.findall(query)}
    if not identifiers:
        return items
    exact = [
        item for item in items
        if identifiers & opaque_identifiers_in_candidate(item)
    ]
    if exact:
        return exact
    return [item for item in items if is_graph_neighbor(item)]


def opaque_identifiers_in_candidate(item: dict[str, Any]) -> set[str]:
    values = [
        item.get("file_path"), item.get("symbol"), item.get("summary"),
        item.get("business_summary"), item.get("business_terms"),
        item.get("search_terms"),
    ]
    text = " ".join(str(value or "") for value in values)
    return {value.casefold() for value in OPAQUE_IDENTIFIER_RE.findall(text)}


def behavior_owner_query(query: str) -> bool:
    lowered = query.casefold()
    markers = (
        " owner", " page", " view", "click", "handler", "render", "route",
        "sql", "formatter", "component", "页面", "视图", "点击", "渲染",
        "路由", "跳转", "组件", "调用",
    )
    named_role = re.search(
        r"\b[A-Z][A-Za-z0-9_$]*(?:Page|View|Service|Controller)\b",
        query,
    )
    return bool(named_role) or any(marker in lowered for marker in markers)


def entity_definition_query(query: str) -> bool:
    lowered = query.casefold()
    markers = (
        "entity definition", "record definition", "data model", "entity fields",
        "实体定义", "数据模型", "记录定义",
    )
    return any(marker in lowered for marker in markers)


def data_entity_path(file_path: str) -> bool:
    normalized = f"/{file_path.casefold().strip('/')}"
    return "/entities/" in normalized


def interleave_graph_candidate(
    items: list[dict[str, Any]],
    explicit_paths: set[str],
) -> list[dict[str, Any]]:
    if len(items) < 2 or is_graph_neighbor(items[0]) or len(explicit_paths) >= 2:
        return items
    seed_score = float(items[0].get("score") or 0.0)
    component_flow = [
        item for item in items[1:]
        if is_component_flow_neighbor(item)
        and float(item.get("score") or 0.0) >= seed_score * 0.5
    ][:2]
    if component_flow:
        selected_ids = {id(item) for item in component_flow}
        return [
            items[0],
            *component_flow,
            *[item for item in items[1:] if id(item) not in selected_ids],
        ]
    for index, item in enumerate(items[1:], start=1):
        if (
            is_graph_neighbor(item)
            and float(item.get("score") or 0.0) >= seed_score * 0.5
        ):
            return [items[0], item, *items[1:index], *items[index + 1:]]
    return items


def protected_explicit_paths(items: list[dict[str, Any]], query: str) -> set[str]:
    if not query.strip() or not items:
        return set()
    padded_query = f" {query.casefold()} "
    if (
        behavior_marker_terms(query)
        or any(marker in padded_query for marker in NEGATIVE_PATH_MARKERS)
    ):
        return set()
    seed_score = float(items[0].get("score") or 0.0)
    matches_by_path: dict[str, set[str]] = {}
    for item in items:
        file_path = str(item.get("file_path") or "")
        matches = explicit_path_segments(query, file_path)
        if (
            file_path
            and not is_graph_neighbor(item)
            and float(item.get("score") or 0.0) >= seed_score * 0.75
            and matches
        ):
            matches_by_path.setdefault(file_path, set()).update(matches)
    strong = {
        file_path for file_path, matches in matches_by_path.items()
        if len(matches) >= 2
    }
    if len(strong) >= 2:
        return strong
    return set(matches_by_path) if len(matches_by_path) >= 3 else set()


def explicit_path_segments(query: str, file_path: str) -> set[str]:
    raw_query = [*tokenize(query), *identifier_tokens(query)]
    query_terms = {
        term.casefold()
        for token in raw_query
        for term in (token, *english_query_variants(token))
        if term.casefold() not in CODE_DIVERSITY_GENERIC_TERMS
        and term.casefold() not in EXPLICIT_PATH_GENERIC_TERMS
    }
    path_terms = {
        token.casefold()
        for token in [*tokenize(file_path), *identifier_tokens(file_path)]
        if token
    }
    return query_terms & path_terms


def is_graph_neighbor(item: dict[str, Any]) -> bool:
    reasons = {str(reason) for reason in item.get("match_reasons") or []}
    return (
        "graph_neighbor" in reasons
        and not reasons & DIRECT_GRAPH_OVERRIDE_REASONS
    )


def is_component_flow_neighbor(item: dict[str, Any]) -> bool:
    reasons = {str(reason) for reason in item.get("match_reasons") or []}
    return bool(
        reasons
        & {"graph_relation:passes_property", "graph_relation:renders_component"}
    )


def code_candidate_terms(item: dict[str, Any]) -> set[str]:
    value = f"{item.get('file_path') or ''} {item.get('symbol') or ''}"
    return {
        token
        for token in [*tokenize(value), *identifier_tokens(value)]
        if len(token) > 1 and token not in CODE_DIVERSITY_GENERIC_TERMS
    }


def code_candidate_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
