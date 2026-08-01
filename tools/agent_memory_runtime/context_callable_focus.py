# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


def focus_callable_anchors(
    anchors: list[dict[str, Any]], evidence: Any, path_activated: bool,
) -> list[dict[str, Any]]:
    """Narrow compact source anchors only for a bounded callable-local query."""
    if path_activated or any(item.get("log_identity_match") for item in anchors):
        return anchors
    if not isinstance(evidence, dict):
        return anchors
    primary = evidence.get("primary")
    if evidence.get("certainty") != "bounded" or not isinstance(primary, dict):
        return anchors
    if (
        any(item.get("graph_neighbor") for item in anchors)
        and not primary.get("target_owner_kind_match")
    ):
        return anchors
    path = str(primary.get("file_path") or "").strip()
    source_range = primary.get("source_range")
    if not path or not isinstance(source_range, dict):
        return anchors
    focused = [item for item in anchors if str(item.get("file_path") or "") == path]
    if not primary.get("target_owner_kind_match"):
        return focused or anchors
    return [callable_anchor(primary, focused[0] if focused else None)]


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
