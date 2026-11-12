# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import os
import sqlite3

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator


class RequiredSourceReadError(RuntimeError):
    """A writer cannot rebuild its declared graph scope completely."""


_REQUIRED: ContextVar[dict[Path, tuple[str, Path]] | None] = ContextVar("required_index_sources", default=None)


@contextmanager
def required_source_reads() -> Iterator[dict[Path, tuple[str, Path]]]:
    required: dict[Path, tuple[str, Path]] = {}
    token = _REQUIRED.set(required)
    try:
        yield required
    finally:
        _REQUIRED.reset(token)


def lexical_path(path: Path) -> Path:
    return Path(os.path.abspath(path))


def source_expectation(path: Path) -> tuple[str, Path] | None:
    required = _REQUIRED.get()
    expected = required.get(lexical_path(path)) if required is not None else None
    if expected is not None and path.resolve() != expected[1]:
        raise RequiredSourceReadError(f"required rebuild source target changed: {path}")
    return expected


def resolve_source_path(path: Path) -> Path:
    expected = source_expectation(path)
    return expected[1] if expected is not None else path.resolve()


def source_read_failed(path: Path, error: OSError) -> None:
    required = _REQUIRED.get()
    if required is not None and lexical_path(path) in required:
        raise RequiredSourceReadError(f"required rebuild source unreadable: {path}: {error}") from error


def read_source_text(path: Path) -> str:
    required = _REQUIRED.get()
    if required is None or lexical_path(path) not in required:
        return path.read_text(encoding="utf-8", errors="ignore")
    # Decode the exact bytes whose digest was checked, with Path.read_text newline semantics.
    return read_source_bytes(path).decode("utf-8", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")


def read_source_bytes(path: Path) -> bytes:
    expected = source_expectation(path)
    try:
        raw = path.read_bytes()
    except OSError as error:
        source_read_failed(path, error)
        raise
    source_expectation(path)
    if expected is not None:
        if not expected[0] or hashlib.sha256(raw).hexdigest() != expected[0]:
            raise RequiredSourceReadError(f"required rebuild source changed outside declared refresh: {path}")
    return raw


def source_is_file(path: Path) -> bool:
    source_expectation(path)
    present = path.is_file()
    if not present:
        source_read_failed(path, FileNotFoundError(str(path)))
    return present


def require_rebuild_sources(
    required: dict[Path, tuple[str, Path]], conn: sqlite3.Connection, project_id: str,
    root: Path, paths: list[str], declared_digests: dict[str, str],
) -> None:
    expected = dict(declared_digests)
    for start in range(0, len(paths), 400):
        chunk = paths[start:start + 400]
        rows = conn.execute(
            f"SELECT file_path, source_digest FROM code_files WHERE project_id = ? "
            f"AND file_path IN ({','.join('?' for _ in chunk)})", (project_id, *chunk),
        ).fetchall()
        for row in rows:
            expected.setdefault(str(row["file_path"]), str(row["source_digest"] or ""))
    for relative in paths:
        path = lexical_path(root / relative)
        resolved = path.resolve()
        value = (expected.get(relative, ""), resolved)
        if resolved in required and required[resolved] != value:
            raise RequiredSourceReadError(f"conflicting rebuild source aliases: {path}")
        required[path] = value
        required[resolved] = value
    # Refuse known missing/changed inputs before mutation; every subsequent read also checks.
    for path in sorted(required):
        read_source_bytes(path)
