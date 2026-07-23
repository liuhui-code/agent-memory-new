# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re

from .code_wiki_component_flow import mask_comments


MAX_INDEXED_OPERATIONS = 12
OPERATION_RE = re.compile(r"(?m)(?:^\s*|\)\s*)\.([a-z][A-Za-z0-9_$]*)\s*\(")
MEMBER_OPERATION_RE = re.compile(
    r"\b(?:this\.)?[A-Za-z_$][A-Za-z0-9_$]*\.([a-zA-Z_$][A-Za-z0-9_$]*)\s*\("
)
SUMMARY_PREFIX = "operations: "
GENERIC_OPERATIONS = {
    "align", "backgroundcolor", "fontsize", "height", "margin", "maxlines",
    "padding", "width",
}
MEMBER_BEHAVIOR_OPERATIONS = {
    "executesql", "foreach", "getwindowavoidarea", "pushpath", "pushpathbyname",
    "pushurl", "querysql", "replacepath", "replacepathbyname", "replaceurl",
}
OPERATION_ALIASES = {
    "navigate": "pushpathbyname",
    "navigation": "pushpathbyname",
    "route": "pushpathbyname",
    "separator": "divider",
    "分隔线": "divider",
    "分割线": "divider",
    "路由": "pushpathbyname",
    "跳转": "pushpathbyname",
}


def extract_arkts_operation_names(text: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    source = mask_comments(text)
    member_matches = [
        match for match in MEMBER_OPERATION_RE.finditer(source)
        if match.group(1).casefold() in MEMBER_BEHAVIOR_OPERATIONS
    ]
    matches = sorted(
        [*OPERATION_RE.finditer(source), *member_matches],
        key=lambda item: item.start(),
    )
    for match in matches:
        name = match.group(1)
        normalized = name.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        names.append(name)
        if len(names) >= MAX_INDEXED_OPERATIONS:
            break
    return names


def summary_operation_names(summary: str) -> list[str]:
    marker = summary.casefold().find(SUMMARY_PREFIX)
    if marker < 0:
        return []
    value = summary[marker + len(SUMMARY_PREFIX):].split(";", 1)[0]
    return [item.strip() for item in value.split(",") if item.strip()]


def matching_operation_names(summary: str, query_terms: list[str]) -> list[str]:
    terms = {term.casefold() for term in query_terms}
    return [
        name for name in summary_operation_names(summary)
        if name.casefold() in terms
    ]


def distinctive_operation_names(names: list[str]) -> list[str]:
    return [name for name in names if name.casefold() not in GENERIC_OPERATIONS]


def direct_operation_query_terms(terms: set[str]) -> list[str]:
    normalized = {term.casefold() for term in terms}
    normalized.update(
        target for source, target in OPERATION_ALIASES.items()
        if source in normalized
    )
    return sorted(normalized)
