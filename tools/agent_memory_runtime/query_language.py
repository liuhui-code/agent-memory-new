# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re

from .text import identifier_tokens, unique_list


NEGATIVE_RESULT_CLAUSE_RE = re.compile(
    r"(?:[,;，；]\s*not\s+|rather\s+than|"
    r"do\s+not\s+return|don't\s+return|"
    r"excluding|exclude|ignore|omit(?:ting)?|不要返回|而不是|排除|忽略)"
    r"[^,.;，。；\n]*[,.;，。；]?",
    re.I,
)
COMPARISON_CLAUSE_RE = re.compile(
    r"(?:compared\s+(?:with|to)|unlike|versus|vs\.?|opposite\s+to|"
    r"相比(?:于|较)?|对比(?:于)?)"
    r"[^,.;，。；\n]*[,.;，。；]?",
    re.I,
)
NAMED_IDENTIFIER_RE = re.compile(r"\b[A-Z][A-Za-z0-9_$]*[A-Z][A-Za-z0-9_$]*\b")
EXCLUDED_ROLE_TERMS = {"class", "data", "entity", "item", "model", "record", "type"}
EXAMPLE_ROLE_TERMS = {"demo", "demos", "example", "examples", "sample", "samples"}
TARGET_ROLE_PATTERNS = (
    (re.compile(r"\beditor\b", re.I), "editor"),
    (re.compile(r"\b(?:edit|editing)\s+(?:screen|page|side)\b", re.I), "editor"),
    (re.compile(r"编辑(?:页|页面|侧)"), "editor"),
)


def target_role_terms(query: str) -> list[str]:
    return unique_list([
        alias for pattern, alias in TARGET_ROLE_PATTERNS if pattern.search(query)
    ])


def positive_retrieval_query(query: str) -> str:
    """Remove explicit result exclusions from positive evidence retrieval."""
    retained_terms = unique_list([
        term
        for clause in NEGATIVE_RESULT_CLAUSE_RE.findall(query)
        for identifier in NAMED_IDENTIFIER_RE.findall(clause)
        for term in identifier_tokens(identifier)
        if term not in EXCLUDED_ROLE_TERMS
    ])
    positive = NEGATIVE_RESULT_CLAUSE_RE.sub(" ", query)
    positive = " ".join(COMPARISON_CLAUSE_RE.sub(" ", positive).split())
    role_terms = target_role_terms(positive)
    return " ".join([positive, *retained_terms, *role_terms]).strip() or query


def excluded_result_roles(query: str) -> set[str]:
    return {
        term
        for clause in NEGATIVE_RESULT_CLAUSE_RE.findall(query)
        for term in re.findall(r"[a-z]+", clause.casefold())
        if term in EXAMPLE_ROLE_TERMS
    }
