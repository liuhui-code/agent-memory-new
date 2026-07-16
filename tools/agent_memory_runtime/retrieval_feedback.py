# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Any

from .feedback_policy import derived_event_key, stable_signal
from .models import Project
from .records import output, row_dict
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .text import query_tokens, unique_list


NEGATIVE_FEEDBACK_REASONS = {"weak_related", "stale", "wrong_domain", "too_broad", "misleading"}
POSITIVE_CALIBRATION_REASONS = {"useful", "verified_useful", "undertrusted"}
NEGATIVE_CALIBRATION_REASONS = {"overtrusted"}
FEEDBACK_REASONS = NEGATIVE_FEEDBACK_REASONS | POSITIVE_CALIBRATION_REASONS | NEGATIVE_CALIBRATION_REASONS
FEEDBACK_RECORD_TYPES = {"semantic", "reflection"}
FEEDBACK_STATUSES = {"open", "confirmed", "resolved", "ignored"}
ACTIVE_FEEDBACK_STATUSES = {"open", "confirmed"}
FEEDBACK_PENALTIES = {
    "weak_related": 18.0, "stale": 24.0, "wrong_domain": 24.0,
    "too_broad": 16.0, "misleading": 30.0, "overtrusted": 18.0,
}
CALIBRATION_BONUSES = {"useful": 0.08, "verified_useful": 0.16, "undertrusted": 0.12}
CALIBRATION_PENALTIES = {"overtrusted": 0.18}
RECORD_TABLES = {"semantic": "semantic_facts", "reflection": "reflections"}


def retrieval_feedback_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    if args.feedback_id is not None:
        if not args.status:
            raise SystemExit("--status is required with --feedback-id")
        row = set_retrieval_feedback_status(project, args.feedback_id, args.status, args.note)
    else:
        require_feedback_write_args(args)
        row = write_retrieval_feedback(
            project,
            query=args.query,
            record_type=args.type,
            record_id=args.id,
            reason=args.reason,
            replacement_type=args.replacement_type,
            replacement_id=args.replacement_id,
            note=args.note,
            task_id=args.task_id,
            query_id=args.query_id,
            event_key=args.event_key,
            verified=bool(args.verified),
        )
    output(row, args.json)


def require_feedback_write_args(args: argparse.Namespace) -> None:
    missing = [name for name in ("query", "type", "id", "reason") if getattr(args, name) in (None, "")]
    if missing:
        raise SystemExit("feedback write requires --query, --type, --id, and --reason")


def write_retrieval_feedback(
    project: Project,
    query: str,
    record_type: str,
    record_id: int,
    reason: str,
    replacement_type: str | None = None,
    replacement_id: int | None = None,
    note: str | None = None,
    task_id: str | None = None,
    query_id: str | None = None,
    event_key: str | None = None,
    verified: bool = False,
) -> dict[str, Any]:
    validate_feedback_values(record_type, reason)
    normalized = normalize_feedback_query(query)
    if not normalized:
        raise SystemExit("query must not be empty")
    intrinsic = reason == "verified_useful"
    is_verified = verified or intrinsic
    status = "confirmed" if is_verified else "open"
    key = str(event_key or "").strip() or derived_event_key(
        "retrieval-feedback",
        task_id,
        [record_type, record_id, reason, normalized, replacement_type, replacement_id],
    )
    with connect(project) as conn:
        validate_record_reference(conn, project, record_type, record_id)
        if replacement_type and replacement_id is not None:
            validate_record_reference(conn, project, replacement_type, replacement_id)
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO retrieval_feedback(
              project_id, query, normalized_query, record_type, record_id, reason,
              replacement_type, replacement_id, note, status, task_id, query_id,
              event_key, verified, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id, query, normalized, record_type, record_id, reason,
                replacement_type, replacement_id, note, status, task_id, query_id,
                key, int(is_verified), now_iso(),
            ),
        )
        conn.commit()
        if cursor.rowcount == 1:
            row = conn.execute(
                "SELECT * FROM retrieval_feedback WHERE project_id = ? AND id = ?",
                (project.project_id, cursor.lastrowid),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM retrieval_feedback WHERE project_id = ? AND event_key = ?",
                (project.project_id, key),
            ).fetchone()
    return row_dict(row)


def set_retrieval_feedback_status(
    project: Project,
    feedback_id: int,
    status: str,
    resolution: str | None,
) -> dict[str, Any]:
    if status not in FEEDBACK_STATUSES:
        raise SystemExit(f"unsupported feedback status: {status}")
    reviewed_at = now_iso() if status != "open" else None
    with connect(project) as conn:
        cursor = conn.execute(
            """
            UPDATE retrieval_feedback
            SET status = ?, verified = CASE WHEN ? = 'confirmed' THEN 1 ELSE verified END,
                resolution = ?, reviewed_at = ?
            WHERE project_id = ? AND id = ?
            """,
            (status, status, resolution, reviewed_at, project.project_id, feedback_id),
        )
        if cursor.rowcount != 1:
            raise SystemExit(f"retrieval feedback not found: {feedback_id}")
        conn.commit()
        row = conn.execute(
            "SELECT * FROM retrieval_feedback WHERE project_id = ? AND id = ?",
            (project.project_id, feedback_id),
        ).fetchone()
    return row_dict(row)


def validate_feedback_values(record_type: str, reason: str) -> None:
    if record_type not in FEEDBACK_RECORD_TYPES:
        raise SystemExit("--type must be semantic or reflection")
    if reason not in FEEDBACK_REASONS:
        raise SystemExit(f"unsupported feedback reason: {reason}")


def validate_record_reference(conn: Any, project: Project, record_type: str, record_id: int) -> None:
    table = RECORD_TABLES.get(record_type)
    if not table:
        raise SystemExit(f"unsupported record type: {record_type}")
    row = conn.execute(
        f"SELECT id FROM {table} WHERE project_id = ? AND id = ?",
        (project.project_id, record_id),
    ).fetchone()
    if not row:
        raise SystemExit(f"{record_type} record not found: {record_id}")


def normalize_feedback_query(query: str) -> str:
    return " ".join(query.lower().split())


def collect_feedback_penalties(project: Project, query: str, record_type: str) -> dict[int, dict[str, Any]]:
    penalties, _ = collect_feedback_adjustments(project, query, (record_type,))
    return penalties[record_type]


def collect_feedback_adjustments(
    project: Project,
    query: str,
    record_types: tuple[str, ...] = ("semantic", "reflection"),
    record_ids: dict[str, set[int]] | None = None,
) -> tuple[dict[str, dict[int, dict[str, Any]]], dict[str, dict[int, dict[str, Any]]]]:
    query_terms = {token for token in query_tokens(query) if len(token) > 1}
    selected = tuple(item for item in record_types if item in FEEDBACK_RECORD_TYPES)
    penalties = {item: {} for item in selected}
    calibration = {item: {} for item in selected}
    if not query_terms or not selected:
        return penalties, calibration
    rows = fetch_active_feedback(project, selected, record_ids)
    groups: dict[tuple[str, int, str], list[tuple[dict[str, Any], float]]] = defaultdict(list)
    for item in rows:
        overlap = feedback_query_overlap(query_terms, str(item.get("query") or ""))
        if overlap > 0:
            key = (str(item["record_type"]), int(item["record_id"]), str(item["reason"]))
            groups[key].append((item, overlap))
    for (record_type, record_id, reason), values in groups.items():
        items = [item for item, _ in values]
        if not stable_signal(items, intrinsic=reason == "verified_useful"):
            continue
        overlap = max(value for _, value in values)
        ids = [item.get("id") for item in items]
        add_feedback_adjustment(penalties[record_type], record_id, reason, overlap, ids)
        add_calibration_adjustment(calibration[record_type], record_id, reason, overlap, ids)
    finalize_feedback_adjustments(penalties, calibration)
    return penalties, calibration


def fetch_active_feedback(
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
            SELECT * FROM retrieval_feedback
            WHERE project_id = ? AND status IN ('open', 'confirmed')
              AND ({' OR '.join(clauses)})
            ORDER BY created_at DESC, id DESC {limit}
            """,
            values,
        ).fetchall()
    return [row_dict(row) for row in rows]


def add_feedback_adjustment(
    target: dict[int, dict[str, Any]], record_id: int, reason: str, overlap: float, ids: list[Any]
) -> None:
    penalty = 0.0 if reason in POSITIVE_CALIBRATION_REASONS else FEEDBACK_PENALTIES.get(reason, 12.0) * overlap
    item = target.setdefault(record_id, {"penalty": 0.0, "reasons": [], "feedback_ids": []})
    item["penalty"] += penalty
    item["reasons"].append(reason)
    item["feedback_ids"].extend(ids)


def add_calibration_adjustment(
    target: dict[int, dict[str, Any]], record_id: int, reason: str, overlap: float, ids: list[Any]
) -> None:
    if reason not in FEEDBACK_REASONS:
        return
    item = target.setdefault(
        record_id, {"bonus": 0.0, "penalty": 0.0, "reasons": [], "feedback_ids": []}
    )
    item["bonus"] += CALIBRATION_BONUSES.get(reason, 0.0) * overlap
    item["penalty"] += CALIBRATION_PENALTIES.get(reason, 0.0) * overlap
    item["reasons"].append(reason)
    item["feedback_ids"].extend(ids)


def finalize_feedback_adjustments(
    penalties: dict[str, dict[int, dict[str, Any]]],
    calibration: dict[str, dict[int, dict[str, Any]]],
) -> None:
    for values in penalties.values():
        for item in values.values():
            item["penalty"] = round(min(40.0, float(item["penalty"])), 3)
            item["reasons"] = unique_list(item["reasons"])
    for values in calibration.values():
        for item in values.values():
            item["bonus"] = round(min(0.3, float(item["bonus"])), 3)
            item["penalty"] = round(min(0.3, float(item["penalty"])), 3)


def collect_calibration_feedback(project: Project, query: str, record_type: str) -> dict[int, dict[str, Any]]:
    _, calibration = collect_feedback_adjustments(project, query, (record_type,))
    return calibration[record_type]


def feedback_query_overlap(query_terms: set[str], feedback_query: str) -> float:
    feedback_terms = {token for token in query_tokens(feedback_query) if len(token) > 1}
    if not feedback_terms:
        return 0.0
    intersection = len(query_terms & feedback_terms)
    return intersection / max(1, len(query_terms | feedback_terms))


def fetch_open_retrieval_feedback(project: Project, limit: int = 20) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT * FROM retrieval_feedback
            WHERE project_id = ? AND status IN ('open', 'confirmed')
            ORDER BY created_at DESC, id DESC LIMIT ?
            """,
            (project.project_id, max(limit * 5, 100)),
        ).fetchall()
    items = [row_dict(row) for row in rows]
    groups: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        groups[(str(item["record_type"]), int(item["record_id"]), str(item["reason"]))].append(item)
    representatives: list[dict[str, Any]] = []
    for group in groups.values():
        item = dict(group[0])
        item["signal_stable"] = stable_signal(group, intrinsic=item["reason"] == "verified_useful")
        item["independent_observations"] = len({str(row.get("task_id") or row["id"]) for row in group})
        item["supporting_feedback_ids"] = [row["id"] for row in group]
        representatives.append(item)
    representatives.sort(key=lambda item: int(item["id"]), reverse=True)
    return representatives[:limit]


def retrieval_feedback_summary(project: Project, limit: int = 5000) -> dict[str, Any]:
    with connect(project) as conn:
        total = int(conn.execute(
            """
            SELECT COUNT(*) AS count FROM retrieval_feedback
            WHERE project_id = ? AND status IN ('open', 'confirmed')
            """,
            (project.project_id,),
        ).fetchone()["count"])
        rows = conn.execute(
            """
            SELECT * FROM retrieval_feedback
            WHERE project_id = ? AND status IN ('open', 'confirmed')
            ORDER BY id DESC LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
    groups: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        item = row_dict(row)
        groups[(str(item["record_type"]), int(item["record_id"]), str(item["reason"]))].append(item)
    stable_count = sum(
        stable_signal(group, intrinsic=group[0]["reason"] == "verified_useful")
        for group in groups.values()
    )
    return {
        "active_event_count": total,
        "group_count": len(groups),
        "stable_signal_count": stable_count,
        "pending_signal_count": len(groups) - stable_count,
        "truncated": total > limit,
        "policy": {
            "verified_event_is_stable": True,
            "independent_task_threshold": 2,
            "single_unverified_event_changes_ranking": False,
        },
    }
