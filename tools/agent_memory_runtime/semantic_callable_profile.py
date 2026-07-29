# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re


OWNER_KIND_RULES = (
    ("viewmodel", "viewmodel"),
    ("repository", "repository"),
    ("service", "service"),
    ("store", "store"),
    ("controller", "controller"),
    ("manager", "manager"),
    ("model", "model"),
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
    text = " ".join((name, file_path)).casefold()
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
    if not value:
        return False
    normalized = query.casefold().replace("-", "").replace("_", "")
    return value.replace("_", "") in normalized
