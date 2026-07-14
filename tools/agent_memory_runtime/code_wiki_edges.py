# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
import sqlite3
import subprocess
from typing import Any

from .code_wiki_extractors import extract_arkts_reference_symbols
from .code_wiki_design_edges import insert_design_edges
from .code_wiki_imports import relative_project_path, resolve_arkts_router_targets, resolve_js_imports
from .models import Project
from .graph_quality_snapshot import bump_graph_revision
from .semantic_index import persist_semantic_index
from .storage import now_iso

EDGE_EXTRACTOR_VERSION = "code-wiki:v4"
SQL_CHUNK_SIZE = 400


def source_revision(project: Project) -> str:
    try:
        process = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unversioned"
    revision = process.stdout.strip()
    return f"git:{revision}" if process.returncode == 0 and revision else "unversioned"


def scope_node_ids(
    conn: sqlite3.Connection,
    project_id: str,
    file_paths: list[str],
) -> dict[str, set[int]]:
    if not file_paths:
        return {"code_file": set(), "code_symbol": set(), "code_log_statement": set()}
    collected: dict[str, set[int]] = {
        "code_file": set(), "code_symbol": set(), "code_log_statement": set(),
    }
    for table, entity_type in (
        ("code_files", "code_file"),
        ("code_symbols", "code_symbol"),
        ("code_log_statements", "code_log_statement"),
    ):
        for chunk in sql_chunks(file_paths):
            rows = conn.execute(
                f"SELECT id FROM {table} WHERE project_id = ? AND file_path IN ({','.join('?' for _ in chunk)})",
                (project_id, *chunk),
            ).fetchall()
            collected[entity_type].update(int(row["id"]) for row in rows)
    return {
        "code_file": collected["code_file"],
        "code_symbol": collected["code_symbol"],
        "code_log_statement": collected["code_log_statement"],
    }



def delete_edges_for_scope(
    conn: sqlite3.Connection,
    project_id: str,
    scoped_ids: dict[str, set[int]],
) -> None:
    for entity_type, ids in scoped_ids.items():
        if not ids:
            continue
        for chunk in sql_chunks(sorted(ids)):
            placeholders = ",".join("?" for _ in chunk)
            conn.execute(
                f"""
                DELETE FROM memory_edges
                WHERE project_id = ?
                  AND (
                    (source_type = ? AND source_id IN ({placeholders}))
                    OR
                    (target_type = ? AND target_id IN ({placeholders}))
                  )
                """,
                (project_id, entity_type, *chunk, entity_type, *chunk),
            )


def dependent_file_paths_for_scope(
    conn: sqlite3.Connection,
    project_id: str,
    scoped_ids: dict[str, set[int]],
    limit: int = 2000,
) -> list[str]:
    sources: dict[str, set[int]] = {"code_file": set(), "code_symbol": set(), "code_log_statement": set()}
    for target_type, ids in scoped_ids.items():
        if not ids:
            continue
        for chunk in sql_chunks(sorted(ids)):
            remaining = limit - sum(len(values) for values in sources.values())
            if remaining <= 0:
                break
            rows = conn.execute(
                f"""
                SELECT source_type, source_id FROM memory_edges
                WHERE project_id = ? AND valid_to IS NULL
                  AND target_type = ? AND target_id IN ({','.join('?' for _ in chunk)})
                  AND source_type IN ('code_file', 'code_symbol', 'code_log_statement')
                ORDER BY source_type, source_id
                LIMIT ?
                """,
                (project_id, target_type, *chunk, remaining),
            ).fetchall()
            for row in rows:
                sources[str(row["source_type"])].add(int(row["source_id"]))
    paths: set[str] = set()
    for entity_type, table in (
        ("code_file", "code_files"),
        ("code_symbol", "code_symbols"),
        ("code_log_statement", "code_log_statements"),
    ):
        ids = sorted(sources[entity_type])[:limit]
        if not ids:
            continue
        for chunk in sql_chunks(ids):
            rows = conn.execute(
                f"SELECT file_path FROM {table} WHERE project_id = ? AND id IN ({','.join('?' for _ in chunk)})",
                (project_id, *chunk),
            ).fetchall()
            paths.update(str(row["file_path"]) for row in rows)
    return sorted(paths)[:limit]


def sql_chunks(items: list[Any], size: int = SQL_CHUNK_SIZE) -> list[list[Any]]:
    return [items[index:index + size] for index in range(0, len(items), size)]



def rebuild_code_memory_edges(
    conn: sqlite3.Connection,
    project: Project,
    scope_file_paths: list[str] | None = None,
) -> dict[str, Any]:
    ts = now_iso()
    project_id = project.project_id
    revision = source_revision(project)
    previous_edge_id = int(
        conn.execute("SELECT COALESCE(MAX(id), 0) AS id FROM memory_edges").fetchone()["id"]
    )
    files = conn.execute(
        "SELECT id, file_path, language FROM code_files WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    scoped_paths = set(scope_file_paths or [])
    scoped_files = [row for row in files if not scoped_paths or row["file_path"] in scoped_paths]
    symbols = load_rebuild_symbols(conn, project, scoped_files, scoped_paths)
    logs = load_scoped_rows(
        conn,
        "code_log_statements",
        "id, file_path, function, line",
        project_id,
        scoped_paths,
    )
    file_ids = {row["file_path"]: row["id"] for row in files}
    symbol_ids = {
        (row["file_path"], row["symbol"]): row["id"]
        for row in symbols
    }
    scoped_symbols = [row for row in symbols if not scoped_paths or row["file_path"] in scoped_paths]
    edge_rows: list[tuple[Any, ...]] = []
    for row in scoped_symbols:
        file_id = file_ids.get(row["file_path"])
        if file_id:
            edge_rows.append(
                (project_id, "code_file", file_id, "contains", "code_symbol", row["id"], row["file_path"], 0.9, ts)
            )
    for row in logs:
        file_id = file_ids.get(row["file_path"])
        evidence = f"{row['file_path']}:{row['line']}" if row["line"] else row["file_path"]
        if file_id:
            edge_rows.append(
                (project_id, "code_file", file_id, "contains", "code_log_statement", row["id"], evidence, 0.9, ts)
            )
        function_name = row["function"]
        symbol_id = symbol_ids.get((row["file_path"], function_name)) if function_name else None
        if symbol_id:
            edge_rows.append(
                (project_id, "code_symbol", symbol_id, "emits_log", "code_log_statement", row["id"], evidence, 0.8, ts)
            )
    insert_memory_edges(conn, edge_rows)

    insert_arkts_knowledge_edges(conn, project, scoped_files, files, symbols, ts)
    insert_design_edges(conn, project, scoped_files, files, symbols, ts)
    annotate_extracted_edges(conn, project, previous_edge_id, revision, ts)
    semantic_stats = persist_semantic_index(
        conn,
        project,
        [str(row["file_path"]) for row in scoped_files],
        revision,
    )
    bump_graph_revision(conn, project_id)
    return semantic_stats


def load_scoped_rows(
    conn: sqlite3.Connection,
    table: str,
    columns: str,
    project_id: str,
    scoped_paths: set[str],
) -> list[sqlite3.Row]:
    if not scoped_paths:
        return conn.execute(f"SELECT {columns} FROM {table} WHERE project_id = ?", (project_id,)).fetchall()
    rows: list[sqlite3.Row] = []
    for chunk in sql_chunks(sorted(scoped_paths)):
        rows.extend(
            conn.execute(
                f"SELECT {columns} FROM {table} WHERE project_id = ? AND file_path IN ({','.join('?' for _ in chunk)})",
                (project_id, *chunk),
            ).fetchall()
        )
    return rows


def load_rebuild_symbols(
    conn: sqlite3.Connection,
    project: Project,
    scoped_files: list[sqlite3.Row],
    scoped_paths: set[str],
) -> list[sqlite3.Row]:
    columns = "id, file_path, symbol, symbol_type"
    if not scoped_paths:
        return load_scoped_rows(conn, "code_symbols", columns, project.project_id, set())
    selected = {
        int(row["id"]): row
        for row in load_scoped_rows(conn, "code_symbols", columns, project.project_id, scoped_paths)
    }
    for chunk in sql_chunks(sorted(referenced_symbol_names(project, scoped_files))):
        rows = conn.execute(
            f"SELECT {columns} FROM code_symbols WHERE project_id = ? AND symbol IN ({','.join('?' for _ in chunk)})",
            (project.project_id, *chunk),
        ).fetchall()
        selected.update({int(row["id"]): row for row in rows})
    return [selected[key] for key in sorted(selected)]


def referenced_symbol_names(project: Project, files: list[sqlite3.Row]) -> set[str]:
    names: set[str] = set()
    for row in files:
        if row["language"] != "ArkTS":
            continue
        try:
            text = (project.root / str(row["file_path"])).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        names.update(re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*", text))
    return names


def annotate_extracted_edges(
    conn: sqlite3.Connection,
    project: Project,
    previous_edge_id: int,
    revision: str,
    timestamp: str,
) -> None:
    conn.execute(
        """
        UPDATE memory_edges
        SET source_revision = ?,
            extractor_version = ?,
            valid_from = COALESCE(valid_from, created_at),
            valid_to = NULL,
            evidence_kind = CASE relation
              WHEN 'contains' THEN 'static_containment'
              WHEN 'emits_log' THEN 'code_observability'
              WHEN 'imports' THEN 'static_import'
              WHEN 'routes_to' THEN 'static_route'
              WHEN 'uses_resource' THEN 'static_resource'
              WHEN 'defines_state' THEN 'static_state'
              WHEN 'renders_component' THEN 'static_component_composition'
              WHEN 'uses_service' THEN 'static_service_use'
              WHEN 'dispatches_event' THEN 'static_event_dispatch'
              WHEN 'handles_event' THEN 'static_event_binding'
              WHEN 'configured_by' THEN 'static_configuration'
              WHEN 'tested_by' THEN 'static_test_relation'
              WHEN 'calls' THEN 'static_call'
              WHEN 'reads_state' THEN 'static_state_read'
              WHEN 'writes_state' THEN 'static_state_write'
              WHEN 'implements' THEN 'static_implementation'
              WHEN 'overrides' THEN 'static_override'
              WHEN 'exposes_api' THEN 'static_api_export'
              WHEN 'consumes_api' THEN 'static_api_use'
              WHEN 'registers_callback' THEN 'static_callback'
              ELSE 'static_structure'
            END,
            last_verified_at = ?
        WHERE project_id = ? AND id > ? AND extractor_version = 'legacy'
        """,
        (revision, EDGE_EXTRACTOR_VERSION, timestamp, project.project_id, previous_edge_id),
    )



def insert_arkts_knowledge_edges(
    conn: sqlite3.Connection,
    project: Project,
    files: list[sqlite3.Row],
    all_files: list[sqlite3.Row],
    symbols: list[sqlite3.Row],
    ts: str,
) -> None:
    file_ids = {row["file_path"]: row["id"] for row in all_files}
    symbol_ids = {
        (row["file_path"], row["symbol"], row["symbol_type"]): row["id"]
        for row in symbols
    }
    for row in files:
        if row["language"] != "ArkTS":
            continue
        source_rel = row["file_path"]
        source_id = row["id"]
        source_abs = project.root / source_rel
        try:
            text = source_abs.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for target in resolve_js_imports(project, source_abs, text, [".ets", ".ts", ".js"]):
            target_rel = relative_project_path(project, target)
            target_id = file_ids.get(target_rel)
            if target_id:
                insert_memory_edge(
                    conn,
                    project.project_id,
                    "code_file",
                    source_id,
                    "imports",
                    "code_file",
                    target_id,
                    f"{source_rel} -> {target_rel}",
                    0.85,
                    ts,
                )

        for target in resolve_arkts_router_targets(project, source_abs, text):
            target_rel = relative_project_path(project, target)
            target_id = file_ids.get(target_rel)
            if target_id:
                insert_memory_edge(
                    conn,
                    project.project_id,
                    "code_file",
                    source_id,
                    "routes_to",
                    "code_file",
                    target_id,
                    f"{source_rel} -> {target_rel}",
                    0.85,
                    ts,
                )

        for resource, kind in extract_arkts_reference_symbols(text):
            if kind != "resource":
                continue
            symbol_id = symbol_ids.get((source_rel, resource, "resource"))
            if symbol_id:
                insert_memory_edge(
                    conn,
                    project.project_id,
                    "code_file",
                    source_id,
                    "uses_resource",
                    "code_symbol",
                    symbol_id,
                    f"{source_rel} uses {resource}",
                    0.8,
                    ts,
                )

        for state_name, kind in extract_arkts_reference_symbols(text):
            if kind != "state":
                continue
            symbol_id = symbol_ids.get((source_rel, state_name, "state"))
            if symbol_id:
                insert_memory_edge(
                    conn,
                    project.project_id,
                    "code_file",
                    source_id,
                    "defines_state",
                    "code_symbol",
                    symbol_id,
                    f"{source_rel} defines state {state_name}",
                    0.8,
                    ts,
                )



def insert_memory_edge(
    conn: sqlite3.Connection,
    project_id: str,
    source_type: str,
    source_id: int,
    relation: str,
    target_type: str,
    target_id: int,
    evidence: str,
    confidence: float,
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO memory_edges(
          project_id, source_type, source_id, relation, target_type,
          target_id, evidence, confidence, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            source_type,
            source_id,
            relation,
            target_type,
            target_id,
            evidence,
            confidence,
            created_at,
        ),
    )


def insert_memory_edges(conn: sqlite3.Connection, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO memory_edges(
          project_id, source_type, source_id, relation, target_type,
          target_id, evidence, confidence, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
