# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .log_event_identity import event_match


OWNER_RADIUS = 8
MAX_OWNER_RANGES = 2


def bind_event_owner_ranges(
    code_anchors: list[dict[str, Any]],
    log_anchors: list[dict[str, Any]],
    query: Any,
) -> list[dict[str, Any]]:
    """Seed source passages from high-confidence selected log event owners."""
    strong_logs = [
        item for item in log_anchors
        if item.get("file_path") and event_match(item, query)["priority"] > 0
    ]
    if not strong_logs:
        return code_anchors
    by_file: dict[str, list[dict[str, Any]]] = {}
    for item in strong_logs:
        by_file.setdefault(str(item["file_path"]), []).append(item)
    for anchor in code_anchors:
        matching = by_file.get(str(anchor.get("file_path") or ""), [])
        if matching:
            anchor["source_ranges"] = merge_owner_ranges(anchor, matching)
    return code_anchors


def merge_owner_ranges(
    anchor: dict[str, Any], logs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing = valid_ranges(anchor.get("source_ranges"))
    owners = []
    for log in logs[:MAX_OWNER_RANGES]:
        owner = owner_range(log, existing)
        if owner and owner not in owners:
            owners.append(owner)
    return [*owners, *existing]


def owner_range(
    log: dict[str, Any], ranges: list[dict[str, Any]],
) -> dict[str, Any]:
    function = str(log.get("function") or "").strip()
    callable_range = next(
        (
            item for item in ranges
            if function and str(item.get("symbol") or "") == function
        ),
        None,
    )
    if callable_range:
        return {
            **callable_range,
            "selection_reason": "selected_log_event_owner",
            "focus_line": valid_line(log.get("line")),
        }
    line = valid_line(log.get("line"))
    if not line:
        return {}
    return {
        "symbol": function or None,
        "start_line": max(1, line - OWNER_RADIUS),
        "end_line": line + OWNER_RADIUS,
        "focus_line": line,
        "selection_reason": "selected_log_event_owner",
    }


def valid_ranges(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [
        item for item in value
        if isinstance(item, dict)
        and isinstance(item.get("start_line"), int)
        and isinstance(item.get("end_line"), int)
        and 0 < item["start_line"] <= item["end_line"]
    ]


def valid_line(value: Any) -> int | None:
    return value if isinstance(value, int) and value > 0 else None
