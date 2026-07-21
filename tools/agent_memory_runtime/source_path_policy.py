# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from pathlib import PurePosixPath
import re
from typing import Any


GENERATED_SOURCE_DIRS = {
    ".cache",
    ".hvigor",
    ".preview",
    "coverage",
    "generated",
}
LANGUAGE_SUFFIXES = {
    "ArkTS": {".ets"},
    "Dart": {".dart"},
    "JavaScript": {".js", ".jsx"},
    "Python": {".py"},
    "Swift": {".swift"},
    "TypeScript": {".ts", ".tsx"},
}
LANGUAGE_HINTS = {
    "ArkTS": re.compile(r"\b(?:arkts|harmonyos|openharmony)\b|\.ets\b", re.I),
    "Dart": re.compile(r"\b(?:dart|flutter)\b|\.dart\b", re.I),
    "JavaScript": re.compile(r"\bjavascript\b|\.jsx?\b", re.I),
    "Python": re.compile(r"\bpython\b|\.py\b", re.I),
    "Swift": re.compile(r"\bswift\b|\.swift\b", re.I),
    "TypeScript": re.compile(r"\btypescript\b|\.tsx?\b", re.I),
}


def is_generated_source_path(file_path: str) -> bool:
    parts = {
        part.casefold()
        for part in PurePosixPath(file_path.replace("\\", "/")).parts
    }
    return bool(parts & GENERATED_SOURCE_DIRS)


def filter_generated_candidates(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    canonical = [
        item for item in items
        if not is_generated_source_path(str(item.get("file_path") or ""))
    ]
    return canonical or items


def filter_explicit_language_candidates(
    items: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    preferred = {
        language
        for language, pattern in LANGUAGE_HINTS.items()
        if pattern.search(query)
    }
    if len(preferred) != 1:
        return items
    matched = [
        item for item in items
        if candidate_language(item) in preferred
    ]
    return matched or items


def candidate_language(item: dict[str, Any]) -> str:
    stored = str(item.get("language") or "")
    if stored:
        return stored
    suffix = PurePosixPath(str(item.get("file_path") or "")).suffix.casefold()
    return next(
        (
            language for language, suffixes in LANGUAGE_SUFFIXES.items()
            if suffix in suffixes
        ),
        "",
    )
