# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Bind stored callable identities to their own ranges, without public ID fields."""
from __future__ import annotations
from typing import Any


def pair(item: dict[str, Any]) -> tuple[str, str]:
    return str(item.get('file_path') or ''), str(item.get('symbol') or '')


def valid_window(item: dict[str, Any]) -> bool:
    start, end = item.get('start_line'), item.get('end_line')
    return type(start) is int and type(end) is int and 0 < start <= end


def resolve_candidate_range(candidate: dict[str, Any], ranges: list[dict[str, Any]]) -> dict[str, Any] | None:
    key = pair(candidate)
    if not all(key):
        return None
    matches = [row for row in ranges if pair(row) == key]
    identifier = candidate.get('symbol_id')
    if identifier is not None:
        if type(identifier) is not int or identifier <= 0 or not valid_window(candidate):
            return None
        matches = [row for row in matches if type(row.get('symbol_id')) is int and row['symbol_id'] == identifier]
    if len(matches) != 1 or not valid_window(matches[0]):
        return None
    selected = matches[0]
    if valid_window(candidate) and not (
        candidate['start_line'] <= selected['start_line'] <= selected['end_line'] <= candidate['end_line']
    ):
        return None
    return selected


def ambiguous_portfolio_ranges(candidates: list[dict[str, Any]], ranges: list[dict[str, Any]]) -> bool:
    """Only inspect candidate pairs actually eligible for composition."""
    for key in {pair(item) for item in candidates}:
        rows = [item for item in candidates if pair(item) == key]
        identities = {(item.get('symbol_id'), item.get('start_line'), item.get('end_line')) for item in rows}
        windows = [item for item in ranges if pair(item) == key]
        range_ids = {(item.get('symbol_id'), item.get('callable_start_line'), item.get('callable_end_line'),
                      item.get('start_line'), item.get('end_line')) for item in windows}
        if len(identities) > 1 or len(range_ids) > 1:
            return True
    return False
