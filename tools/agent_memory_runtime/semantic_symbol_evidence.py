# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from pathlib import Path

from .models import Project
from .semantic_models import SemanticEntity
from .text import ENGLISH_QUERY_STOPWORDS, identifier_tokens, unique_list


MAX_EVIDENCE_TERMS = 36
MAX_STRING_EVIDENCE_TERMS = 24
MAX_SPAN_LINES = 240
MAX_SOURCE_FILES = 1000
CALLABLE_KINDS = {"function", "method"}
CODE_STOPWORDS = {
    "async", "await", "boolean", "break", "case", "catch", "class", "const",
    "continue", "default", "else", "export", "extends", "false", "finally",
    "for", "function", "if", "implements", "import", "interface", "let", "new",
    "null", "number", "override", "private", "promise", "protected", "public",
    "readonly", "return", "static", "string", "struct", "super", "switch", "this",
    "throw", "true", "try", "undefined", "void", "while",
    *ENGLISH_QUERY_STOPWORDS,
}
CHAIN_RE = re.compile(
    r"\b(?:this\.)?[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)+"
)
CALL_RE = re.compile(r"\b([A-Za-z_$][A-Za-z0-9_$]*)\s*(?=\()")
STRING_RE = re.compile(r"(['\"])([^'\"\n]{2,96})\1")


def load_semantic_source_lines(
    project: Project,
    file_paths: list[str],
) -> dict[str, list[str]]:
    loaded: dict[str, list[str]] = {}
    for file_path in sorted(set(file_paths))[:MAX_SOURCE_FILES]:
        source = safe_source_path(project, file_path)
        if source is None:
            continue
        try:
            loaded[file_path] = source.read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines()
        except OSError:
            continue
    return loaded


def method_evidence_text(
    entity: SemanticEntity,
    source_lines: list[str] | None,
) -> str:
    return method_evidence_payload(entity, source_lines)[0]


def method_evidence_payload(
    entity: SemanticEntity,
    source_lines: list[str] | None,
) -> tuple[str, str]:
    source = method_source_text(entity, source_lines)
    if not source:
        return "", ""
    return (
        " ".join(method_terms_from_source(source, entity)),
        " ".join(string_terms_from_source(source)),
    )


def method_evidence_terms(
    source_lines: list[str],
    entity: SemanticEntity,
) -> list[str]:
    source = method_source_text(entity, source_lines)
    return method_terms_from_source(source, entity) if source else []


def method_source_text(
    entity: SemanticEntity,
    source_lines: list[str] | None,
) -> str:
    if entity.kind not in CALLABLE_KINDS or not source_lines:
        return ""
    start = max(0, entity.start_line - 1)
    end = min(len(source_lines), entity.end_line, start + MAX_SPAN_LINES)
    return "\n".join(source_lines[start:end]) if start < end else ""


def method_terms_from_source(source: str, entity: SemanticEntity) -> list[str]:
    identifiers: list[str] = []
    for chain in CHAIN_RE.findall(source):
        identifiers.extend(chain.replace("this.", "", 1).split("."))
    identifiers.extend(CALL_RE.findall(source))
    terms: list[str] = []
    for identifier in identifiers:
        normalized = identifier.casefold()
        terms.extend([normalized, *identifier_tokens(identifier)])
    blocked = {entity.name.casefold(), *CODE_STOPWORDS}
    return unique_list([
        term for term in terms
        if 2 < len(term) <= 64
        and term not in blocked
        and not term.isdigit()
    ])[:MAX_EVIDENCE_TERMS]


def string_terms_from_source(source: str) -> list[str]:
    terms: list[str] = []
    for _quote, value in STRING_RE.findall(source):
        normalized = value.casefold().strip()
        if len(normalized) > 64 or not any(character.isalpha() for character in normalized):
            continue
        terms.extend([normalized, *identifier_tokens(value)])
    return unique_list([
        term for term in terms
        if 2 < len(term) <= 64 and not term.isdigit()
    ])[:MAX_STRING_EVIDENCE_TERMS]


def safe_source_path(project: Project, file_path: str) -> Path | None:
    relative = Path(file_path)
    if relative.is_absolute():
        return None
    source = (project.root / relative).resolve()
    try:
        source.relative_to(project.root.resolve())
    except ValueError:
        return None
    return source if source.is_file() else None
