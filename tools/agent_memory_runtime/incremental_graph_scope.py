# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3
from typing import Any


DEPENDENT_CALL_DEPTH = 3
SQL_CHUNK_SIZE = 400


def transitive_caller_paths(
    conn: sqlite3.Connection,
    project_id: str,
    seed_symbol_ids: set[int],
    limit: int = 2000,
) -> list[str]:
    frontier = set(seed_symbol_ids)
    visited = set(seed_symbol_ids)
    callers: set[int] = set()
    for _depth in range(DEPENDENT_CALL_DEPTH):
        next_frontier: set[int] = set()
        for chunk in chunks(sorted(frontier)):
            remaining = limit - len(callers) - len(next_frontier)
            if remaining <= 0:
                break
            rows = conn.execute(
                f"""
                SELECT DISTINCT source_id FROM memory_edges
                WHERE project_id = ? AND valid_to IS NULL
                  AND source_type = 'code_symbol' AND target_type = 'code_symbol'
                  AND relation = 'calls' AND target_id IN ({','.join('?' for _ in chunk)})
                LIMIT ?
                """,
                (project_id, *chunk, remaining),
            ).fetchall()
            next_frontier.update(
                int(row["source_id"]) for row in rows
                if int(row["source_id"]) not in visited
            )
        if not next_frontier:
            break
        callers.update(next_frontier)
        visited.update(next_frontier)
        frontier = next_frontier
    return symbol_paths(conn, project_id, callers, limit)


def symbol_paths(
    conn: sqlite3.Connection, project_id: str, symbol_ids: set[int], limit: int,
) -> list[str]:
    paths: set[str] = set()
    for chunk in chunks(sorted(symbol_ids)):
        rows = conn.execute(
            f"SELECT file_path FROM code_symbols WHERE project_id = ? "
            f"AND id IN ({','.join('?' for _ in chunk)}) LIMIT ?",
            (project_id, *chunk, limit - len(paths)),
        ).fetchall()
        paths.update(str(row["file_path"]) for row in rows)
        if len(paths) >= limit:
            break
    return sorted(paths)[:limit]


def chunks(values: list[Any], size: int = SQL_CHUNK_SIZE) -> list[list[Any]]:
    return [values[index:index + size] for index in range(0, len(values), size)]
