# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3
from typing import Any

from .models import Project
from .storage import connect, now_iso


def _non_empty(*values: Any) -> bool:
    return any(str(value or "").strip() for value in values)


def _placeholders(values: list[str]) -> str:
    return ",".join("?" for _ in values)


def load_business_semantics(
    conn: sqlite3.Connection,
    project_id: str,
    file_paths: list[str],
) -> dict[str, dict[Any, dict[str, Any]]]:
    paths = sorted({str(path).strip() for path in file_paths if str(path).strip()})
    snapshot: dict[str, dict[Any, dict[str, Any]]] = {
        "code_files": {},
        "code_symbols": {},
        "code_log_statements": {},
    }
    if not paths:
        return snapshot
    placeholders = _placeholders(paths)
    file_rows = conn.execute(
        f"""
        SELECT file_path, business_summary, business_terms
        FROM code_files
        WHERE project_id = ? AND file_path IN ({placeholders})
        """,
        (project_id, *paths),
    ).fetchall()
    for row in file_rows:
        if _non_empty(row["business_summary"], row["business_terms"]):
            snapshot["code_files"][row["file_path"]] = dict(row)

    symbol_rows = conn.execute(
        f"""
        SELECT file_path, symbol, COALESCE(symbol_type, '') AS symbol_type,
               business_summary, business_terms
        FROM code_symbols
        WHERE project_id = ? AND file_path IN ({placeholders})
        """,
        (project_id, *paths),
    ).fetchall()
    for row in symbol_rows:
        if _non_empty(row["business_summary"], row["business_terms"]):
            key = (row["file_path"], row["symbol"], row["symbol_type"])
            snapshot["code_symbols"][key] = dict(row)

    log_rows = conn.execute(
        f"""
        SELECT file_path, COALESCE(function, '') AS function, COALESCE(level, '') AS level,
               COALESCE(logger, '') AS logger, message_template, business_summary,
               business_terms, business_event, trigger_stage, symptom_terms,
               likely_causes, process_hint, neighbor_terms
        FROM code_log_statements
        WHERE project_id = ? AND file_path IN ({placeholders})
        """,
        (project_id, *paths),
    ).fetchall()
    for row in log_rows:
        semantic_values = [
            row["business_summary"],
            row["business_terms"],
            row["business_event"],
            row["trigger_stage"],
            row["symptom_terms"],
            row["likely_causes"],
            row["process_hint"],
            row["neighbor_terms"],
        ]
        if _non_empty(*semantic_values):
            key = (row["file_path"], row["message_template"], row["function"], row["level"], row["logger"])
            snapshot["code_log_statements"][key] = dict(row)
    return snapshot


def restore_business_semantics(
    conn: sqlite3.Connection,
    project_id: str,
    snapshot: dict[str, dict[Any, dict[str, Any]]],
) -> dict[str, int]:
    counts = {"code_files": 0, "code_symbols": 0, "code_log_statements": 0}
    for file_path, row in snapshot.get("code_files", {}).items():
        cursor = conn.execute(
            """
            UPDATE code_files
            SET business_summary = ?, business_terms = ?
            WHERE project_id = ? AND file_path = ?
            """,
            (row.get("business_summary"), row.get("business_terms"), project_id, file_path),
        )
        counts["code_files"] += cursor.rowcount

    for key, row in snapshot.get("code_symbols", {}).items():
        file_path, symbol, symbol_type = key
        cursor = conn.execute(
            """
            UPDATE code_symbols
            SET business_summary = ?, business_terms = ?
            WHERE project_id = ? AND file_path = ? AND symbol = ? AND COALESCE(symbol_type, '') = ?
            """,
            (row.get("business_summary"), row.get("business_terms"), project_id, file_path, symbol, symbol_type),
        )
        counts["code_symbols"] += cursor.rowcount

    for key, row in snapshot.get("code_log_statements", {}).items():
        file_path, message_template, function, level, logger = key
        cursor = conn.execute(
            """
            UPDATE code_log_statements
            SET business_summary = ?, business_terms = ?, business_event = ?,
                trigger_stage = ?, symptom_terms = ?, likely_causes = ?,
                process_hint = ?, neighbor_terms = ?
            WHERE project_id = ? AND file_path = ? AND message_template = ?
              AND COALESCE(function, '') = ? AND COALESCE(level, '') = ?
              AND COALESCE(logger, '') = ?
            """,
            (
                row.get("business_summary"),
                row.get("business_terms"),
                row.get("business_event"),
                row.get("trigger_stage"),
                row.get("symptom_terms"),
                row.get("likely_causes"),
                row.get("process_hint"),
                row.get("neighbor_terms"),
                project_id,
                file_path,
                message_template,
                function,
                level,
                logger,
            ),
        )
        counts["code_log_statements"] += cursor.rowcount
    return counts


def load_refresh_semantic_snapshot(
    project: Project,
    file_paths: list[str],
) -> dict[str, dict[str, Any]]:
    paths = sorted({str(path).strip() for path in file_paths if str(path).strip()})
    if not paths:
        return {}
    placeholders = _placeholders(paths)
    snapshot: dict[str, dict[str, Any]] = {}
    with connect(project) as conn:
        file_rows = conn.execute(
            f"""
            SELECT file_path, summary, business_summary, business_terms
            FROM code_files
            WHERE project_id = ? AND file_path IN ({placeholders})
            """,
            (project.project_id, *paths),
        ).fetchall()
        log_rows = conn.execute(
            f"""
            SELECT file_path, message_template
            FROM code_log_statements
            WHERE project_id = ? AND file_path IN ({placeholders})
            ORDER BY file_path, message_template
            """,
            (project.project_id, *paths),
        ).fetchall()
    for row in file_rows:
        snapshot[row["file_path"]] = {
            "summary": row["summary"],
            "business_summary": row["business_summary"],
            "business_terms": row["business_terms"],
            "log_templates": [],
        }
    for row in log_rows:
        item = snapshot.setdefault(
            row["file_path"],
            {"summary": "", "business_summary": "", "business_terms": "", "log_templates": []},
        )
        item["log_templates"].append(row["message_template"])
    return snapshot


def _format_refresh_drift(
    previous: dict[str, Any] | None,
    current: dict[str, Any] | None,
) -> str:
    if not previous:
        return "source file changed during maintain-refresh-scope; verify whether stored business_summary still applies"
    current = current or {}
    changes: list[str] = []
    previous_summary = str(previous.get("summary") or "").strip()
    current_summary = str(current.get("summary") or "").strip()
    if previous_summary != current_summary:
        changes.append(f"summary changed from [{previous_summary}] to [{current_summary}]")
    previous_logs = {str(value) for value in previous.get("log_templates") or [] if str(value)}
    current_logs = {str(value) for value in current.get("log_templates") or [] if str(value)}
    added_logs = sorted(current_logs - previous_logs)
    removed_logs = sorted(previous_logs - current_logs)
    if added_logs:
        changes.append("logs added: " + "; ".join(added_logs[:5]))
    if removed_logs:
        changes.append("logs removed: " + "; ".join(removed_logs[:5]))
    if not changes:
        changes.append("file hash changed, but structural summary and log templates look unchanged")
    return "maintain-refresh-scope detected semantic drift: " + " | ".join(changes)


def record_refresh_semantic_conflicts(
    project: Project,
    changed_files: list[str],
    previous_snapshot: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    changed = sorted({str(path).strip() for path in changed_files if str(path).strip()})
    if not changed:
        return []
    previous_snapshot = previous_snapshot or {}
    current_snapshot = load_refresh_semantic_snapshot(project, changed)
    observed_at = now_iso()
    conflicts: list[dict[str, Any]] = []
    with connect(project) as conn:
        placeholders = _placeholders(changed)
        rows = conn.execute(
            f"""
            SELECT file_path, business_summary
            FROM code_files
            WHERE project_id = ? AND file_path IN ({placeholders})
              AND business_summary IS NOT NULL AND TRIM(business_summary) != ''
            """,
            (project.project_id, *changed),
        ).fetchall()
        for row in rows:
            incoming = _format_refresh_drift(
                previous_snapshot.get(row["file_path"]),
                current_snapshot.get(row["file_path"]),
            )
            duplicate = conn.execute(
                """
                SELECT id
                FROM semantic_conflicts
                WHERE project_id = ? AND entity_type = 'code_file'
                  AND target = ? AND field = 'business_summary'
                  AND existing = ? AND incoming = ? AND source_command = 'maintain-refresh-scope'
                  AND status = 'open'
                LIMIT 1
                """,
                (project.project_id, row["file_path"], row["business_summary"], incoming),
            ).fetchone()
            if duplicate:
                continue
            conn.execute(
                """
                INSERT INTO semantic_conflicts(
                  project_id, entity_type, target, field, existing, incoming,
                  resolution, source_command, observed_at, status
                )
                VALUES (?, 'code_file', ?, 'business_summary', ?, ?,
                        'manual_review_required', 'maintain-refresh-scope', ?, 'open')
                """,
                (project.project_id, row["file_path"], row["business_summary"], incoming, observed_at),
            )
            conflicts.append(
                {
                    "entity_type": "code_file",
                    "target": row["file_path"],
                    "field": "business_summary",
                    "existing": row["business_summary"],
                    "incoming": incoming,
                    "resolution": "manual_review_required",
                    "source_command": "maintain-refresh-scope",
                    "observed_at": observed_at,
                }
            )
        conn.commit()
    return conflicts
