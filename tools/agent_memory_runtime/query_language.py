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
LOWER_CAMEL_IDENTIFIER_RE = re.compile(
    r"\b[a-z][A-Za-z0-9_$]*[A-Z][A-Za-z0-9_$]*\b"
)
EXCLUDED_ROLE_TERMS = {
    "adapter", "boundary", "card", "class", "component", "config", "configuration",
    "coordinator", "data", "entity", "item", "manifest", "metadata", "model", "page",
    "record", "reporter", "repository", "service", "store", "type", "view", "viewmodel",
}
EXAMPLE_ROLE_TERMS = {"demo", "demos", "example", "examples", "sample", "samples"}
NEGATIVE_ROLE_ALIASES = (
    (re.compile(r"(?:列表|详情|设置|状态|加载)?(?:页|页面)"), "page"),
    (re.compile(r"组件"), "component"),
    (re.compile(r"服务"), "service"),
    (re.compile(r"仓库"), "repository"),
    (re.compile(r"适配器"), "adapter"),
    (re.compile(r"视图模型"), "viewmodel"),
    (re.compile(r"数据模型|模型"), "model"),
)
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


def excluded_result_identifiers(query: str) -> set[str]:
    return {
        re.sub(r"[^a-z0-9]", "", value.casefold())
        for clause in NEGATIVE_RESULT_CLAUSE_RE.findall(query)
        for pattern in (NAMED_IDENTIFIER_RE, LOWER_CAMEL_IDENTIFIER_RE)
        for value in pattern.findall(clause)
    }


def excluded_code_candidate(query: str, item: dict[str, object]) -> bool:
    clauses = NEGATIVE_RESULT_CLAUSE_RE.findall(query)
    if not clauses:
        return False
    text = " ".join(str(item.get(key) or "") for key in ("file_path", "owner_name"))
    tokens = set(identifier_tokens(text))
    roles = {
        term for clause in clauses for term in re.findall(r"[a-z]+", clause.casefold())
        if term in EXCLUDED_ROLE_TERMS
    }
    roles.update(
        role for clause in clauses for pattern, role in NEGATIVE_ROLE_ALIASES
        if pattern.search(clause)
    )
    normalized = re.sub(r"[^a-z0-9]", "", text.casefold())
    identifiers = {
        re.sub(r"[^a-z0-9]", "", value.casefold())
        for clause in clauses for value in NAMED_IDENTIFIER_RE.findall(clause)
    }
    return bool(roles & tokens or any(value in normalized for value in identifiers))
