# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from typing import Any

from .models import Project
from .records import output, row_dict
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .text import query_tokens, unique_list


USAGE_RECORD_TYPES = {"semantic", "reflection"}
USAGE_OUTCOMES = {"used", "helpful", "ignored", "misleading", "superseded"}
POSITIVE_USAGE_BONUSES = {
    "used": 0.06,
    "helpful": 0.18,
}
NEGATIVE_USAGE_PENALTIES = {
    "ignored": 0.10,
    "misleading": 0.35,
    "superseded": 0.30,
}


def experience_usage_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    row = write_experience_usage(
        project,
        query=args.query,
        record_type=args.type,
        record_id=args.id,
        outcome=args.outcome,
        note=args.note,
        evidence=args.evidence,
    )
    output(row, args.json)


def write_experience_usage(
    project: Project,
    query: str,
    record_type: str,
    record_id: int,
    outcome: str,
    note: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any]:
    if record_type not in USAGE_RECORD_TYPES:
        raise SystemExit("--type must be semantic or reflection")
    if outcome not in USAGE_OUTCOMES:
        raise SystemExit("--outcome must be used, helpful, ignored, misleading, or superseded")
    ts = now_iso()
    normalized = normalize_usage_query(query)
    with connect(project) as conn:
        cur = conn.execute(
            """
            INSERT INTO experience_usage_events(
              project_id, query, normalized_query, record_type, record_id,
              outcome, note, evidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                query,
                normalized,
                record_type,
                record_id,
                outcome,
                note,
                evidence,
                ts,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM experience_usage_events WHERE project_id = ? AND id = ?",
            (project.project_id, cur.lastrowid),
        ).fetchone()
    return row_dict(row)


def normalize_usage_query(query: str) -> str:
    return " ".join(query.lower().split())


def collect_usage_adjustments(project: Project, query: str, record_type: str) -> dict[int, dict[str, Any]]:
    query_terms = {token for token in query_tokens(query) if len(token) > 1}
    if not query_terms:
        return {}
    adjustments: dict[int, dict[str, Any]] = {}
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM experience_usage_events
            WHERE project_id = ?
              AND record_type = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            (project.project_id, record_type),
        ).fetchall()
    for row in rows:
        item = row_dict(row)
        overlap = usage_query_overlap(query_terms, str(item.get("query") or ""))
        if overlap <= 0:
            continue
        record_id = int(item["record_id"])
        outcome = str(item.get("outcome") or "")
        existing = adjustments.get(
            record_id,
            {"bonus": 0.0, "penalty": 0.0, "reasons": [], "usage_ids": []},
        )
        existing["bonus"] += POSITIVE_USAGE_BONUSES.get(outcome, 0.0) * overlap
        existing["penalty"] += NEGATIVE_USAGE_PENALTIES.get(outcome, 0.0) * overlap
        existing["reasons"].append(outcome)
        existing["usage_ids"].append(item.get("id"))
        adjustments[record_id] = existing
    for value in adjustments.values():
        value["bonus"] = round(min(0.18, float(value["bonus"])), 3)
        value["penalty"] = round(min(0.35, float(value["penalty"])), 3)
        value["reasons"] = unique_list([str(reason) for reason in value["reasons"]])
    return adjustments


def usage_query_overlap(query_terms: set[str], usage_query: str) -> float:
    usage_terms = {token for token in query_tokens(usage_query) if len(token) > 1}
    if not usage_terms:
        return 0.0
    return len(query_terms & usage_terms) / max(1, len(query_terms))


def apply_usage_adjustment(item: dict[str, Any], adjustments: dict[int, dict[str, Any]]) -> None:
    adjustment = adjustments.get(int(item.get("id") or 0))
    if not adjustment:
        item["usage_feedback_bonus"] = 0.0
        item["usage_feedback_penalty"] = 0.0
        return
    item["usage_feedback_bonus"] = adjustment.get("bonus", 0.0)
    item["usage_feedback_penalty"] = adjustment.get("penalty", 0.0)
    item["usage_feedback_reasons"] = adjustment.get("reasons", [])
    item["usage_feedback_ids"] = adjustment.get("usage_ids", [])


def fetch_experience_usage_summary(project: Project, limit: int = 10) -> dict[str, Any]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT record_type, record_id, outcome, COUNT(*) AS count, MAX(created_at) AS last_seen_at
            FROM experience_usage_events
            WHERE project_id = ?
            GROUP BY record_type, record_id, outcome
            ORDER BY last_seen_at DESC
            LIMIT ?
            """,
            (project.project_id, max(limit * 4, 20)),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) AS count FROM experience_usage_events WHERE project_id = ?",
            (project.project_id,),
        ).fetchone()["count"]
    grouped: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        item = row_dict(row)
        key = (str(item["record_type"]), int(item["record_id"]))
        existing = grouped.get(
            key,
            {
                "record_type": key[0],
                "record_id": key[1],
                "outcomes": {},
                "last_seen_at": item.get("last_seen_at"),
            },
        )
        existing["outcomes"][str(item["outcome"])] = int(item["count"])
        if str(item.get("last_seen_at") or "") > str(existing.get("last_seen_at") or ""):
            existing["last_seen_at"] = item.get("last_seen_at")
        grouped[key] = existing
    records = list(grouped.values())
    for record in records:
        outcomes = record["outcomes"]
        record["dominant_outcome"] = max(outcomes.items(), key=lambda pair: (pair[1], pair[0]))[0]
        record["negative_count"] = sum(outcomes.get(name, 0) for name in NEGATIVE_USAGE_PENALTIES)
        record["positive_count"] = sum(outcomes.get(name, 0) for name in POSITIVE_USAGE_BONUSES)
    records.sort(key=lambda item: (item["negative_count"], item["last_seen_at"] or ""), reverse=True)
    return {
        "event_count": int(total),
        "misleading_records": sum(1 for item in records if item["outcomes"].get("misleading", 0) > 0),
        "helpful_records": sum(1 for item in records if item["outcomes"].get("helpful", 0) > 0),
        "records": records[:limit],
    }


def build_experience_usage_actions(summary: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for record in summary.get("records") or []:
        outcomes = record.get("outcomes") or {}
        if not outcomes.get("misleading") and not outcomes.get("superseded"):
            continue
        actions.append(
            {
                "action": "review_experience_usage",
                "governance_lane": "experience_usage",
                "type": record.get("record_type"),
                "id": record.get("record_id"),
                "reason": "experience has negative usage outcomes from prior tasks",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
                "dominant_outcome": record.get("dominant_outcome"),
                "outcomes": outcomes,
                "suggested_actions": [
                    "tighten trigger or scope",
                    "lower confidence",
                    "mark stale if the current source contradicts it",
                    "record replacement guidance if a better memory exists",
                ],
            }
        )
    return actions
