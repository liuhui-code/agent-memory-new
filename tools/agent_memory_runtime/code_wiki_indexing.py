# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from .code_wiki_edges import delete_edges_for_scope, rebuild_code_memory_edges, scope_node_ids
from .code_wiki_extractors import extract_log_statements, extract_symbols, language_for, should_skip_dir, summarize_file, summarize_symbol
from .graph_refresh_metrics import edge_rebuild_metrics, scoped_edge_summary
from .models import Project
from .semantic_refresh import load_business_semantics, restore_business_semantics
from .storage import connect, now_iso

def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()



def build_file_snapshot(project: Project, files: list[Path]) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted({item.resolve() for item in files}):
        try:
            rel = str(path.relative_to(project.root))
        except ValueError:
            continue
        if not path.exists() or not path.is_file():
            continue
        snapshot[rel] = file_sha256(path)
    return snapshot



def learn_scope_key(
    scope_type: str,
    source_root: Path,
    target_path: str | None = None,
    entry_path: str | None = None,
    depth: int | None = None,
) -> str:
    raw = json.dumps(
        {
            "scope_type": scope_type,
            "source_root": str(source_root),
            "target_path": target_path or "",
            "entry_path": entry_path or "",
            "depth": depth,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]



def record_learn_scope(
    project: Project,
    source_root: Path,
    scope_type: str,
    mode: str,
    files: list[Path],
    *,
    target_path: str | None = None,
    entry_path: str | None = None,
    depth: int | None = None,
) -> int:
    ts = now_iso()
    snapshot = build_file_snapshot(project, files)
    scope_key = learn_scope_key(
        scope_type,
        source_root,
        target_path=target_path,
        entry_path=entry_path,
        depth=depth,
    )
    with connect(project) as conn:
        conn.execute(
            """
            INSERT INTO learn_scopes(
              project_id, scope_key, scope_type, source_root, target_path, entry_path,
              depth, mode, file_snapshot, file_count, status, created_at, updated_at, last_refreshed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
            ON CONFLICT(project_id, scope_key) DO UPDATE SET
              scope_type=excluded.scope_type,
              source_root=excluded.source_root,
              target_path=excluded.target_path,
              entry_path=excluded.entry_path,
              depth=excluded.depth,
              mode=excluded.mode,
              file_snapshot=excluded.file_snapshot,
              file_count=excluded.file_count,
              status='active',
              updated_at=excluded.updated_at,
              last_refreshed_at=excluded.last_refreshed_at
            """,
            (
                project.project_id,
                scope_key,
                scope_type,
                str(source_root),
                target_path,
                entry_path,
                depth,
                mode,
                json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                len(snapshot),
                ts,
                ts,
                ts,
            ),
        )
        row = conn.execute(
            """
            SELECT id
            FROM learn_scopes
            WHERE project_id = ? AND scope_key = ?
            """,
            (project.project_id, scope_key),
        ).fetchone()
        conn.commit()
    return int(row["id"])



def write_wiki_scope(
    project: Project,
    files: list[Path],
    *,
    replace: bool = False,
    retired_relative_files: list[str] | None = None,
) -> dict[str, Any]:
    stats = write_wiki_index(project, files, replace=replace)
    retired = sorted(
        {
            str(item).strip()
            for item in (retired_relative_files or [])
            if str(item).strip()
        }
    )
    if retired:
        with connect(project) as conn:
            retired_ids = scope_node_ids(conn, project.project_id, retired)
            delete_edges_for_scope(conn, project.project_id, retired_ids)
            for file_path in retired:
                conn.execute(
                    "DELETE FROM code_files WHERE project_id = ? AND file_path = ?",
                    (project.project_id, file_path),
                )
                conn.execute(
                    "DELETE FROM code_symbols WHERE project_id = ? AND file_path = ?",
                    (project.project_id, file_path),
                )
                conn.execute(
                    "DELETE FROM code_log_statements WHERE project_id = ? AND file_path = ?",
                    (project.project_id, file_path),
                )
            stats["memory_edges_total"] = conn.execute(
                "SELECT COUNT(*) AS count FROM memory_edges WHERE project_id = ?",
                (project.project_id,),
            ).fetchone()["count"]
            conn.commit()
        stats["retired_files"] = retired
    else:
        stats["retired_files"] = []
    return stats



def load_learn_scopes(project: Project, scope_id: int | None = None) -> list[sqlite3.Row]:
    with connect(project) as conn:
        if scope_id is not None:
            row = conn.execute(
                """
                SELECT *
                FROM learn_scopes
                WHERE project_id = ? AND id = ?
                ORDER BY id
                """,
                (project.project_id, scope_id),
            ).fetchone()
            return [row] if row else []
        return conn.execute(
            """
            SELECT *
            FROM learn_scopes
            WHERE project_id = ? AND status = 'active'
            ORDER BY updated_at DESC, id DESC
            """,
            (project.project_id,),
        ).fetchall()



def write_wiki_index(project: Project, files: list[Path], replace: bool = False) -> dict[str, Any]:
    ts = now_iso()
    unique_files = sorted({path.resolve() for path in files})
    relative_files: list[tuple[Path, Path, str, str]] = []
    for path in unique_files:
        try:
            rel = path.relative_to(project.root)
        except ValueError:
            continue
        if should_skip_dir(rel):
            continue
        language = language_for(path)
        if not language:
            continue
        relative_files.append((path, rel, str(rel), language))

    language_counts: Counter[str] = Counter()
    symbol_type_counts: Counter[str] = Counter()
    log_level_counts: Counter[str] = Counter()
    symbols_by_file: dict[str, list[tuple[str, str]]] = {}
    logs_by_file: dict[str, list[dict[str, Any]]] = {}
    for path, _rel, rel_text, language in relative_files:
        language_counts[language] += 1
        symbols = extract_symbols(path, language)
        logs = extract_log_statements(path, language)
        symbols_by_file[rel_text] = symbols
        logs_by_file[rel_text] = logs
        for _symbol, symbol_type in symbols:
            symbol_type_counts[symbol_type or "symbol"] += 1
        for log in logs:
            log_level_counts[str(log.get("level") or "log")] += 1

    affected_file_paths = [rel_text for _, _, rel_text, _ in relative_files]
    with connect(project) as conn:
        previous_scope_ids = scope_node_ids(conn, project.project_id, affected_file_paths)
        edges_before = scoped_edge_summary(conn, project.project_id, previous_scope_ids)
        business_snapshot = (
            load_business_semantics(conn, project.project_id, affected_file_paths)
            if not replace
            else {"code_files": {}, "code_symbols": {}, "code_log_statements": {}}
        )
        if replace:
            conn.execute("DELETE FROM code_files WHERE project_id = ?", (project.project_id,))
            conn.execute("DELETE FROM code_symbols WHERE project_id = ?", (project.project_id,))
            conn.execute("DELETE FROM code_log_statements WHERE project_id = ?", (project.project_id,))
            conn.execute("DELETE FROM memory_edges WHERE project_id = ?", (project.project_id,))
        else:
            delete_edges_for_scope(conn, project.project_id, previous_scope_ids)
            for _, _, rel_text, _ in relative_files:
                conn.execute(
                    "DELETE FROM code_files WHERE project_id = ? AND file_path = ?",
                    (project.project_id, rel_text),
                )
                conn.execute(
                    "DELETE FROM code_symbols WHERE project_id = ? AND file_path = ?",
                    (project.project_id, rel_text),
                )
                conn.execute(
                    "DELETE FROM code_log_statements WHERE project_id = ? AND file_path = ?",
                    (project.project_id, rel_text),
                )
        for path, _rel, rel_text, language in relative_files:
            summary = summarize_file(path, language)
            conn.execute(
                """
                INSERT INTO code_files(project_id, file_path, summary, language, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project.project_id, rel_text, summary, language, ts),
            )
            for symbol, symbol_type in symbols_by_file.get(rel_text, []):
                summary = summarize_symbol(rel_text, symbol, symbol_type, language)
                conn.execute(
                    """
                    INSERT INTO code_symbols(project_id, file_path, symbol, symbol_type, summary, calls, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (project.project_id, rel_text, symbol, symbol_type, summary, "", ts),
                )
            for log in logs_by_file.get(rel_text, []):
                conn.execute(
                    """
                    INSERT INTO code_log_statements(
                      project_id, file_path, line, function, level, logger,
                      message_template, raw_statement, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project.project_id,
                        rel_text,
                        log.get("line"),
                        log.get("function"),
                        log.get("level"),
                        log.get("logger"),
                        log.get("message_template") or "",
                        log.get("raw_statement"),
                        ts,
                    ),
                )
        business_semantics_restored = restore_business_semantics(conn, project.project_id, business_snapshot)
        rebuild_code_memory_edges(conn, project, scope_file_paths=None if replace else affected_file_paths)
        refreshed_scope_ids = scope_node_ids(conn, project.project_id, affected_file_paths)
        edges_after = scoped_edge_summary(conn, project.project_id, refreshed_scope_ids)
        memory_edges_total = conn.execute(
            "SELECT COUNT(*) AS count FROM memory_edges WHERE project_id = ?",
            (project.project_id,),
        ).fetchone()["count"]
        conn.commit()
    return {
        "files_indexed": len(relative_files),
        "languages": dict(sorted(language_counts.items())),
        "symbols_total": sum(symbol_type_counts.values()),
        "symbols_by_type": dict(sorted(symbol_type_counts.items())),
        "code_logs_total": sum(log_level_counts.values()),
        "code_logs_by_level": dict(sorted(log_level_counts.items())),
        "business_semantics_restored": business_semantics_restored,
        "edge_rebuild": edge_rebuild_metrics(
            scope_file_paths=affected_file_paths,
            before=edges_before,
            after=edges_after,
            replace=replace,
        ),
        "memory_edges_total": memory_edges_total,
    }



def parse_stats_summary(stats: dict[str, Any]) -> str:
    return (
        f"parsed files={stats.get('files_indexed', 0)}, "
        f"symbols={stats.get('symbols_total', 0)}, "
        f"logs={stats.get('code_logs_total', 0)}, "
        f"edges={stats.get('memory_edges_total', 0)}"
    )
