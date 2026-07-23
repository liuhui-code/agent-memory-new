# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re

from .semantic_models import SemanticMechanism
from .text import identifier_tokens, unique_list


MAX_MECHANISMS_PER_CALLABLE = 16
CALL_CHAIN_RE = re.compile(
    r"\b((?:this\.)?[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+)\s*\("
)
GUARD_RE = re.compile(r"\bif\s*\((.*)")
RESOURCE_RE = re.compile(
    r"(?:\.length\b|\.size\b|\b(?:count|capacity|limit|max(?:imum)?|bytes?)\b)",
    re.IGNORECASE,
)
COMPARISON_RE = re.compile(r"(?:<=|>=|<|>|===?|!==?)")
CALLBACK_RE = re.compile(r"\.((?:on|add|register)[A-Z][A-Za-z0-9_$]*)\s*\(")
PLATFORM_RE = re.compile(
    r"\b(?:deviceInfo\.[A-Za-z_$][\w$]*|canIUse\s*\(|"
    r"hasSystemCapability\s*\(|ConfigurationConstant\.[A-Za-z_$][\w$]*)"
)
PERSISTENCE_CALL_RE = re.compile(
    r"\b((?:this\.)?[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\."
    r"([A-Za-z_$][\w$]*)\s*\("
)
PERSISTENCE_RECEIVER_RE = re.compile(
    r"(?:preferences?|storage|store|repository|dao|database)$", re.IGNORECASE
)
READ_METHOD_RE = re.compile(r"^(?:get|read|load|restore|find|query)", re.IGNORECASE)
WRITE_METHOD_RE = re.compile(r"^(?:set|put|write|save|persist|insert|update|commit|flush)", re.IGNORECASE)


def extract_callable_mechanisms(
    lines: list[str], source_key: str, start: int, end: int
) -> list[SemanticMechanism]:
    mechanisms: list[SemanticMechanism] = []
    for index in range(start, min(end + 1, len(lines))):
        source = strip_line_comment(lines[index])
        if not source.strip():
            continue
        line = index + 1
        mechanisms.extend(operation_mechanisms(source_key, source, line))
        guard = GUARD_RE.search(source)
        if guard:
            mechanisms.append(mechanism(
                source_key, "guard", guard.group(1), line,
                ("conditional", "guard"), "conditional guard",
            ))
            if RESOURCE_RE.search(guard.group(1)) and COMPARISON_RE.search(guard.group(1)):
                mechanisms.append(mechanism(
                    source_key, "resource_bound", guard.group(1), line,
                    ("resource", "bound", "size", "limit", "maximum"),
                    "bounded resource comparison",
                ))
        for callback in CALLBACK_RE.findall(source):
            mechanisms.append(mechanism(
                source_key, "callback_binding", callback, line,
                ("callback", "binding", "event"), f"callback:{callback}",
            ))
        if PLATFORM_RE.search(source):
            mechanisms.append(mechanism(
                source_key, "platform_predicate", source, line,
                ("platform", "predicate", "capability", "device"),
                "platform capability predicate",
            ))
        mechanisms.extend(persistence_mechanisms(source_key, source, line))
    return dedupe_mechanisms(mechanisms)[:MAX_MECHANISMS_PER_CALLABLE]


def operation_mechanisms(
    source_key: str, source: str, line: int
) -> list[SemanticMechanism]:
    return [
        mechanism(
            source_key, "operation", chain, line,
            ("operation", "call"), f"call:{chain.replace('this.', '', 1)}",
        )
        for chain in unique_list(CALL_CHAIN_RE.findall(source))[:8]
    ]


def persistence_mechanisms(
    source_key: str, source: str, line: int
) -> list[SemanticMechanism]:
    result: list[SemanticMechanism] = []
    for receiver, method_name in PERSISTENCE_CALL_RE.findall(source):
        receiver_name = receiver.rsplit(".", 1)[-1]
        if not PERSISTENCE_RECEIVER_RE.search(receiver_name):
            continue
        if READ_METHOD_RE.match(method_name):
            kind, aliases = "persistence_read", ("persistence", "read", "load", "restore")
        elif WRITE_METHOD_RE.match(method_name):
            kind, aliases = "persistence_write", ("persistence", "write", "save", "commit")
        else:
            continue
        result.append(mechanism(
            source_key, kind, f"{receiver}.{method_name}", line, aliases,
            f"{kind}:{receiver_name}.{method_name}",
        ))
    return result


def mechanism(
    source_key: str,
    kind: str,
    evidence: str,
    line: int,
    aliases: tuple[str, ...],
    detail: str,
) -> SemanticMechanism:
    terms = unique_list([
        kind,
        kind.replace("_", ""),
        *aliases,
        *identifier_tokens(evidence),
    ])[:12]
    return SemanticMechanism(
        source_key=source_key,
        kind=kind,
        terms=[term.casefold() for term in terms if 1 < len(term) <= 64],
        line=line,
        detail=detail[:120],
    )


def dedupe_mechanisms(items: list[SemanticMechanism]) -> list[SemanticMechanism]:
    result: dict[tuple[str, int, tuple[str, ...]], SemanticMechanism] = {}
    for item in items:
        result[(item.kind, item.line, tuple(item.terms))] = item
    return list(result.values())


def strip_line_comment(line: str) -> str:
    return line.split("//", 1)[0]
