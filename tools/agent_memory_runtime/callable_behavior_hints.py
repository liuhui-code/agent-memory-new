# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any


LIFECYCLE_NAMES = {
    "abouttoappear", "abouttodisappear", "oncreate", "ondestroy",
    "onwindowstagecreate", "onwindowstagedestroy", "onmount", "onunmount",
    "onresume", "onpause",
}
DEFERRED_EXECUTION_RE = re.compile(
    r"\b(?:setTimeout|setInterval|queueMicrotask|requestAnimationFrame)\s*\("
)
INSTANCE_WRITE_RE = re.compile(
    r"\bthis\.[A-Za-z_$][A-Za-z0-9_$]*\s*(?:=|\+=|-=|\+\+|--)"
)
INSTANCE_READ_RE = re.compile(r"\bthis\.([A-Za-z_$][A-Za-z0-9_$]*)\b")
STATE_BRANCH_RE = re.compile(r"\b(?:if|switch)\s*\([^\n]*\bthis\.")
PERSISTENCE_WRITE_RE = re.compile(
    r"\b[A-Za-z_$][A-Za-z0-9_$]*\.(?:save|store|persist|write)[A-Za-z0-9_$]*\s*\(",
    re.IGNORECASE,
)
ASYNC_CALLABLE_RE = re.compile(r"\basync\s+[A-Za-z_$][A-Za-z0-9_$]*\s*\(")
EARLY_RETURN_GUARD_RE = re.compile(r"\bif\s*\([^\n]*\)\s*\{\s*return\b", re.DOTALL)


def callable_behavior_hints(entity: Any, source: str) -> list[str]:
    """Return bounded, source-proven callable behavior labels for retrieval."""
    name = str(getattr(entity, "name", "") or "").casefold()
    hints: list[str] = []
    if name in LIFECYCLE_NAMES:
        hints.extend(("lifecyclehook", "lifecycleactivation", "lifecycle"))
    if DEFERRED_EXECUTION_RE.search(source):
        hints.extend(("deferredexecution", "deferred", "schedule"))
    if INSTANCE_WRITE_RE.search(source):
        hints.extend(("statewrite", "state", "write"))
    reads = set(INSTANCE_READ_RE.findall(source))
    if reads:
        hints.extend(("stateread", "state", "read"))
    if STATE_BRANCH_RE.search(source):
        hints.extend(("statebranch", "state", "branch", "conditional"))
    if PERSISTENCE_WRITE_RE.search(source):
        hints.extend(("persistencewrite", "persistence", "write"))
    if ASYNC_CALLABLE_RE.search(source):
        hints.extend(("asyncboundary", "async"))
    if EARLY_RETURN_GUARD_RE.search(source):
        hints.extend(("guardreturn", "guard"))
    return list(dict.fromkeys(hints))
