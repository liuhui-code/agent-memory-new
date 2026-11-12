# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Preserve typed bounds only after existing same-owner portfolio admission."""
from __future__ import annotations
from typing import Any
from .query_same_owner_retention import key, valid_range, preserve_callable_bounds

MARKER = "certified_same_owner_callable_bounds"


def same_owner_members(members: Any, primary: dict[str, Any]) -> bool:
    if not isinstance(members, list) or not 2 <= len(members) <= 3:
        return False
    path, symbol = key(primary)
    owner = primary.get("owner_name")
    if not path or not symbol or not isinstance(owner, str) or not owner.strip():
        return False
    seen = set()
    for member in members:
        if not isinstance(member, dict):
            return False
        identity = key(member)
        if (not all(identity) or identity in seen or identity[0] != path
                or member.get("owner_name") != owner
                or not isinstance(member.get("source_range"), dict)
                or not valid_range(member["source_range"])):
            return False
        seen.add(identity)
    if (path, symbol) not in seen:
        return False
    window = primary.get("source_range")
    if not isinstance(window, dict) or not valid_range(window):
        return False
    chosen = next(member["source_range"] for member in members if key(member) == (path, symbol))
    return (window["start_line"], window["end_line"]) == (chosen["start_line"], chosen["end_line"])


def certify_selected_bounds(members, primary, candidates, ranges):
    """Return None on uncertified input; never change which members were admitted."""
    if not same_owner_members(members, primary):
        return None
    selected = {}
    for member in members:
        identity = key(member)
        matches = [row for row in candidates if key(row) == identity]
        if not matches or any(not valid_range(row) or row.get("owner_name") != member["owner_name"] for row in matches):
            return None
        if len({(row["start_line"], row["end_line"]) for row in matches}) != 1:
            return None
        selected[identity] = matches[0]
        raw = [row for row in ranges if key(row) == identity]
        window = member["source_range"]
        if not raw:
            return None
        for row in raw:
            bounds = {"start_line": row.get("callable_start_line"), "end_line": row.get("callable_end_line")}
            if not valid_range(row) or not valid_range(bounds):
                return None
            if (row["start_line"], row["end_line"]) != (window["start_line"], window["end_line"]):
                return None
            if (bounds["start_line"], bounds["end_line"]) != (matches[0]["start_line"], matches[0]["end_line"]):
                return None
            if not bounds["start_line"] <= row["start_line"] <= row["end_line"] <= bounds["end_line"]:
                return None
    return preserve_callable_bounds(members, set(selected), selected, ranges)


def certified_projection(portfolio: dict[str, Any], primary: dict[str, Any]) -> bool:
    """Validate all consumer ranges explicitly; expansion helper is not a validator."""
    basis = portfolio.get("selection_basis")
    if (not isinstance(basis, list) or MARKER not in basis
            or "explicit_cross_file_targets" in basis
            or portfolio.get("state") != "composed"
            or portfolio.get("target_scope") != "multiple"
            or not same_owner_members(portfolio.get("members"), primary)):
        return False
    for member in portfolio["members"]:
        window = member["source_range"]
        bounds = {"start_line": window.get("callable_start_line"), "end_line": window.get("callable_end_line")}
        if not valid_range(bounds):
            return False
        if not bounds["start_line"] <= window["start_line"] <= window["end_line"] <= bounds["end_line"]:
            return False
    return True
