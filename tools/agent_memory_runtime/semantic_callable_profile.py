# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re

from .query_language import positive_retrieval_query


OWNER_KIND_RULES = (
    ("viewmodel", "viewmodel"),
    ("repository", "repository"),
    ("adapter", "adapter"),
    ("boundary", "boundary"),
    ("policy", "policy"),
    ("coordinator", "coordinator"),
    ("service", "service"),
    ("store", "store"),
    ("controller", "controller"),
    ("manager", "manager"),
    ("model", "model"),
)
OWNER_KIND_QUERY_ALIASES = {
    "adapter": ("adapter", "适配"),
    "boundary": ("boundary", "边界"),
    "policy": ("policy", "策略"),
    "coordinator": ("coordinator", "协调器"),
    "component": (
        "component", "view", "page", "builder", "组件", "视图", "页面", "构建器",
    ),
    "controller": ("controller", "控制器"),
    "manager": ("manager", "管理器"),
    "model": ("model", "模型"),
    "repository": ("repository", "仓库"),
    "service": ("service", "服务"),
    "store": ("store", "状态仓"),
    "viewmodel": ("viewmodel", "view model", "视图模型"),
}
TARGET_CUE_RE = re.compile(
    r"\b(?:locate|find|identify|return)\b|定位|查找|找到|返回|给出",
    re.IGNORECASE,
)
CLAUSE_END_RE = re.compile(r"[.!?。！？;；\n]")
MULTI_TARGET_RE = re.compile(
    r"\b(?:both|chain|flow|path|trace|owners|and the)\b|链|路径|同时|两个|两处|多个|各自",
    re.IGNORECASE,
)
LIFECYCLE_NAMES = {
    "abouttoappear", "abouttodisappear", "oncreate", "ondestroy",
    "onwindowstagecreate", "onwindowstagedestroy", "onmount", "onunmount",
    "onresume", "onpause",
}
EARLY_RETURN_GUARD_RE = re.compile(r"\bif\s*\([^\n]*\)\s*\{\s*return\b", re.DOTALL)
STATE_WRITE_RE = re.compile(r"\bthis\.[A-Za-z_$][A-Za-z0-9_$]*\s*(?:=|\+=|-=|\+\+|--)" )
PERSISTENCE_WRITE_RE = re.compile(
    r"\b[A-Za-z_$][A-Za-z0-9_$]*\.(?:save|store|persist|write)[A-Za-z0-9_$]*\s*\(",
    re.IGNORECASE,
)
NAVIGATION_RE = re.compile(r"\b(?:navigate|router|navigator|pushUrl|replaceUrl)\b", re.IGNORECASE)


def owner_kind(name: str, container_kind: str, file_path: str) -> str:
    """Return a conservative, language-neutral owner role for a symbol container."""
    if container_kind == "component":
        return "component"
    for text in (name.casefold(), file_path.casefold()):
        for needle, value in OWNER_KIND_RULES:
            if needle in text:
                return value
    if container_kind in {"class", "interface"}:
        return "class"
    return "module"


def callable_roles(name: str, signature: str, source: str) -> list[str]:
    """Return inspectable callable roles; mechanisms retain operation-level detail."""
    roles: list[str] = []
    if "async " in signature:
        roles.append("async")
    if name.casefold() in LIFECYCLE_NAMES:
        roles.append("lifecycle")
    if EARLY_RETURN_GUARD_RE.search(source):
        roles.append("guard")
    if STATE_WRITE_RE.search(source):
        roles.append("state_write")
    if PERSISTENCE_WRITE_RE.search(source):
        roles.append("persistence_write")
    if NAVIGATION_RE.search(source):
        roles.append("navigation")
    return roles


def matching_owner_kind(query: str, candidate_kind: object) -> bool:
    value = str(candidate_kind or "").casefold()
    return bool(value) and value in requested_owner_kinds(query)


def matching_target_owner_kind(query: str, candidate_kind: object) -> bool:
    value = str(candidate_kind or "").casefold()
    return (
        bool(value)
        and value in requested_target_owner_kinds(query)
        and not MULTI_TARGET_RE.search(positive_retrieval_query(query))
    )


def requested_owner_kinds(query: str) -> set[str]:
    positive = positive_retrieval_query(query)
    target = requested_target_owner_kinds(positive)
    return target or matching_kinds([positive])


def requested_target_owner_kinds(query: str) -> set[str]:
    return matching_kinds(target_clauses(positive_retrieval_query(query)))


def matching_kinds(clauses: list[str]) -> set[str]:
    return {
        kind
        for kind in owner_kinds()
        if any(alias_matches(clause, alias) for clause in clauses for alias in aliases(kind))
    }


def target_clauses(query: str) -> list[str]:
    clauses: list[str] = []
    for match in TARGET_CUE_RE.finditer(query):
        tail = query[match.end():]
        end = CLAUSE_END_RE.search(tail)
        clauses.append(tail[:end.start()] if end else tail)
    return clauses


def owner_kinds() -> set[str]:
    return {value for _, value in OWNER_KIND_RULES} | {"component"}


def aliases(kind: str) -> tuple[str, ...]:
    return OWNER_KIND_QUERY_ALIASES.get(kind, (kind.replace("_", ""),))


def alias_matches(clause: str, alias: str) -> bool:
    normalized = clause.casefold().replace("-", " ").replace("_", " ")
    if alias.isascii():
        return re.search(rf"\b{re.escape(alias)}\b", normalized, re.IGNORECASE) is not None
    return alias in normalized
