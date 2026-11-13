# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .arkts_behavior_markers import CALLBACK_CLEANUP_RE, ASYNC_ORDER_GUARD_RE


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
    hints.extend(event_collection_hints(entity, source))
    return list(dict.fromkeys(hints))


# Mask non-code before recognizing writes. Template interpolation is deliberately
# not inspected: it is not proof of a direct operation owned by this callable.
NON_CODE_RE = re.compile(r"//[^\n]*|/\*[\s\S]*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`")
INDEX_WRITE_RE = re.compile(
    r"\bthis\.[A-Za-z_$][\w$]*(?:\s*\[[^\]\n]+\])+"
    r"(?:\.[A-Za-z_$][\w$]*)?\s*(?:=(?!=|>)|[+*/%-]=|\+\+|--)"
)


def event_collection_hints(entity: Any, source: str) -> list[str]:
    """Add callable-local ECMA mechanism evidence, never combined file hints."""
    if Path(str(getattr(entity, "file_path", ""))).suffix not in {".ts", ".ets"}:
        return []
    code = NON_CODE_RE.sub(lambda m: " " * len(m.group()), source)
    name = str(getattr(entity, "name", ""))
    result = ["eventboundary"] if re.fullmatch(r"(?:on|handle)[A-Z_$][\w$]*", name) else []
    if name.casefold() in LIFECYCLE_NAMES:
        result.append("lifecycleboundary")
    body = code.partition("{")[2]
    # The existing index carries spans, not nested scope ownership. Fail closed
    # for bodies with callbacks/functions rather than attribute their writes to
    # the enclosing callable. This does not remove prior behavior labels.
    nested_method = re.search(
        r"\b(?!(?:if|for|while|switch|catch|with)\b)[A-Za-z_$][\w$]*"
        r"\s*\([^)]*\)\s*(?::[^{};]+)?\{", body,
    )
    # Slash can start a regex literal, which this bounded lexer does not parse.
    # Abstain for ambiguous slash-containing bodies rather than index its text.
    if ("=>" not in body and "/" not in body and nested_method is None
            and not re.search(r"\b(?:function|class)\b", body)):
        if INDEX_WRITE_RE.search(body):
            result.append("collectionwrite")
        if ASYNC_ORDER_GUARD_RE.search(body) and re.search(r"\basync\b|\bawait\b", code):
            result.append("orderingguard")
        if CALLBACK_CLEANUP_RE.search(body):
            result.append("callbackcleanup")
    return result
