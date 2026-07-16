# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Any

from .feedback_policy import derived_event_key, stable_signal
from .models import Project
from .records import output, row_dict
from .retrieval_feedback import validate_record_reference
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .text import query_tokens, unique_list


USAGE_RECORD_TYPES = {"semantic", "reflection"}
USAGE_OUTCOMES = {"used", "helpful", "ignored", "misleading", "superseded"}
POSITIVE_USAGE_BONUSES = {"helpful": 0.18}
NEGATIVE_USAGE_PENALTIES = {"misleading": 0.35}
RANKING_USAGE_OUTCOMES = set(POSITIVE_USAGE_BONUSES) | set(NEGATIVE_USAGE_PENALTIES)


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
        task_id=args.task_id,
        query_id=args.query_id,
        event_key=args.event_key,
        verified=bool(args.verified),
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
    task_id: str | None = None,
    query_id: str | None = None,
    event_key: str | None = None,
    verified: bool = False,
) -> dict[str, Any]:
    if record_type not in USAGE_RECORD_TYPES:
        raise SystemExit("--type must be semantic or reflection")
    if outcome not in USAGE_OUTCOMES:
        raise SystemExit("--outcome must be used, helpful, ignored, misleading, or superseded")
    normalized = normalize_usage_query(query)
    if not normalized:
        raise SystemExit("query must not be empty")
    key = str(event_key or "").strip() or derived_event_key(
        "experience-usage", task_id, [record_type, record_id, outcome, normalized]
    )
    with connect(project) as conn:
        validate_record_reference(conn, project, record_type, record_id)
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO experience_usage_events(
              project_id, query, normalized_query, record_type, record_id,
              outcome, note, evidence, task_id, query_id, event_key, verified, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id, query, normalized, record_type, record_id,
                outcome, note, evidence, task_id, query_id, key, int(verified), now_iso(),
            ),
        )
        conn.commit()
        if cur.rowcount == 1:
            row = conn.execute(
                "SELECT * FROM experience_usage_events WHERE project_id = ? AND id = ?",
                (project.project_id, cur.lastrowid),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM experience_usage_events WHERE project_id = ? AND event_key = ?",
                (project.project_id, key),
            ).fetchone()
    return row_dict(row)


def normalize_usage_query(query: str) -> str:
    return " ".join(query.lower().split())


def collect_usage_adjustments(project: Project, query: str, record_type: str) -> dict[int, dict[str, Any]]:
    return collect_usage_adjustments_by_type(project, query, (record_type,))[record_type]


def collect_usage_adjustments_by_type(
    project: Project,
    query: str,
    record_types: tuple[str, ...] = ("semantic", "reflection"),
    record_ids: dict[str, set[int]] | None = None,
) -> dict[str, dict[int, dict[str, Any]]]:
    query_terms = {token for token in query_tokens(query) if len(token) > 1}
    selected_types = tuple(record_type for record_type in record_types if record_type in USAGE_RECORD_TYPES)
    adjustments: dict[str, dict[int, dict[str, Any]]] = {record_type: {} for record_type in selected_types}
    if not query_terms or not selected_types:
        return adjustments
    rows = fetch_candidate_usage(project, selected_types, record_ids)
    groups: dict[tuple[str, int, str], list[tuple[dict[str, Any], float]]] = defaultdict(list)
    for item in rows:
        outcome = str(item.get("outcome") or "")
        if outcome not in RANKING_USAGE_OUTCOMES:
            continue
        overlap = usage_query_overlap(query_terms, str(item.get("query") or ""))
        if overlap > 0:
            groups[(str(item["record_type"]), int(item["record_id"]), outcome)].append((item, overlap))
    for (record_type, record_id, outcome), values in groups.items():
        items = [item for item, _ in values]
        if not stable_signal(items):
            continue
        overlap = max(value for _, value in values)
        existing = adjustments[record_type].get(
            record_id,
            {"bonus": 0.0, "penalty": 0.0, "reasons": [], "usage_ids": []},
        )
        existing["bonus"] += POSITIVE_USAGE_BONUSES.get(outcome, 0.0) * overlap
        existing["penalty"] += NEGATIVE_USAGE_PENALTIES.get(outcome, 0.0) * overlap
        existing["reasons"].append(outcome)
        existing["usage_ids"].extend(item.get("id") for item in items)
        adjustments[record_type][record_id] = existing
    for typed_adjustments in adjustments.values():
        for value in typed_adjustments.values():
            value["bonus"] = round(min(0.18, float(value["bonus"])), 3)
            value["penalty"] = round(min(0.35, float(value["penalty"])), 3)
            value["reasons"] = unique_list([str(reason) for reason in value["reasons"]])
    return adjustments


def fetch_candidate_usage(
    project: Project,
    record_types: tuple[str, ...],
    record_ids: dict[str, set[int]] | None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = [project.project_id]
    for record_type in record_types:
        ids = sorted((record_ids or {}).get(record_type, set())) if record_ids is not None else []
        if record_ids is not None and not ids:
            continue
        if ids:
            marks = ",".join("?" for _ in ids)
            clauses.append(f"(record_type = ? AND record_id IN ({marks}))")
            values.extend([record_type, *ids])
        else:
            clauses.append("record_type = ?")
            values.append(record_type)
    if not clauses:
        return []
    limit = "" if record_ids is not None else "LIMIT 2000"
    with connect(project) as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM experience_usage_events
            WHERE project_id = ? AND ({' OR '.join(clauses)})
            ORDER BY created_at DESC, id DESC {limit}
            """,
            values,
        ).fetchall()
    return [row_dict(row) for row in rows]


def usage_query_overlap(query_terms: set[str], usage_query: str) -> float:
    usage_terms = {token for token in query_tokens(usage_query) if len(token) > 1}
    if not usage_terms:
        return 0.0
    return len(query_terms & usage_terms) / max(1, len(query_terms | usage_terms))


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
    scan_limit = 5000
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM experience_usage_events
            WHERE project_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (project.project_id, scan_limit),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) AS count FROM experience_usage_events WHERE project_id = ?",
            (project.project_id,),
        ).fetchone()["count"]
    grouped: dict[tuple[str, int], dict[str, Any]] = {}
    signal_groups: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
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
        outcome = str(item["outcome"])
        existing["outcomes"][outcome] = int(existing["outcomes"].get(outcome, 0)) + 1
        if str(item.get("created_at") or "") > str(existing.get("last_seen_at") or ""):
            existing["last_seen_at"] = item.get("created_at")
        grouped[key] = existing
        signal_groups[(key[0], key[1], outcome)].append(item)
    records = list(grouped.values())
    for record in records:
        outcomes = record["outcomes"]
        record["stable_outcomes"] = [
            outcome
            for outcome in outcomes
            if stable_signal(signal_groups[(record["record_type"], record["record_id"], outcome)])
        ]
        record["dominant_outcome"] = max(outcomes.items(), key=lambda pair: (pair[1], pair[0]))[0]
        record["negative_count"] = sum(outcomes.get(name, 0) for name in NEGATIVE_USAGE_PENALTIES)
        record["positive_count"] = sum(outcomes.get(name, 0) for name in POSITIVE_USAGE_BONUSES)
        record.update(effectiveness_metrics(outcomes))
    records.sort(key=lambda item: (item["negative_count"], item["last_seen_at"] or ""), reverse=True)
    return {
        "event_count": int(total),
        "misleading_records": sum(1 for item in records if item["outcomes"].get("misleading", 0) > 0),
        "helpful_records": sum(1 for item in records if item["outcomes"].get("helpful", 0) > 0),
        "stable_signal_count": sum(len(item["stable_outcomes"]) for item in records),
        "pending_signal_count": sum(len(item["outcomes"]) - len(item["stable_outcomes"]) for item in records),
        "truncated": int(total) > scan_limit,
        "records": records[:limit],
    }


def build_experience_usage_actions(summary: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for record in summary.get("records") or []:
        outcomes = record.get("outcomes") or {}
        stable_outcomes = set(record.get("stable_outcomes") or [])
        if not ({"misleading", "superseded"} & stable_outcomes):
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
                "effectiveness": {
                    "total_count": record.get("total_count"),
                    "success_count": record.get("success_count"),
                    "failure_count": record.get("failure_count"),
                    "success_rate": record.get("success_rate"),
                    "misleading_rate": record.get("misleading_rate"),
                    "effectiveness_band": record.get("effectiveness_band"),
                },
                "suggested_actions": [
                    "tighten trigger or scope",
                    "lower confidence",
                    "mark stale if the current source contradicts it",
                    "record replacement guidance if a better memory exists",
                ],
            }
        )
    return actions


def effectiveness_metrics(outcomes: dict[str, int]) -> dict[str, Any]:
    total = sum(int(value or 0) for value in outcomes.values())
    success = sum(int(outcomes.get(name, 0) or 0) for name in POSITIVE_USAGE_BONUSES)
    failure = sum(int(outcomes.get(name, 0) or 0) for name in NEGATIVE_USAGE_PENALTIES)
    success_rate = round(success / total, 3) if total else 0.0
    misleading_rate = round(int(outcomes.get("misleading", 0) or 0) / total, 3) if total else 0.0
    if failure and success:
        band = "mixed"
    elif success_rate >= 0.67:
        band = "strong"
    elif failure:
        band = "weak"
    else:
        band = "unknown"
    return {
        "total_count": total,
        "success_count": success,
        "failure_count": failure,
        "success_rate": success_rate,
        "misleading_rate": misleading_rate,
        "effectiveness_band": band,
    }
