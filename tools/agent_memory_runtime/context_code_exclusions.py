# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Conservative post-cap code projection; never filter log or path evidence."""
from __future__ import annotations
from typing import Any
from .context_anchor_selection import exact_log_identity
from .context_directory_role import excluded_directory_role
from .query_language import NEGATIVE_RESULT_CLAUSE_RE, excluded_code_candidate

QUOTATION_CHARACTERS = frozenset('"\'`“”‘’')


def project_code_exclusions(
    anchors: list[dict[str, Any]], query: str,
    raw_candidates: list[dict[str, Any]], raw_logs: list[dict[str, Any]],
    path_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Remove a strict subset of rendered code results, preserving all conflicts."""
    if not anchors or not NEGATIVE_RESULT_CLAUSE_RE.search(query):
        return anchors
    if any(char in query for char in QUOTATION_CHARACTERS):
        return anchors
    if path_context.get("activated") or path_context.get("path_candidates"):
        return anchors
    if any(exact_log_identity(item, query) for item in raw_logs):
        return anchors
    if any(any(item.get(flag) for flag in (
        "log_identity_match", "identity_match", "graph_neighbor", "graph_relation",
    )) for item in raw_candidates):
        return anchors
    excluded = []
    for anchor in anchors:
        if not isinstance(anchor, dict):
            return anchors
        path = anchor.get("file_path")
        if not isinstance(path, str) or not path.strip():
            return anchors
        members = [item for item in raw_candidates if item.get("file_path") == path]
        if not members:
            return anchors
        decision = excluded_code_candidate(query, anchor) or excluded_directory_role(query, anchor)
        if any((excluded_code_candidate(query, item) or excluded_directory_role(query, item)) != decision for item in members):
            return anchors
        if "source_ranges" in anchor:
            ranges = anchor["source_ranges"]
            if not isinstance(ranges, list):
                return anchors
            symbols = {item.get("symbol") for item in members if isinstance(item.get("symbol"), str)}
            for source_range in ranges:
                if not isinstance(source_range, dict):
                    return anchors
                symbol = source_range.get("symbol")
                if not isinstance(symbol, str) or not symbol.strip() or symbol not in symbols:
                    return anchors
        excluded.append(decision)
    if not any(excluded) or all(excluded):
        return anchors
    return [anchor for anchor, remove in zip(anchors, excluded) if not remove]
