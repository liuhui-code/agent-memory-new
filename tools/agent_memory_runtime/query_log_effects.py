# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .models import Project
from .query_candidate_recall import fts_match_expression


LOG_EFFECT_RECALL_LIMIT = 40


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


def json_list(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []
