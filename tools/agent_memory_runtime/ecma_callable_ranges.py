# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any

from .ecma_braces import block_end
from .ecma_callable_headers import CONTROL_NAMES, named_callable_header


MAX_CALLBACK_HEADER_LINES = 4
MAX_CALLBACK_RANGES = 256
PROPERTY_CALLBACK_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|readonly|static)\s+)*"
    r"([A-Za-z_$][\w$]*)\s*[:=]\s*(?:async\s*)?\([^)]*\)"
    r"(?:\s*:\s*[^=]+)?\s*=>\s*\{"
)
MEMBER_CALLBACK_RE = re.compile(r"\.(on(?:[A-Z][A-Za-z0-9_$]*)?)\s*\(")


def callable_line_ranges(lines: list[str]) -> list[dict[str, Any]]:
    """Return named and property callback ranges for TypeScript-like source."""
    return dedupe_ranges([*named_callable_ranges(lines), *property_callback_ranges(lines)])


def callable_ranges_for_language(
    lines: list[str], language: str,
) -> list[dict[str, Any]]:
    ranges = callable_line_ranges(lines)
    if language == "ArkTS":
        ranges.extend(member_callback_ranges(lines))
    return dedupe_ranges(ranges)


def callback_ranges_for_language(
    lines: list[str], language: str,
) -> list[dict[str, Any]]:
    ranges = property_callback_ranges(lines)
    if language == "ArkTS":
        ranges.extend(member_callback_ranges(lines))
    return dedupe_ranges(ranges)


def named_callable_ranges(lines: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, _line in enumerate(lines):
        header = named_callable_header(lines, index)
        if header is None:
            continue
        result.append(source_range(
            header.name, index, block_end(lines, index), "callable_mechanism_window",
        ))
    return result


def property_callback_ranges(lines: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        match = PROPERTY_CALLBACK_RE.match(line)
        if match is None:
            continue
        result.append(source_range(
            match.group(1), index, block_end(lines, index), "ecma_property_callback_window",
        ))
        if len(result) >= MAX_CALLBACK_RANGES:
            break
    return result


def member_callback_ranges(lines: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        match = MEMBER_CALLBACK_RE.search(line)
        if match is None:
            continue
        arrow_line = callback_arrow_line(lines, index, match.start())
        if arrow_line is None:
            continue
        result.append(source_range(
            match.group(1), index, block_end(lines, arrow_line), "arkts_dsl_callback_window",
        ))
        if len(result) >= MAX_CALLBACK_RANGES:
            break
    return result


def callback_arrow_line(
    lines: list[str], start: int, start_column: int = 0,
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


def callable_symbols_by_line(
    lines: list[str], language: str,
) -> dict[int, str]:
    ranges = callable_ranges_for_language(lines, language)
    result: dict[int, str] = {}
    for line in range(1, len(lines) + 1):
        owners = [
            item for item in ranges
            if int(item["start_line"]) <= line <= int(item["end_line"])
        ]
        if owners:
            selected = min(owners, key=lambda item: (
                int(item["end_line"]) - int(item["start_line"]),
                -int(item["start_line"]),
            ))
            result[line] = str(selected["symbol"])
    return result


def source_range(symbol: str, start: int, end: int, reason: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "start_line": start + 1,
        "end_line": end + 1,
        "selection_reason": reason,
    }


def dedupe_ranges(ranges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[int, int, str]] = set()
    for item in ranges:
        key = (int(item["start_line"]), int(item["end_line"]), str(item["symbol"]))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
