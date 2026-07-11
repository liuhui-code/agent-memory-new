# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .log_signal_quality import score_log_signal
from .models import Project
from .storage import connect
from .text import json_list


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


def build_graph_signal_quality(project: Project, limit: int = 10) -> dict[str, Any]:
    graph = build_graph_quality(project)
    with connect(project) as conn:
        symbol_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, file_path, symbol, summary, business_summary, business_terms
                FROM code_symbols
                WHERE project_id = ?
                ORDER BY id
                LIMIT ?
                """,
                (project.project_id, limit * 3),
            ).fetchall()
        ]
        log_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, file_path, line, function, level, logger, message_template,
                       raw_statement, business_summary, business_terms, business_event,
                       trigger_stage, symptom_terms, likely_causes, process_hint, neighbor_terms
                FROM code_log_statements
                WHERE project_id = ?
                ORDER BY id
                LIMIT ?
                """,
                (project.project_id, limit * 3),
            ).fetchall()
        ]

    targets: list[dict[str, Any]] = []
    missing_business = 0
    missing_log_signal_fields = 0

    for row in log_rows:
        signal = score_log_signal(row)
        if not has_business_semantics(row):
            missing_business += 1
        if signal["log_signal_band"] != "good":
            missing_log_signal_fields += len(signal["missing_signals"])
            targets.append(
                {
                    "target_type": "code_log_statement",
                    "target_id": row["id"],
                    "file_path": row.get("file_path"),
                    "function_name": row.get("function"),
                    "message_template": row.get("message_template"),
                    "reason": "log statement has weak diagnostic signal",
                    "log_signal_score": signal["log_signal_score"],
                    "missing_signals": signal["missing_signals"],
                    "suggested_fields": signal["suggested_log_fields"],
                }
            )

    for row in symbol_rows:
        if has_business_semantics(row):
            continue
        missing_business += 1
        targets.append(
            {
                "target_type": "code_symbol",
                "target_id": row["id"],
                "file_path": row.get("file_path"),
                "function_name": row.get("symbol"),
                "reason": "symbol lacks business summary or business terms",
                "suggested_fields": ["business_summary", "business_terms"],
            }
        )

    weak_anchor_count = int(graph.get("orphan_code_symbols") or 0) + int(graph.get("orphan_code_logs") or 0)
    weak_anchor_count += len([target for target in targets if target["target_type"] == "code_log_statement"])
    targets.sort(key=lambda item: (0 if item["target_type"] == "code_log_statement" else 1, item.get("target_id") or 0))
    return {
        "weak_anchor_count": weak_anchor_count,
        "missing_business_semantics": missing_business,
        "missing_log_signal_fields": missing_log_signal_fields,
        "top_repair_targets": targets[:limit],
        "health_status": graph_signal_health_status(weak_anchor_count, missing_business, missing_log_signal_fields),
    }


def build_graph_signal_quality_actions(graph_signal_quality: dict[str, Any]) -> list[dict[str, Any]]:
    if graph_signal_quality.get("health_status") == "ok" or not graph_signal_quality.get("top_repair_targets"):
        return []
    return [
        {
            "action": "review_graph_signal_quality",
            "governance_lane": "graph_quality",
            "type": "graph_signal_quality",
            "id": None,
            "reason": "code/log graph has weak diagnostic anchors or missing business/log signal fields",
            "risk": "low",
            "requires_confirmation": False,
            "command": None,
            "graph_signal_quality": graph_signal_quality,
            "suggested_actions": [
                "enrich_business_semantics",
                "add_request_or_session_correlation_to_logs",
                "add_route_resource_reason_or_result_fields",
                "rerun_focused_learn_business",
            ],
        }
    ]


def graph_signal_health_status(weak_anchor_count: int, missing_business: int, missing_log_signal_fields: int) -> str:
    if weak_anchor_count == 0 and missing_business == 0 and missing_log_signal_fields == 0:
        return "ok"
    if weak_anchor_count > 5 or missing_log_signal_fields > 20:
        return "poor"
    return "watch"


def has_business_semantics(row: dict[str, Any]) -> bool:
    return bool(str(row.get("business_summary") or "").strip() or json_list(row.get("business_terms")))
