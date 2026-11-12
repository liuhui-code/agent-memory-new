# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Conservative exception to per-file diversity for explicitly named owner methods."""
from __future__ import annotations

import unicodedata
from typing import Any

from .query_language import COMPARISON_CLAUSE_RE, NEGATIVE_RESULT_CLAUSE_RE
from .query_target_scope import SINGLE_TARGET_RE


def identifier_char(value: str) -> bool:
    return value.isalnum() or value in "_$" or unicodedata.category(value).startswith("M")


def directly_named(symbol: str, text: str) -> bool:
    if not symbol or symbol[0].isdigit() or not all(identifier_char(c) for c in symbol):
        return False
    start = 0
    while (offset := text.find(symbol, start)) >= 0:
        end = offset + len(symbol)
        if (offset == 0 or not identifier_char(text[offset - 1])) and (
            end == len(text) or not identifier_char(text[end])
        ):
            return True
        start = offset + 1
    return False


def key(item: dict[str, Any]) -> tuple[str, str]:
    return str(item.get("file_path") or ""), str(item.get("symbol") or "")


def valid_range(item: dict[str, Any]) -> bool:
    start, end = item.get("start_line"), item.get("end_line")
    return type(start) is int and type(end) is int and 0 < start <= end


def retain_named_owner_methods(
    query: str,
    primary: dict[str, Any],
    candidates: list[dict[str, Any]],
    ranges: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
    original: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    # No query expansion, retained exclusion terms, or empty-text fallback here.
    text = COMPARISON_CLAUSE_RE.sub(" ", NEGATIVE_RESULT_CLAUSE_RE.sub(" ", query))
    if SINGLE_TARGET_RE.search(text) or not primary.get("owner_name") or not all(key(primary)):
        return original
    named: dict[tuple[str, str], dict[str, Any]] = {}
    for item in candidates:
        if not directly_named(key(item)[1], text):
            continue
        identity = key(item)
        if not all(identity) or not item.get("owner_name"):
            return original
        previous = named.get(identity)
        if previous is not None and any(
            previous.get(field) != item.get(field) for field in ("owner_name", "start_line", "end_line")
        ):
            return original
        named[identity] = item
    if not 2 <= len(named) <= limit:
        return original
    eligible_keys = {key(item) for item in eligible}
    if not set(named).issubset(eligible_keys):
        return original
    for identity in named:
        matches = [item for item in ranges if key(item) == identity]
        if not matches or not all(valid_range(item) for item in matches):
            return original
        if len({(item["start_line"], item["end_line"]) for item in matches}) != 1:
            return original
    owner_keys = {
        identity for identity, item in named.items()
        if identity[0] == key(primary)[0] and item["owner_name"] == primary["owner_name"]
    }
    original_keys = {key(item) for item in original}
    if len(owner_keys) < 2 or key(primary) not in owner_keys:
        return original
    # Every other explicitly named identity must already be selected. Never
    # promote a cross-file (or another owner's same-file) target via this fix.
    if not (set(named) - owner_keys).issubset(original_keys):
        return original
    result = [item for item in eligible if key(item) in named]
    result.extend(item for item in original if key(item) not in named)
    return preserve_callable_bounds(result[:limit], owner_keys, named, ranges)


def preserve_callable_bounds(
    members: list[dict[str, Any]],
    owner_keys: set[tuple[str, str]],
    named: dict[tuple[str, str], dict[str, Any]],
    ranges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    certified = {}
    for identity in owner_keys:
        candidate = named[identity]
        if not valid_range(candidate):
            return members
        matches = [row for row in ranges if key(row) == identity]
        if not matches:
            return members
        for row in matches:
            bounds = {"start_line": row.get("callable_start_line"), "end_line": row.get("callable_end_line")}
            if not valid_range(bounds) or not valid_range(row):
                return members
            if (bounds["start_line"], bounds["end_line"]) != (candidate["start_line"], candidate["end_line"]):
                return members
            if not bounds["start_line"] <= row["start_line"] <= row["end_line"] <= bounds["end_line"]:
                return members
        certified[identity] = {"callable_start_line": candidate["start_line"], "callable_end_line": candidate["end_line"]}
    return [
        {**member, "source_range": {**member["source_range"], **certified[key(member)]}}
        if key(member) in certified else member
        for member in members
    ]
