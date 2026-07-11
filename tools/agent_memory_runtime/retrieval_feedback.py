# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from typing import Any

from .models import Project
from .records import output, row_dict
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .text import query_tokens


FEEDBACK_REASONS = {"weak_related", "stale", "wrong_domain", "too_broad", "misleading"}
FEEDBACK_RECORD_TYPES = {"semantic", "reflection"}
FEEDBACK_PENALTIES = {
    "weak_related": 18.0,
    "stale": 24.0,
    "wrong_domain": 24.0,
    "too_broad": 16.0,
    "misleading": 30.0,
}


def retrieval_feedback_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    if args.type not in FEEDBACK_RECORD_TYPES:
        raise SystemExit("--type must be semantic or reflection")
    if args.reason not in FEEDBACK_REASONS:
        raise SystemExit("--reason must be weak_related, stale, wrong_domain, too_broad, or misleading")
    row = write_retrieval_feedback(
        project,
        query=args.query,
        record_type=args.type,
        record_id=args.id,
        reason=args.reason,
        replacement_type=args.replacement_type,
        replacement_id=args.replacement_id,
        note=args.note,
    )
    output(row, args.json)


def write_retrieval_feedback(
    project: Project,
    query: str,
    record_type: str,
    record_id: int,
    reason: str,
    replacement_type: str | None = None,
    replacement_id: int | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    ts = now_iso()
    normalized = normalize_feedback_query(query)
    with connect(project) as conn:
        cur = conn.execute(
            """
            INSERT INTO retrieval_feedback(
              project_id, query, normalized_query, record_type, record_id, reason,
              replacement_type, replacement_id, note, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
            """,
            (
                project.project_id,
                query,
                normalized,
                record_type,
                record_id,
                reason,
                replacement_type,
                replacement_id,
                note,
                ts,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM retrieval_feedback WHERE project_id = ? AND id = ?",
            (project.project_id, cur.lastrowid),
        ).fetchone()
    return row_dict(row)


def normalize_feedback_query(query: str) -> str:
    return " ".join(query.lower().split())


def collect_feedback_penalties(project: Project, query: str, record_type: str) -> dict[int, dict[str, Any]]:
    query_terms = {token for token in query_tokens(query) if len(token) > 1}
    if not query_terms:
        return {}
    penalties: dict[int, dict[str, Any]] = {}
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM retrieval_feedback
            WHERE project_id = ?
              AND record_type = ?
              AND status = 'open'
            ORDER BY created_at DESC, id DESC
            LIMIT 100
            """,
            (project.project_id, record_type),
        ).fetchall()
    for row in rows:
        item = row_dict(row)
        overlap = feedback_query_overlap(query_terms, str(item.get("query") or ""))
        if overlap <= 0:
            continue
        record_id = int(item["record_id"])
        penalty = FEEDBACK_PENALTIES.get(str(item.get("reason")), 12.0) * overlap
        existing = penalties.get(record_id, {"penalty": 0.0, "reasons": [], "feedback_ids": []})
        existing["penalty"] += penalty
        existing["reasons"].append(item.get("reason"))
        existing["feedback_ids"].append(item.get("id"))
        penalties[record_id] = existing
    for value in penalties.values():
        value["penalty"] = round(min(40.0, float(value["penalty"])), 3)
    return penalties


def feedback_query_overlap(query_terms: set[str], feedback_query: str) -> float:
    feedback_terms = {token for token in query_tokens(feedback_query) if len(token) > 1}
    if not feedback_terms:
        return 0.0
    return len(query_terms & feedback_terms) / max(1, len(query_terms))


def fetch_open_retrieval_feedback(project: Project, limit: int = 20) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM retrieval_feedback
            WHERE project_id = ?
              AND status = 'open'
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
    return [row_dict(row) for row in rows]
