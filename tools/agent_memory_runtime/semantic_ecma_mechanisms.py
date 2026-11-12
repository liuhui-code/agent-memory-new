# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .semantic_models import SemanticMechanism
from .source_call_scanner import balanced_call_end, code_mask
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


@dataclass
class OperationScan:
    chains: dict[int, list[str]]
    end_lines: dict[int, list[int]]
    unbalanced_lines: set[int]


def scan_operation_source(lines: list[str]) -> OperationScan:
    text = "\n".join(lines)
    mask = code_mask(text)
    chains: dict[int, list[str]] = {}
    ends: dict[int, list[int]] = {}
    unbalanced: set[int] = set()
    line, previous = 1, 0
    # Same mask/balancing primitives as scan_calls_masked, preserving source offsets.
    for match in CALL_CHAIN_RE.finditer(mask):
        line += text.count("\n", previous, match.start())
        previous = match.start()
        if "\n" in text[match.end(1):match.end()]:
            continue  # Legacy extraction does not support a call head split across lines.
        end = balanced_call_end(mask, match.end() - 1)
        if end is None:
            unbalanced.add(line)
            continue
        chains.setdefault(line, []).append(text[match.start(1):match.end(1)])
        ends.setdefault(line, []).append(line + text.count("\n", match.start(), end))
    return OperationScan(chains, ends, unbalanced)


def operation_gap_reason(lines: list[str], start: int, end: int, scan: OperationScan) -> str:
    if any("`" in line for line in lines[start:end + 1]):
        return "operation_syntax_unverified_template"
    if any(line in scan.unbalanced_lines or any(last > end + 1 for last in scan.end_lines.get(line, []))
           for line in range(start + 1, min(end + 2, len(lines) + 1))):
        return "operation_syntax_unverified_unbalanced_call"
    return ""


def extract_file_mechanisms(
    lines: list[str], callables: list[Any],
) -> tuple[list[SemanticMechanism], list[dict[str, str]]]:
    scan = scan_operation_source(lines)
    mechanisms: list[SemanticMechanism] = []
    gaps: list[dict[str, str]] = []
    for block in callables:
        reason = operation_gap_reason(lines, block.start, block.end, scan)
        if reason:
            gaps.append({"kind": reason, "file_path": block.entity.file_path,
                         "symbol": block.entity.qualified_name,
                         "start_line": str(block.start + 1), "end_line": str(block.end + 1)})
        mechanisms.extend(extract_callable_mechanisms(
            lines, block.entity.key, block.start, block.end, scan,
        ))
    return mechanisms, gaps


def extract_callable_mechanisms(
    lines: list[str], source_key: str, start: int, end: int,
    operation_scan: OperationScan | None = None,
) -> list[SemanticMechanism]:
    mechanisms: list[SemanticMechanism] = []
    scan = operation_scan if operation_scan is not None else scan_operation_source(lines)
    legacy = bool(operation_gap_reason(lines, start, end, scan))
    for index in range(start, min(end + 1, len(lines))):
        source = strip_line_comment(lines[index])
        if not source.strip():
            continue
        line = index + 1
        mechanisms.extend(operation_mechanisms(
            source_key, source, line, scan.chains.get(line, []), legacy=legacy,
        ))
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
    source_key: str, source: str, line: int, chains: list[str] | None = None,
    *, legacy: bool = False,
) -> list[SemanticMechanism]:
    if chains is None and not legacy:
        lines = source.splitlines()
        scan = scan_operation_source(lines)
        legacy = bool(operation_gap_reason(lines, 0, len(lines) - 1, scan))
        chains = [chain for number in sorted(scan.chains) for chain in scan.chains[number]]
    selected = CALL_CHAIN_RE.findall(source) if legacy else (chains or [])
    return [
        mechanism(
            source_key, "operation", chain, line,
            ("operation", "call"), f"call:{chain.replace('this.', '', 1)}",
        )
        for chain in unique_list(selected)[:8]
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
