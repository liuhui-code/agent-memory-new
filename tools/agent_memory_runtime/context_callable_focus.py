# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any
import re

from .query_language import (
    COMPARISON_CLAUSE_RE, NEGATIVE_RESULT_CLAUSE_RE,
    excluded_result_identifiers, result_alternative_query,
)
from .query_target_scope import classify_target_scope

from .query_explicit_owner_certificate import CertifiedPortfolio
from .query_certified_portfolio_bounds import certified_projection
from .query_code_selection import explicitly_named_candidate


def focus_callable_anchors(
    anchors: list[dict[str, Any]], evidence: Any, path_activated: Any,
    query: str = "",
) -> list[dict[str, Any]]:
    """Narrow compact source anchors only for a bounded callable-local query."""
    activated = path_scope_activated(path_activated)
    if exclusive_path_scope(path_activated) or any(
        item.get("log_identity_match") for item in anchors
    ):
        return anchors
    if not isinstance(evidence, dict):
        return anchors
    primary = evidence.get("primary")
    portfolio = evidence.get("passage_portfolio")
    if not isinstance(primary, dict):
        return anchors
    # Recognize this provenance before every legacy consumer, including the
    # uncertain-primary path. JSON/dict copies lose private authority, not the
    # provenance marker; they must never inherit older cross-file permission.
    indexed_owner = isinstance(portfolio, dict) and "indexed_explicit_owner_methods" in (
        portfolio.get("selection_basis") or []
    )
    if indexed_owner or isinstance(portfolio, CertifiedPortfolio):
        if (not indexed_owner or not isinstance(portfolio, CertifiedPortfolio)
                or portfolio.get("state") != "composed"
                or evidence.get("certainty") != "bounded"
                or not portfolio.valid_for(primary) or primary.get("typed_contract_match")
                or any(item.get("graph_neighbor") or item.get("graph_relation") or item.get("identity_match") for item in anchors)):
            return anchors
        projected = [callable_anchor(member, None) for member in portfolio["members"]]
        return merge_incomplete_path(projected, anchors, path_activated) if activated else projected
    if evidence.get("certainty") != "bounded":
        weak_uncertain = (evidence.get("certainty") == "uncertain"
                          and primary.get("typed_contract_weak") is True
                          and primary_range_covered(anchors, primary))
        return (
            reserve_uncertain_primary(anchors, primary)
            if activated or (primary.get("typed_contract_match")
                             and not weak_uncertain) else anchors
        )
    if multiple_requested_anchors_present(anchors, evidence, query):
        return anchors
    composed = isinstance(portfolio, dict) and portfolio.get("state") == "composed"
    cross_file = composed and "explicit_cross_file_targets" in set(
        portfolio.get("selection_basis") or []
    )
    if cross_file and activated:
        projected = portfolio_anchors(portfolio, anchors)
        return merge_incomplete_path(projected, anchors, path_activated)
    if activated:
        return anchors
    preferred_artifact = preferred_competing_artifact(primary)
    if (
        any(item.get("graph_neighbor") for item in anchors)
        and not primary.get("target_owner_kind_match")
        and not preferred_artifact
    ):
        return anchors
    path = str(primary.get("file_path") or "").strip()
    source_range = primary.get("source_range")
    if not path or not isinstance(source_range, dict):
        return anchors
    focused = [item for item in anchors if str(item.get("file_path") or "") == path]
    if primary.get("typed_contract_match") or primary.get("source_operation_match"):
        return [callable_anchor(primary, focused[0] if focused else None)]
    if composed and cross_file:
        retained = same_owner_retained_portfolio(portfolio, primary)
        if retained is not None:
            return retained_owner_anchors(retained, focused)
    if composed and not cross_file:
        if certified_projection(portfolio, primary):
            return retained_owner_anchors(portfolio, focused)
        return portfolio_anchors(portfolio, focused)
    if not primary.get("target_owner_kind_match") and not preferred_artifact:
        return focused or anchors
    return [callable_anchor(primary, focused[0] if focused else None)]


def exclusive_path_scope(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if not isinstance(value, dict) or not value.get("activated"):
        return False
    if value.get("wrapped_log_evidence"):
        return True
    return any(
        isinstance(item, dict)
        and item.get("complete") is True
        and item.get("truncated") is not True
        for item in value.get("path_candidates") or []
    )


def path_scope_activated(value: Any) -> bool:
    return value if isinstance(value, bool) else bool(
        isinstance(value, dict) and value.get("activated")
    )


def merge_incomplete_path(
    projected: list[dict[str, Any]],
    anchors: list[dict[str, Any]],
    path_context: Any,
) -> list[dict[str, Any]]:
    if not isinstance(path_context, dict) or not path_context.get("activated"):
        return projected
    paths = {str(item.get("file_path") or "") for item in projected}
    return [
        *projected,
        *(item for item in anchors if str(item.get("file_path") or "") not in paths),
    ]


def preferred_competing_artifact(primary: dict[str, Any]) -> bool:
    if not primary.get("artifact_role_competition") or not primary.get("artifact_role_representative"):
        return False
    reasons = set(primary.get("reasons") or [])
    if not reasons & {"exact_function", "exact_identifier", "exact_symbol"}:
        return False
    role = str(primary.get("artifact_role") or "")
    intent = str(primary.get("artifact_query_intent") or "")
    return (
        (intent == "implementation" and role == "production")
        or (intent == "validation" and role == "test")
    )


def portfolio_anchors(
    portfolio: dict[str, Any], existing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    by_path = {
        str(item.get("file_path") or ""): item for item in existing
        if item.get("file_path")
    }
    for index, member in enumerate(portfolio.get("members") or []):
        if not isinstance(member, dict) or not isinstance(member.get("source_range"), dict):
            continue
        result.append(callable_anchor(
            member, by_path.get(str(member.get("file_path") or "")),
        ))
    return result or existing


def primary_range_covered(anchors: list[dict[str, Any]], primary: dict[str, Any]) -> bool:
    """Check display coverage only, not identity or source-reading authority."""
    source_range = primary.get("source_range")
    path = str(primary.get("file_path") or "")
    if not path or not valid_retained_range(source_range):
        return False
    return any(str(anchor.get("file_path") or "") == path
               and valid_retained_range(anchor)
               and anchor["start_line"] <= source_range["start_line"]
               and source_range["end_line"] <= anchor["end_line"] for anchor in anchors)


def reserve_uncertain_primary(
    anchors: list[dict[str, Any]], primary: dict[str, Any],
) -> list[dict[str, Any]]:
    path = str(primary.get("file_path") or "")
    source_range = primary.get("source_range")
    if not path or not isinstance(source_range, dict):
        return anchors
    existing = next(
        (item for item in anchors if str(item.get("file_path") or "") == path), None,
    )
    reservation = callable_anchor(primary, existing)
    remaining = [item for item in anchors if str(item.get("file_path") or "") != path]
    return [*remaining[:1], reservation, *remaining[1:]] if remaining else [reservation]


def callable_anchor(
    primary: dict[str, Any],
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    source_range = primary["source_range"]
    if (isinstance(existing, dict) and valid_retained_range(existing)
            and valid_retained_range(source_range)
            and not existing["start_line"] <= source_range["start_line"] <= source_range["end_line"] <= existing["end_line"]):
        existing = None
    anchor = dict(existing or {
        "source": "callable_evidence",
        "file_path": primary["file_path"],
        "symbol_type": "method",
    })
    anchor["symbol"] = primary.get("symbol") or anchor.get("symbol")
    for key in ("start_line", "end_line"):
        if isinstance(source_range.get(key), int):
            anchor[key] = source_range[key]
    anchor["callable_focus"] = True
    return anchor


def same_owner_retained_portfolio(portfolio: dict[str, Any], primary: dict[str, Any]) -> dict[str, Any] | None:
    """Consume only the producer's certified same-owner subset, never other files."""
    if "same_owner_named_retention" not in set(portfolio.get("selection_basis") or []):
        return None
    path, owner = primary.get("file_path"), primary.get("owner_name")
    if not path or not owner or not valid_retained_range(primary.get("source_range")):
        return None
    members = portfolio.get("members")
    if not isinstance(members, list):
        return None
    selected: dict[str, dict[str, Any]] = {}
    spans = set()
    for member in members:
        if not isinstance(member, dict) or member.get("file_path") != path or member.get("owner_name") != owner:
            continue
        symbol, source_range = member.get("symbol"), member.get("source_range")
        if not isinstance(symbol, str) or not symbol or not valid_retained_range(source_range):
            return None
        span = (source_range["start_line"], source_range["end_line"])
        if symbol in selected:
            previous = selected[symbol]["source_range"]
            if span != (previous["start_line"], previous["end_line"]):
                return None
            continue
        selected[symbol] = member
        spans.add(span)
    if len(selected) < 2 or len(spans) < 2 or primary.get("symbol") not in selected:
        return None
    return {**portfolio, "members": list(selected.values())}


def valid_retained_range(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    start, end = value.get("start_line"), value.get("end_line")
    return type(start) is int and type(end) is int and 0 < start <= end


def retained_owner_anchors(portfolio: dict[str, Any], existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    members = complete_retained_members(portfolio["members"])
    for member in members:
        source_range = member["source_range"]
        matched = next((anchor for anchor in existing if (
            anchor.get("file_path") == member["file_path"]
            and anchor.get("symbol") == member["symbol"]
            and type(anchor.get("start_line")) is int
            and type(anchor.get("end_line")) is int
            and anchor["start_line"] == source_range["start_line"]
            and anchor["end_line"] == source_range["end_line"]
        )), None)
        result.append(callable_anchor(member, matched))
    return result


def complete_retained_members(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded = []
    for member in members:
        window = member["source_range"]
        bounds = {"start_line": window.get("callable_start_line"), "end_line": window.get("callable_end_line")}
        if not valid_retained_range(bounds) or not valid_retained_range(window):
            return members
        if not bounds["start_line"] <= window["start_line"] <= window["end_line"] <= bounds["end_line"]:
            return members
        expanded.append({**member, "source_range": {**window, **bounds}})
    return expanded


def multiple_requested_anchors_present(
    anchors: list[dict[str, Any]], evidence: dict[str, Any], query: str,
) -> bool:
    """Decline narrowing existing source, without granting portfolio projection."""
    # Retrieval adds tokens from excluded/comparison clauses. Those synthesized
    # terms are useful recall hints, but cannot authorize a requested owner.
    positive = COMPARISON_CLAUSE_RE.sub(" ", NEGATIVE_RESULT_CLAUSE_RE.sub(
        " ", result_alternative_query(query),
    ))
    excluded = excluded_result_identifiers(query)
    owners: dict[str, set[str]] = {}
    if (classify_target_scope(positive).get("kind") == "multiple"
            and not re.search(r"[`\"']", positive)
            and not re.search(r"\b(?:strings?|text|literals?)\b|字符串|字面量|文本", positive, re.I)):
        for anchor in anchors:
            name = str(anchor.get("symbol") or "")
            if (anchor.get("symbol_type") in {"class", "component", "struct", "interface"}
                    and valid_retained_range(anchor) and name
                    and re.sub(r"[^a-z0-9]", "", name.casefold()) not in excluded
                    and re.search(r"(?<![\w$.])" + re.escape(name) + r"(?![\w$.])", positive)):
                owners.setdefault(name, set()).add(str(anchor.get("file_path") or ""))
        named_paths = {next(iter(paths)) for paths in owners.values() if len(paths) == 1 and next(iter(paths))}
        if len(named_paths) >= 2:
            return True
    paths: set[str] = set()
    candidates = [evidence.get("primary"), *(evidence.get("alternatives") or [])]
    for candidate in candidates:
        if not isinstance(candidate, dict) or not explicitly_named_candidate(candidate, query):
            continue
        span = candidate.get("source_range")
        if not valid_retained_range(span):
            continue
        path = candidate.get("file_path")
        if any(
            anchor.get("file_path") == path and valid_retained_range(anchor)
            and anchor["start_line"] <= span["start_line"] <= span["end_line"] <= anchor["end_line"]
            for anchor in anchors
        ):
            paths.add(str(path))
    return len(paths) >= 2
