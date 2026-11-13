# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations

import re
from typing import Any

from .query_language import positive_retrieval_query
from .query_salience import salient_query_tokens
from .query_salience_score import prefix_match
from .query_target_scope import classify_target_scope
from .text import tokenize


def redundant_source_supplement(
    item: dict[str, Any], focused: list[dict[str, Any]], query: str,
) -> bool:
    """Reject only redundant non-graph salience after established method focus.

    Unknown query cardinality is not treated as single: explicit targets, quoted
    literals, novel evidence and all already-selected members remain untouched.
    Missing source evidence fails open. This does not certify a diagnosis.
    """
    if not query or classify_target_scope(query).get("kind") == "multiple":
        return False
    reasons = set(item.get("match_reasons") or [])
    if item.get("graph_depth") or any(str(reason).startswith("graph_") for reason in reasons):
        return False
    if item.get("kind") != "symbol" or not source_fields_present(item):
        return False
    for identity in (item.get("symbol"), item.get("owner_name")):
        if identity and literal_mentioned(str(identity), query):
            return False
    literals = re.findall(r"`([^`\n]+)`|\"([^\"\n]+)\"|'([^'\n]+)'", query)
    strings = str(item.get("string_evidence") or "")
    if any(literal_mentioned(next(value for value in group if value), strings) for group in literals):
        return False
    proven = [row for row in focused if (
        "multi_term_method_evidence" in (row.get("match_reasons") or [])
        and row.get("kind") == "symbol" and source_fields_present(row)
    )]
    if not proven:
        return False
    terms = salient_query_tokens(positive_retrieval_query(query))
    covered = set().union(*(source_matches(row, terms) for row in proven))
    matched = source_matches(item, terms)
    return bool(covered and matched and matched <= covered)


def source_fields_present(item: dict[str, Any]) -> bool:
    start, end = item.get("start_line"), item.get("end_line")
    return (
        type(start) is int and type(end) is int and 0 < start <= end
        and all(isinstance(item.get(key), str) for key in ("method_evidence", "string_evidence"))
    )


def source_matches(item: dict[str, Any], terms: list[str]) -> set[str]:
    evidence = set(tokenize(f"{item.get('method_evidence') or ''} {item.get('string_evidence') or ''}"))
    return {term for term in terms if any(prefix_match(term, value) for value in evidence)}


def literal_mentioned(value: str, text: str) -> bool:
    return bool(value and re.search(r"(?<![\w$])" + re.escape(value) + r"(?![\w$])", text, re.IGNORECASE))
