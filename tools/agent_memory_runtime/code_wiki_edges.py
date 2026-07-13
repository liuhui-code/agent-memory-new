# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3

from .code_wiki_extractors import extract_arkts_reference_symbols
from .code_wiki_imports import relative_project_path, resolve_arkts_router_targets, resolve_js_imports
from .models import Project
from .storage import now_iso

def scope_node_ids(
    conn: sqlite3.Connection,
    project_id: str,
    file_paths: list[str],
) -> dict[str, set[int]]:
    if not file_paths:
        return {"code_file": set(), "code_symbol": set(), "code_log_statement": set()}
    placeholders = ",".join("?" for _ in file_paths)
    file_rows = conn.execute(
        f"""
        SELECT id
        FROM code_files
        WHERE project_id = ? AND file_path IN ({placeholders})
        """,
        (project_id, *file_paths),
    ).fetchall()
    symbol_rows = conn.execute(
        f"""
        SELECT id
        FROM code_symbols
        WHERE project_id = ? AND file_path IN ({placeholders})
        """,
        (project_id, *file_paths),
    ).fetchall()
    log_rows = conn.execute(
        f"""
        SELECT id
        FROM code_log_statements
        WHERE project_id = ? AND file_path IN ({placeholders})
        """,
        (project_id, *file_paths),
    ).fetchall()
    return {
        "code_file": {int(row["id"]) for row in file_rows},
        "code_symbol": {int(row["id"]) for row in symbol_rows},
        "code_log_statement": {int(row["id"]) for row in log_rows},
    }



def delete_edges_for_scope(
    conn: sqlite3.Connection,
    project_id: str,
    scoped_ids: dict[str, set[int]],
) -> None:
    for entity_type, ids in scoped_ids.items():
        if not ids:
            continue
        placeholders = ",".join("?" for _ in ids)
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
            (project_id, entity_type, *ids, entity_type, *ids),
        )



def rebuild_code_memory_edges(
    conn: sqlite3.Connection,
    project: Project,
    scope_file_paths: list[str] | None = None,
) -> None:
    ts = now_iso()
    project_id = project.project_id
    files = conn.execute(
        "SELECT id, file_path, language FROM code_files WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    symbols = conn.execute(
        "SELECT id, file_path, symbol, symbol_type FROM code_symbols WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    logs = conn.execute(
        "SELECT id, file_path, function, line FROM code_log_statements WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    file_ids = {row["file_path"]: row["id"] for row in files}
    symbol_ids = {
        (row["file_path"], row["symbol"]): row["id"]
        for row in symbols
    }
    scoped_paths = set(scope_file_paths or [])
    scoped_symbols = [row for row in symbols if not scoped_paths or row["file_path"] in scoped_paths]
    scoped_logs = [row for row in logs if not scoped_paths or row["file_path"] in scoped_paths]
    scoped_files = [row for row in files if not scoped_paths or row["file_path"] in scoped_paths]
    for row in scoped_symbols:
        file_id = file_ids.get(row["file_path"])
        if file_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_file",
                file_id,
                "contains",
                "code_symbol",
                row["id"],
                row["file_path"],
                0.9,
                ts,
            )
    for row in scoped_logs:
        file_id = file_ids.get(row["file_path"])
        evidence = f"{row['file_path']}:{row['line']}" if row["line"] else row["file_path"]
        if file_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_file",
                file_id,
                "contains",
                "code_log_statement",
                row["id"],
                evidence,
                0.9,
                ts,
            )
        function_name = row["function"]
        symbol_id = symbol_ids.get((row["file_path"], function_name)) if function_name else None
        if symbol_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_symbol",
                symbol_id,
                "emits_log",
                "code_log_statement",
                row["id"],
                evidence,
                0.8,
                ts,
            )

    insert_arkts_knowledge_edges(conn, project, scoped_files, symbols, ts)



def insert_arkts_knowledge_edges(
    conn: sqlite3.Connection,
    project: Project,
    files: list[sqlite3.Row],
    symbols: list[sqlite3.Row],
    ts: str,
) -> None:
    file_ids = {row["file_path"]: row["id"] for row in files}
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
