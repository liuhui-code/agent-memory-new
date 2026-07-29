# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from .models import Project


SQL_CHUNK_SIZE = 400
DISPATCH_SCOPE_LIMIT = 2000
CLASS_HIERARCHY_RE = re.compile(
    r"\b(?:class|struct)\s+[A-Za-z_$][\w$]*"
    r"(?:\s+extends\s+([A-Za-z_$][\w$]*))?"
    r"(?:[^\n{]*?\s+implements\s+([^\n{]+))?"
)


def dispatch_rebuild_paths(
    conn: sqlite3.Connection,
    project: Project,
    changed_paths: list[str],
    previous_symbol_ids: set[int],
    limit: int = DISPATCH_SCOPE_LIMIT,
) -> list[str]:
    contract_ids = _old_contract_ids(conn, project.project_id, previous_symbol_ids)
    names = _declared_parent_names(project.root, changed_paths)
    contract_ids.update(_contract_ids_for_names(conn, project.project_id, names))
    if not contract_ids:
        return []
    symbol_ids = set(contract_ids)
    symbol_ids.update(_related_symbol_ids(conn, project.project_id, contract_ids, limit))
    return _symbol_paths(conn, project.project_id, symbol_ids, limit)


def _declared_parent_names(root: Path, paths: list[str]) -> set[str]:
    names: set[str] = set()
    for relative in paths:
        if Path(relative).suffix.lower() not in {".ets", ".ts", ".tsx"}:
            continue
        try:
            text = (root / relative).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for extends, implements in CLASS_HIERARCHY_RE.findall(text):
            if extends:
                names.add(extends)
            for item in implements.split(",") if implements else []:
                name = re.match(r"[A-Za-z_$][\w$]*", item.strip())
                if name:
                    names.add(name.group(0))
    return names


def _old_contract_ids(
    conn: sqlite3.Connection,
    project_id: str,
    symbol_ids: set[int],
) -> set[int]:
    result: set[int] = set()
    for chunk in _chunks(sorted(symbol_ids)):
        rows = conn.execute(
            f"""
            SELECT DISTINCT target_id FROM memory_edges
            WHERE project_id = ? AND valid_to IS NULL
              AND source_type = 'code_symbol' AND target_type = 'code_symbol'
              AND relation IN ('implements', 'extends')
              AND source_id IN ({','.join('?' for _ in chunk)})
            """,
            (project_id, *chunk),
        ).fetchall()
        result.update(int(row["target_id"]) for row in rows)
    return result


def _contract_ids_for_names(
    conn: sqlite3.Connection,
    project_id: str,
    names: set[str],
) -> set[int]:
    result: set[int] = set()
    for chunk in _chunks(sorted(names)):
        rows = conn.execute(
            f"SELECT id FROM code_symbols WHERE project_id = ? "
            f"AND symbol IN ({','.join('?' for _ in chunk)})",
            (project_id, *chunk),
        ).fetchall()
        result.update(int(row["id"]) for row in rows)
    return result


def _related_symbol_ids(
    conn: sqlite3.Connection,
    project_id: str,
    contract_ids: set[int],
    limit: int,
) -> set[int]:
    result: set[int] = set()
    for chunk in _chunks(sorted(contract_ids)):
        remaining = limit - len(result)
        if remaining <= 0:
            break
        rows = conn.execute(
            f"""
            SELECT DISTINCT source_id FROM memory_edges
            WHERE project_id = ? AND valid_to IS NULL
              AND source_type = 'code_symbol' AND target_type = 'code_symbol'
              AND relation IN ('dispatches_via', 'implements', 'extends')
              AND target_id IN ({','.join('?' for _ in chunk)})
            LIMIT ?
            """,
            (project_id, *chunk, remaining),
        ).fetchall()
        result.update(int(row["source_id"]) for row in rows)
    return result


def _symbol_paths(
    conn: sqlite3.Connection,
    project_id: str,
    symbol_ids: set[int],
    limit: int,
) -> list[str]:
    paths: set[str] = set()
    for chunk in _chunks(sorted(symbol_ids)):
        rows = conn.execute(
            f"SELECT file_path FROM code_symbols WHERE project_id = ? "
            f"AND id IN ({','.join('?' for _ in chunk)}) LIMIT ?",
            (project_id, *chunk, limit - len(paths)),
        ).fetchall()
        paths.update(str(row["file_path"]) for row in rows)
        if len(paths) >= limit:
            break
    return sorted(paths)[:limit]


def _chunks(values: list[Any]) -> list[list[Any]]:
    return [
        values[index:index + SQL_CHUNK_SIZE]
        for index in range(0, len(values), SQL_CHUNK_SIZE)
    ]
