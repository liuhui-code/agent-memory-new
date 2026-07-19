# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any

from .semantic_ecma import block_end, callable_line_ranges


DSL_CALLBACK_RE = re.compile(r"\.([a-z][A-Za-z0-9_$]*)\s*\(")
MAX_CALLBACK_HEADER_LINES = 4


def arkts_line_ranges(lines: list[str]) -> list[dict[str, Any]]:
    """Return named callables plus bounded ArkUI arrow-callback ranges."""
    ranges = callable_line_ranges(lines)
    ranges.extend(dsl_callback_ranges(lines))
    return dedupe_ranges(ranges)


def dsl_callback_ranges(lines: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        match = DSL_CALLBACK_RE.search(line)
        if match is None:
            continue
        arrow_line = callback_arrow_line(lines, index, match.start())
        if arrow_line is None:
            continue
        result.append({
            "symbol": match.group(1),
            "start_line": index + 1,
            "end_line": block_end(lines, arrow_line) + 1,
            "selection_reason": "arkts_dsl_callback_window",
        })
    return result


def callback_arrow_line(
    lines: list[str],
    start: int,
    start_column: int = 0,
) -> int | None:
    stop = min(len(lines), start + MAX_CALLBACK_HEADER_LINES)
    balance = 0
    for index in range(start, stop):
        segment = lines[index][start_column:] if index == start else lines[index]
        arrow = segment.find("=>")
        prefix = segment[:arrow] if arrow >= 0 else segment
        balance += prefix.count("(") - prefix.count(")")
        if arrow >= 0 and "{" in segment[arrow:] and balance > 0:
            return index
        if balance <= 0:
            return None
    return None


def dedupe_ranges(ranges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[int, int, str]] = set()
    for item in ranges:
        key = (
            int(item["start_line"]),
            int(item["end_line"]),
            str(item.get("symbol") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
