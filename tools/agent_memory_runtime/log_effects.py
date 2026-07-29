# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from .code_wiki_extractors import string_literals
from .models import Project
from .source_call_scanner import scan_calls
from .storage import now_iso


MAX_WRAPPER_DEPTH = 3
MAX_EFFECTS_PER_CALLER = 32
PATH_SEARCH_LIMIT = MAX_EFFECTS_PER_CALLER + 1
FORWARD_EXPANSION_LIMIT = 2000


def rebuild_log_effects(
    conn: sqlite3.Connection,
    project: Project,
    scope_file_paths: list[str] | None,
) -> dict[str, Any]:
    paths = sorted(set(scope_file_paths or []))
    delete_scope(conn, project.project_id, paths)
    candidates = wrapper_call_candidates(conn, project.project_id, paths)
    rows = []
    source_cache: dict[str, list[str]] = {}
    for item in candidates:
        message, raw_call = call_message(project.root, item, source_cache)
        rows.append((
            project.project_id, item["file_path"], item["line"], item["caller"],
            item["wrapper"], item["sink_log_id"], item["level"], item["logger"],
            message or item["sink_template"], item["evidence_class"], item["wrapper_depth"],
            int(bool(item.get("truncated"))),
            json.dumps(item["call_path"]), json.dumps(item["call_path_locations"]),
            raw_call, item["source_digest"], item["index_generation"], now_iso(),
        ))
    conn.executemany(
        """
        INSERT INTO code_log_effects(
          project_id, file_path, line, function, wrapper_symbol, sink_log_id,
          level, logger, message_template, evidence_class, wrapper_depth,
          truncated, call_path, call_path_locations, raw_call, source_digest,
          index_generation, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return {
        "schema_version": "log-effect/v1",
        "wrappers_resolved": len({item["wrapper"] for item in candidates}),
        "effects_emitted": len(rows),
        "truncated": any(item.get("truncated") for item in candidates),
        "max_wrapper_depth": max((item["wrapper_depth"] for item in candidates), default=0),
    }


def delete_scope(conn: sqlite3.Connection, project_id: str, paths: list[str]) -> None:
    if not paths:
        conn.execute("DELETE FROM code_log_effects WHERE project_id = ?", (project_id,))
        return
    for chunk in chunks(paths):
        conn.execute(
            f"DELETE FROM code_log_effects WHERE project_id = ? AND file_path IN ({','.join('?' for _ in chunk)})",
            (project_id, *chunk),
        )


def wrapper_call_candidates(
    conn: sqlite3.Connection, project_id: str, paths: list[str],
) -> list[dict[str, Any]]:
    calls: list[sqlite3.Row] = []
    sinks: list[sqlite3.Row] = []
    symbol_ids = scoped_symbol_ids(conn, project_id, paths) if paths else []
    reachable_ids, closure_truncated = (
        forward_symbol_ids(conn, project_id, symbol_ids) if paths else ([], False)
    )
    scopes = chunks(reachable_ids) if paths else [[]]
    for scope_ids in scopes:
        calls.extend(query_call_edges(conn, project_id, scope_ids))
        sinks.extend(query_direct_sinks(conn, project_id, scope_ids))
    candidates = derive_candidates(calls, sinks, set(symbol_ids) if paths else None)
    if closure_truncated:
        for item in candidates:
            item["truncated"] = True
    return candidates


def forward_symbol_ids(
    conn: sqlite3.Connection,
    project_id: str,
    seed_ids: list[int],
    limit: int = FORWARD_EXPANSION_LIMIT,
) -> tuple[list[int], bool]:
    visited = set(seed_ids)
    frontier = set(seed_ids)
    discovered: set[int] = set()
    truncated = False
    for _depth in range(MAX_WRAPPER_DEPTH):
        next_frontier: set[int] = set()
        for scope in chunks(sorted(frontier)):
            remaining = limit - len(discovered) - len(next_frontier)
            if remaining <= 0:
                truncated = True
                break
            rows = conn.execute(
                f"""
                SELECT DISTINCT target_id FROM memory_edges
                WHERE project_id = ? AND valid_to IS NULL
                  AND source_type = 'code_symbol' AND target_type = 'code_symbol'
                  AND relation = 'calls'
                  AND source_id IN ({','.join('?' for _ in scope)})
                ORDER BY target_id LIMIT ?
                """,
                (project_id, *scope, remaining + 1),
            ).fetchall()
            if len(rows) > remaining:
                truncated = True
            next_frontier.update(
                int(row["target_id"]) for row in rows[:remaining]
                if int(row["target_id"]) not in visited
            )
        if not next_frontier:
            break
        discovered.update(next_frontier)
        visited.update(next_frontier)
        frontier = next_frontier
    return sorted(visited), truncated


def scoped_symbol_ids(
    conn: sqlite3.Connection, project_id: str, paths: list[str],
) -> list[int]:
    result: list[int] = []
    for path_chunk in chunks(paths):
        rows = conn.execute(
            f"SELECT id FROM code_symbols WHERE project_id = ? "
            f"AND file_path IN ({','.join('?' for _ in path_chunk)})",
            (project_id, *path_chunk),
        ).fetchall()
        result.extend(int(row["id"]) for row in rows)
    return result


def query_call_edges(
    conn: sqlite3.Connection, project_id: str, symbol_ids: list[int],
) -> list[sqlite3.Row]:
    scope_sql = f" AND calls.source_id IN ({','.join('?' for _ in symbol_ids)})" if symbol_ids else ""
    return conn.execute(
        """
        SELECT caller.id AS caller_id, caller.file_path, caller.symbol AS caller,
               caller.source_digest,
               caller.index_generation,
               wrapper.id AS wrapper_id, wrapper.symbol AS wrapper,
               wrapper.file_path AS wrapper_file_path, calls.evidence,
               calls.evidence_kind
        FROM memory_edges calls
        JOIN code_symbols caller ON caller.id = calls.source_id AND calls.source_type = 'code_symbol'
        JOIN code_symbols wrapper ON wrapper.id = calls.target_id AND calls.target_type = 'code_symbol'
        WHERE calls.project_id = ? AND calls.relation = 'calls' AND calls.valid_to IS NULL
          AND caller.id != wrapper.id
        """ + scope_sql + " ORDER BY caller.file_path, caller.id, wrapper.id",
        (project_id, *symbol_ids),
    ).fetchall()


def query_direct_sinks(
    conn: sqlite3.Connection, project_id: str, symbol_ids: list[int],
) -> list[sqlite3.Row]:
    scope_sql = f" AND direct.source_id IN ({','.join('?' for _ in symbol_ids)})" if symbol_ids else ""
    return conn.execute(
        """
        SELECT wrapper.id AS wrapper_id, wrapper.symbol AS wrapper,
               wrapper.file_path AS wrapper_file_path, log.file_path AS sink_file_path,
               direct.target_id AS sink_log_id, log.level, log.logger,
               log.message_template AS sink_template
        FROM memory_edges direct
        JOIN code_symbols wrapper ON wrapper.id = direct.source_id
          AND direct.source_type = 'code_symbol'
        JOIN code_log_statements log ON log.id = direct.target_id
        WHERE direct.project_id = ? AND direct.relation = 'emits_log'
          AND direct.valid_to IS NULL
        """ + scope_sql + " ORDER BY wrapper.id, log.id",
        (project_id, *symbol_ids),
    ).fetchall()


def derive_candidates(
    call_rows: list[sqlite3.Row],
    sink_rows: list[sqlite3.Row],
    root_ids: set[int] | None = None,
) -> list[dict[str, Any]]:
    adjacency: dict[int, list[dict[str, Any]]] = defaultdict(list)
    names: dict[int, str] = {}
    locations: dict[int, str] = {}
    for row in call_rows:
        edge = dict(row)
        adjacency[int(row["caller_id"])].append(edge)
        names[int(row["caller_id"])] = str(row["caller"])
        names[int(row["wrapper_id"])] = str(row["wrapper"])
        locations[int(row["caller_id"])] = str(row["file_path"])
        locations[int(row["wrapper_id"])] = str(row["wrapper_file_path"])
    sinks: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in sink_rows:
        sinks[int(row["wrapper_id"])].append(dict(row))
        names[int(row["wrapper_id"])] = str(row["wrapper"])
        locations[int(row["wrapper_id"])] = str(row["wrapper_file_path"])
    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    counts: dict[int, int] = defaultdict(int)
    truncated_callers: set[int] = set()
    for row in call_rows:
        caller_id = int(row["caller_id"])
        if root_ids is not None and caller_id not in root_ids:
            continue
        evidence = parse_evidence(row["evidence"])
        line = int(evidence.get("line") or 0)
        if line <= 0:
            continue
        paths = sink_paths(int(row["wrapper_id"]), adjacency, sinks, {caller_id}, 1)
        for sink, symbol_ids, depth, nested_inferred in paths:
            symbols = [names.get(symbol_id, str(symbol_id)) for symbol_id in symbol_ids]
            key = (row["file_path"], row["caller"], tuple(symbols), sink["sink_log_id"], line)
            if counts[caller_id] >= MAX_EFFECTS_PER_CALLER:
                truncated_callers.add(caller_id)
                continue
            if key in seen:
                continue
            seen.add(key)
            counts[caller_id] += 1
            sink_api = f"{sink['logger']}.{sink['level']}"
            outer = dict(row)
            result.append({
                **outer, **sink, "wrapper": outer["wrapper"],
                "line": line, "wrapper_depth": depth,
                "evidence_class": (
                    "inferred_wrapped"
                    if nested_inferred or inferred_edge(row)
                    else "static_wrapped"
                ),
                "sink_api": sink_api,
                "call_path": [str(row["caller"]), *symbols, sink_api],
                "call_path_locations": [
                    f"{row['file_path']}#{row['caller']}",
                    *(f"{locations.get(symbol_id, '')}#{names.get(symbol_id, symbol_id)}" for symbol_id in symbol_ids),
                    f"{sink['sink_file_path']}#{sink_api}",
                ],
                "truncated": len(paths) > MAX_EFFECTS_PER_CALLER,
            })
    for item in result:
        if int(item["caller_id"]) in truncated_callers:
            item["truncated"] = True
    return result


def sink_paths(
    current: int,
    adjacency: dict[int, list[dict[str, Any]]],
    sinks: dict[int, list[dict[str, Any]]],
    visited: set[int],
    depth: int,
) -> list[tuple[dict[str, Any], list[int], int, bool]]:
    if current in visited or depth > MAX_WRAPPER_DEPTH:
        return []
    current_path = [current]
    result = [
        (sink, current_path, depth, False) for sink in sinks.get(current, [])
    ][:PATH_SEARCH_LIMIT]
    if depth == MAX_WRAPPER_DEPTH or len(result) >= PATH_SEARCH_LIMIT:
        return result
    for edge in adjacency.get(current, []):
        target = int(edge["wrapper_id"])
        for sink, symbols, nested_depth, nested_inferred in sink_paths(
            target, adjacency, sinks, visited | {current}, depth + 1,
        ):
            result.append((
                sink, [*current_path, *symbols], nested_depth,
                inferred_edge(edge) or nested_inferred,
            ))
            if len(result) >= PATH_SEARCH_LIMIT:
                return result
    return result


def call_message(
    root: Path, item: dict[str, Any], source_cache: dict[str, list[str]],
) -> tuple[str, str]:
    file_path = str(item["file_path"])
    if file_path not in source_cache:
        try:
            source_cache[file_path] = (root / file_path).read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines(keepends=True)
        except OSError:
            source_cache[file_path] = []
    line = int(item["line"])
    text = "".join(source_cache[file_path][max(0, line - 1):line + 19])
    pattern = rf"\b(?:[A-Za-z_$][\w$]*\.)?{re.escape(str(item['wrapper']))}\s*\("
    calls = [call for call_line, call in scan_calls(text, pattern) if call_line == 1]
    if len(calls) != 1:
        return "", ""
    literals = string_literals(calls[0])
    return (literals[0] if literals else "", calls[0])


def parse_evidence(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value or ""))
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def inferred_edge(value: Any) -> bool:
    if isinstance(value, sqlite3.Row):
        value = dict(value)
    return str(value.get("evidence_kind") or "").startswith("inferred_")


def chunks(values: list[str], size: int = 400) -> list[list[str]]:
    return [values[index:index + size] for index in range(0, len(values), size)]
