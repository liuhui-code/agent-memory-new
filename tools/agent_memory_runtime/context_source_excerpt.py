# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Any

from .performance_scoring import estimate_payload_tokens
from .text import query_tokens, score_text


MAX_EXCERPT_ANCHORS = 3
MAX_EXCERPTS_PER_ANCHOR = 2
MAX_EXCERPT_LINES = 40
MAX_EXCERPT_CHARS = 1500
MAX_TOTAL_EXCERPT_CHARS = 2600
TOKEN_RESERVE = 180
MAX_FOCUS_SCAN_LINES = 4000
FOCUS_RADIUS = 8
FOCUS_SCORE_RADIUS = 4
ACTION_MARKERS = (
    ".onclick", ": this.", "@prop", "await ", "if (", "foreach(",
    "pushpath", "replacepath", "loaddata", ".fileaccess",
)
UI_OPERATION_RE = re.compile(r"\.[a-z][A-Za-z0-9_$]*\s*\(")
COMPONENT_BINDING_RE = re.compile(r"\b[A-Z][A-Za-z0-9_$]*\s*\(\s*\{")


def attach_source_excerpts(
    payload: dict[str, Any],
    project_path: Any,
    token_budget: int,
) -> int:
    root = resolved_root(project_path)
    handoff = payload.get("query_handoff")
    if root is None or not isinstance(handoff, dict):
        return 0
    available_tokens = max(0, token_budget - TOKEN_RESERVE - estimate_payload_tokens(payload))
    remaining_chars = min(MAX_TOTAL_EXCERPT_CHARS, available_tokens * 3)
    if remaining_chars < 160:
        return 0
    excerpt_count = 0
    excerpt_chars = 0
    anchors = primary_anchors(handoff)
    for index, anchor in enumerate(anchors):
        source_path = safe_source_path(root, anchor.get("file_path"))
        if source_path is None:
            continue
        excerpts = []
        anchors_left = max(1, len(anchors) - index)
        anchor_remaining = min(
            MAX_EXCERPT_CHARS,
            max(160, remaining_chars // anchors_left),
        )
        for source_range in selected_ranges(
            anchor,
            source_path,
            str(payload.get("query") or ""),
        ):
            char_budget = min(anchor_remaining, remaining_chars)
            excerpt = read_excerpt(source_path, source_range, char_budget)
            if not excerpt:
                continue
            excerpts.append(excerpt)
            used = len(str(excerpt.get("content") or ""))
            remaining_chars -= used
            anchor_remaining -= used
            excerpt_chars += used
            excerpt_count += 1
            if (
                remaining_chars < 160
                or anchor_remaining < 160
                or len(excerpts) >= MAX_EXCERPTS_PER_ANCHOR
            ):
                break
        if excerpts:
            anchor["source_excerpts"] = excerpts
        if remaining_chars < 160:
            break
    if excerpt_count:
        handoff["source_excerpt_policy"] = {
            "source": "current_worktree",
            "body_persisted": False,
            "excerpt_count": excerpt_count,
            "excerpt_chars": excerpt_chars,
        }
    return excerpt_count


def has_source_excerpt_candidate(
    payload: dict[str, Any],
    project_path: Any,
) -> bool:
    root = resolved_root(project_path)
    handoff = payload.get("query_handoff")
    if root is None or not isinstance(handoff, dict):
        return False
    return any(
        safe_source_path(root, anchor.get("file_path")) is not None
        and bool(selected_ranges(anchor))
        for anchor in primary_anchors(handoff)
    )


def primary_anchors(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    anchors = handoff.get("code_anchors")
    if not isinstance(anchors, list):
        return []
    return [
        item for item in anchors
        if isinstance(item, dict) and item.get("role") == "primary"
    ][:MAX_EXCERPT_ANCHORS]


def resolved_root(value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    root = Path(value).expanduser().resolve()
    return root if root.is_dir() else None


def safe_source_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    relative = Path(value)
    if relative.is_absolute():
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def selected_ranges(
    anchor: dict[str, Any],
    source_path: Path | None = None,
    query: str = "",
) -> list[dict[str, Any]]:
    ranges = [
        item for item in anchor.get("source_ranges") or []
        if valid_range(item)
    ]
    if source_path is not None and query.strip():
        ranges = [focused_source_range(source_path, item, query) for item in ranges]
    ranges.sort(key=lambda item: (int(item["end_line"]) - int(item["start_line"]), int(item["start_line"])))
    selected: list[dict[str, Any]] = []
    for item in ranges:
        if any(overlapping_ranges(item, existing) for existing in selected):
            continue
        selected.append(item)
        if len(selected) >= MAX_EXCERPTS_PER_ANCHOR:
            break
    return selected


def focused_source_range(
    path: Path,
    source_range: dict[str, Any],
    query: str,
) -> dict[str, Any]:
    terms = query_tokens(query)
    if not terms:
        return source_range
    lines: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line_number > MAX_FOCUS_SCAN_LINES:
                    break
                lines.append(line)
    except OSError:
        return source_range
    line_scores = [score_text(terms, line) for line in lines]
    best_line = 0
    best_score = 0
    for index, line in enumerate(lines):
        start = max(0, index - FOCUS_SCORE_RADIUS)
        end = min(len(lines), index + FOCUS_SCORE_RADIUS + 1)
        term_score = sum(line_scores[start:end])
        score = term_score * 10 + source_behavior_bonus(line, term_score)
        if term_score and score > best_score:
            best_line = index + 1
            best_score = score
    if not best_line:
        return source_range
    start = max(1, best_line - FOCUS_RADIUS)
    end = best_line + FOCUS_RADIUS
    result = {**source_range, "start_line": start, "end_line": end}
    if not int(source_range["start_line"]) <= best_line <= int(source_range["end_line"]):
        result.pop("symbol", None)
    result["selection_reason"] = "query_term_window"
    return result


def source_behavior_bonus(line: str, term_score: int) -> int:
    if not term_score:
        return 0
    lowered = line.casefold()
    bonus = 2 if any(marker in lowered for marker in ACTION_MARKERS) else 0
    if UI_OPERATION_RE.search(line):
        bonus += 5
    if COMPONENT_BINDING_RE.search(line) or re.search(r"\b[a-z][A-Za-z0-9_$]*\s*:\s*this\.", line):
        bonus += 4
    return bonus


def valid_range(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("start_line"), int)
        and isinstance(value.get("end_line"), int)
        and 0 < value["start_line"] <= value["end_line"]
    )


def overlapping_ranges(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return not (
        int(first["end_line"]) < int(second["start_line"])
        or int(second["end_line"]) < int(first["start_line"])
    )


def read_excerpt(
    path: Path,
    source_range: dict[str, Any],
    char_budget: int,
) -> dict[str, Any]:
    start = int(source_range["start_line"])
    requested_end = int(source_range["end_line"])
    line_end = min(requested_end, start + MAX_EXCERPT_LINES - 1)
    lines: list[str] = []
    actual_end = start - 1
    char_truncated = False
    used_chars = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line_number < start:
                    continue
                if line_number > line_end:
                    break
                if "\x00" in line:
                    return {}
                value = line.rstrip("\r\n")
                separator = 1 if lines else 0
                if used_chars + len(value) + separator > char_budget:
                    char_truncated = True
                    break
                lines.append(value)
                used_chars += len(value) + separator
                actual_end = line_number
    except OSError:
        return {}
    if not lines:
        return {}
    return {
        "symbol": source_range.get("symbol"),
        "start_line": start,
        "end_line": actual_end,
        "content": "\n".join(lines),
        "source": "current_worktree",
        "selection_reason": source_range.get("selection_reason") or "anchor_range",
        "truncated": char_truncated or actual_end < requested_end,
    }


def redact_source_excerpt_bodies(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = deepcopy(payload)
    handoff = sanitized.get("query_handoff")
    if not isinstance(handoff, dict):
        return sanitized
    for anchor in handoff.get("code_anchors") or []:
        if not isinstance(anchor, dict):
            continue
        excerpts = anchor.pop("source_excerpts", [])
        metadata = [excerpt_metadata(item) for item in excerpts if isinstance(item, dict)]
        if metadata:
            anchor["source_excerpt_metadata"] = metadata
    return sanitized


def excerpt_metadata(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item[key]
        for key in (
            "symbol", "start_line", "end_line", "source", "selection_reason", "truncated",
        )
        if item.get(key) not in (None, "")
    }
