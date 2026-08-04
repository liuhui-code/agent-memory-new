# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


def focus_callable_anchors(
    anchors: list[dict[str, Any]], evidence: Any, path_activated: Any,
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
    if evidence.get("certainty") != "bounded":
        return (
            reserve_uncertain_primary(anchors, primary)
            if activated else anchors
        )
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
    if composed and not cross_file:
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
