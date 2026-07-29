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
    if any(item.get("graph_neighbor") for item in anchors):
        return anchors
    primary = evidence.get("primary")
    if evidence.get("certainty") != "bounded" or not isinstance(primary, dict):
        return anchors
    path = str(primary.get("file_path") or "").strip()
    source_range = primary.get("source_range")
    if not path or not isinstance(source_range, dict):
        return anchors
    focused = [item for item in anchors if str(item.get("file_path") or "") == path]
    return focused or anchors
