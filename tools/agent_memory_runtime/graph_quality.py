# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .models import Project
from .storage import connect


LOW_CONFIDENCE_EDGE_THRESHOLD = 0.5


def build_graph_quality(project: Project) -> dict[str, Any]:
    with connect(project) as conn:
        code_files = count_table(conn, project, "code_files")
        code_symbols = count_table(conn, project, "code_symbols")
        code_logs = count_table(conn, project, "code_log_statements")
        memory_edges = count_table(conn, project, "memory_edges")
        connected_symbols = connected_count(conn, project, "code_symbol", "code_symbols")
        connected_logs = connected_count(conn, project, "code_log_statement", "code_log_statements")
        orphan_symbols = max(0, code_symbols - connected_symbols)
        orphan_logs = max(0, code_logs - connected_logs)
        stale_edges = count_stale_edges(project)
        low_confidence_edges = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM memory_edges
            WHERE project_id = ?
              AND COALESCE(confidence, 0.8) < ?
            """,
            (project.project_id, LOW_CONFIDENCE_EDGE_THRESHOLD),
        ).fetchone()["count"]

    symbol_coverage = coverage(connected_symbols, code_symbols)
    log_coverage = coverage(connected_logs, code_logs)
    return {
        "code_files": code_files,
        "code_symbols": code_symbols,
        "code_log_statements": code_logs,
        "memory_edges": memory_edges,
        "orphan_code_symbols": orphan_symbols,
        "orphan_code_logs": orphan_logs,
        "stale_edges": stale_edges,
        "low_confidence_edges": low_confidence_edges,
        "symbol_anchor_coverage": symbol_coverage,
        "log_anchor_coverage": log_coverage,
        "health_status": graph_health_status(stale_edges, orphan_symbols, orphan_logs, code_symbols, code_logs),
    }


def count_table(conn: Any, project: Project, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE project_id = ?", (project.project_id,)).fetchone()["count"])


def connected_count(conn: Any, project: Project, entity_type: str, table: str) -> int:
    rows = conn.execute(
        f"""
        SELECT COUNT(DISTINCT entity_id) AS count
        FROM (
          SELECT source_id AS entity_id
          FROM memory_edges
          WHERE project_id = ? AND source_type = ?
          UNION
          SELECT target_id AS entity_id
          FROM memory_edges
          WHERE project_id = ? AND target_type = ?
        )
        WHERE entity_id IN (
          SELECT id FROM {table} WHERE project_id = ?
        )
        """,
        (project.project_id, entity_type, project.project_id, entity_type, project.project_id),
    ).fetchone()
    return int(rows["count"] or 0)


def coverage(connected: int, total: int) -> float:
    if total == 0:
        return 1.0
    return round(connected / total, 3)


def count_stale_edges(project: Project) -> int:
    stale = 0
    for side in ("source", "target"):
        stale += count_stale_edges_for_side(project, side)
    return stale


def count_stale_edges_for_side(project: Project, side: str) -> int:
    id_column = f"{side}_id"
    type_column = f"{side}_type"
    total = 0
    with connect(project) as conn:
        for entity_type, table in (
            ("code_file", "code_files"),
            ("code_symbol", "code_symbols"),
            ("code_log_statement", "code_log_statements"),
        ):
            total += int(
                conn.execute(
                    f"""
                    SELECT COUNT(*) AS count
                    FROM memory_edges e
                    WHERE e.project_id = ?
                      AND e.{type_column} = ?
                      AND NOT EXISTS (
                        SELECT 1
                        FROM {table} t
                        WHERE t.project_id = e.project_id
                          AND t.id = e.{id_column}
                      )
                    """,
                    (project.project_id, entity_type),
                ).fetchone()["count"]
            )
    return total


def graph_health_status(stale_edges: int, orphan_symbols: int, orphan_logs: int, total_symbols: int, total_logs: int) -> str:
    if stale_edges:
        return "poor"
    if total_logs and orphan_logs / total_logs > 0.5:
        return "poor"
    if total_symbols and orphan_symbols / total_symbols > 0.5:
        return "poor"
    if orphan_symbols or orphan_logs:
        return "watch"
    return "ok"


def build_graph_quality_actions(graph_quality: dict[str, Any]) -> list[dict[str, Any]]:
    if graph_quality.get("health_status") == "ok":
        return []
    return [
        {
            "action": "review_graph_quality",
            "governance_lane": "graph_quality",
            "type": "graph_quality",
            "id": None,
            "reason": "code/log graph has orphan anchors, stale edges, or weak coverage",
            "risk": "low",
            "requires_confirmation": False,
            "command": None,
            "graph_quality": graph_quality,
            "suggested_actions": [
                "rerun_focused_learn_entry_or_learn_path",
                "review_removed_file_drift",
                "inspect_orphan_log_anchors",
                "rebuild_code_memory_edges",
            ],
        }
    ]
