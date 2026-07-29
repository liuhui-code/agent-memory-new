# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .models import Project
from .query_candidate_recall import fts_match_expression


LOG_EFFECT_RECALL_LIMIT = 40
SQL_CHUNK_SIZE = 400


def collect_log_effect_matches(
    conn: sqlite3.Connection,
    project: Project,
    query: str,
    limit: int = LOG_EFFECT_RECALL_LIMIT,
) -> list[dict[str, Any]]:
    expression = fts_match_expression(query)
    if not expression:
        return []
    rows = conn.execute(
        """
        SELECT effect.*
        FROM code_log_effect_fts
        JOIN code_log_effects effect ON effect.id = code_log_effect_fts.rowid
        WHERE code_log_effect_fts.project_id = ?
          AND code_log_effect_fts MATCH ?
        ORDER BY bm25(code_log_effect_fts), effect.id
        LIMIT ?
        """,
        (project.project_id, expression, limit),
    ).fetchall()
    return [normalize_effect(row) for row in rows]


def normalize_effect(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item.update({
        "kind": "log_effect",
        "raw_statement": item.get("raw_call") or "",
        "business_summary": "",
        "business_terms": "[]",
        "business_event": "",
        "trigger_stage": "",
        "symptom_terms": "[]",
        "likely_causes": "[]",
        "process_hint": "",
        "neighbor_terms": "[]",
        "recall_lanes": ["log_effect_fts"],
        "recall_fusion": {},
        "call_path": json_list(item.get("call_path")),
        "call_path_locations": json_list(item.get("call_path_locations")),
    })
    return item


def attach_log_owner_ranges(
    conn: sqlite3.Connection,
    project_id: str,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    paths = sorted({
        str(item.get("file_path") or "")
        for item in items if item.get("file_path") and item.get("function")
    })
    rows: list[sqlite3.Row] = []
    for chunk in chunks(paths):
        rows.extend(conn.execute(
            f"""
            SELECT file_path, symbol, start_line, end_line
            FROM code_symbols
            WHERE project_id = ?
              AND start_line IS NOT NULL AND end_line IS NOT NULL
              AND file_path IN ({','.join('?' for _ in chunk)})
            ORDER BY file_path, symbol, start_line, id
            """,
            (project_id, *chunk),
        ).fetchall())
    by_owner: dict[tuple[str, str], list[sqlite3.Row]] = {}
    for row in rows:
        by_owner.setdefault((str(row["file_path"]), str(row["symbol"])), []).append(row)
    for item in items:
        candidates = by_owner.get((
            str(item.get("file_path") or ""), str(item.get("function") or ""),
        ), [])
        line = int(item.get("line") or 0)
        containing = [
            row for row in candidates
            if int(row["start_line"]) <= line <= int(row["end_line"])
        ]
        selected = min(containing or candidates, key=range_width, default=None)
        if selected is not None:
            item["start_line"] = int(selected["start_line"])
            item["end_line"] = int(selected["end_line"])
    return items


def range_width(row: sqlite3.Row) -> tuple[int, int]:
    return int(row["end_line"]) - int(row["start_line"]), int(row["start_line"])


def chunks(values: list[str]) -> list[list[str]]:
    return [values[index:index + SQL_CHUNK_SIZE] for index in range(0, len(values), SQL_CHUNK_SIZE)]


def json_list(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []
