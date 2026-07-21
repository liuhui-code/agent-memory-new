# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .models import Project
from .text import (
    ENGLISH_QUERY_STOPWORDS,
    english_query_variants,
    tokenize,
    unique_list,
)


METHOD_EVIDENCE_QUERY_TERM_LIMIT = 16
GENERIC_METHOD_TERMS = {
    "application", "behavior", "code", "current", "find", "function",
    "functions", "locate", "method", "methods", "owner", "owners",
    "problem", "project", "source", "symbol", "symbols", "system", "user",
}


def method_evidence_focus_terms(query: str) -> list[str]:
    explicit_identifiers = unique_list([
        variant
        for token in tokenize(query)
        if token.isascii() and token.isalnum() and len(token) > 2
        and token.casefold() not in ENGLISH_QUERY_STOPWORDS
        and token.casefold() not in GENERIC_METHOD_TERMS
        for variant in method_query_variants(token.casefold())
    ])
    return explicit_identifiers[:METHOD_EVIDENCE_QUERY_TERM_LIMIT]


def method_query_variants(token: str) -> list[str]:
    variants = [token, *english_query_variants(token)]
    if token.endswith("ing") and len(token) > 6:
        stem = token[:-3]
        variants.append(stem[:-1] if len(stem) > 3 and stem[-1:] == stem[-2:-1] else stem)
    elif token.endswith("ed") and len(token) > 5:
        stem = token[:-2]
        variants.append(f"{stem[:-1]}y" if stem.endswith("i") else stem)
    return unique_list(variants)


def qualifying_method_evidence_ids(
    conn: Any,
    project: Project,
    candidate_ids: list[int],
    focus_terms: list[str],
) -> list[int]:
    if not candidate_ids:
        return []
    placeholders = ",".join("?" for _ in candidate_ids)
    rows = conn.execute(
        f"SELECT id, method_evidence FROM code_symbols "
        f"WHERE project_id = ? AND id IN ({placeholders})",
        (project.project_id, *candidate_ids),
    ).fetchall()
    evidence_by_id = {int(row["id"]): str(row["method_evidence"] or "") for row in rows}
    return [
        item_id
        for item_id in candidate_ids
        if method_evidence_term_coverage(evidence_by_id.get(item_id, ""), focus_terms) >= 2
    ]


def method_evidence_term_coverage(evidence: str, focus_terms: list[str]) -> int:
    evidence_terms = [term.casefold() for term in tokenize(evidence) if len(term) > 1]
    return sum(
        1
        for focus_term in unique_list(focus_terms)
        if any(term.startswith(focus_term.casefold()) for term in evidence_terms)
    )
