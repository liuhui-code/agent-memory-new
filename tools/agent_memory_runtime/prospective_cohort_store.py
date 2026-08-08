# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from typing import Any


JSON_FIELDS = {
    "protocol_json": "protocol",
    "report_json": "report",
    "evidence_refs_json": "evidence_refs",
    "memory_manifest_json": "memory_manifest",
    "source_snapshot_json": "source_snapshot",
    "usage_metrics_json": "usage_metrics",
    "benchmark_metrics_json": "benchmark_metrics",
}


def insert_cohort(
    conn: sqlite3.Connection,
    project_id: str,
    protocol: dict[str, Any],
    protocol_digest: str,
    registered_at: str,
) -> dict[str, Any]:
    try:
        cursor = conn.execute(
            """
            INSERT INTO prospective_cohorts(
              project_id, cohort_id, protocol_json, protocol_digest, task_type,
              target_presented_tasks, status, chain_head_digest, registered_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'registered', ?, ?)
            """,
            (
                project_id,
                protocol["cohort_id"],
                encode(protocol),
                protocol_digest,
                protocol["task_type"],
                protocol["target_presented_tasks"],
                protocol_digest,
                registered_at,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise SystemExit(f"prospective cohort already exists: {protocol['cohort_id']}") from exc
    return get_cohort_by_pk(conn, int(cursor.lastrowid))


def get_cohort(
    conn: sqlite3.Connection, project_id: str, cohort_id: str,
) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM prospective_cohorts WHERE project_id = ? AND cohort_id = ?",
        (project_id, cohort_id),
    ).fetchone()
    if row is None:
        raise SystemExit(f"prospective cohort not found: {cohort_id}")
    return decode_row(row)


def get_cohort_by_pk(conn: sqlite3.Connection, cohort_pk: int) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM prospective_cohorts WHERE id = ?", (cohort_pk,)
    ).fetchone()
    if row is None:
        raise SystemExit("prospective cohort disappeared during update")
    return decode_row(row)


def list_tasks(conn: sqlite3.Connection, cohort_pk: int) -> list[dict[str, Any]]:
    return [
        decode_row(row)
        for row in conn.execute(
            "SELECT * FROM prospective_cohort_tasks WHERE cohort_pk = ? ORDER BY sequence_no",
            (cohort_pk,),
        )
    ]


def get_task(conn: sqlite3.Connection, cohort_pk: int, task_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM prospective_cohort_tasks WHERE cohort_pk = ? AND task_id = ?",
        (cohort_pk, task_id),
    ).fetchone()
    if row is None:
        raise SystemExit(f"prospective cohort task not found: {task_id}")
    return decode_row(row)


def insert_task(conn: sqlite3.Connection, value: dict[str, Any]) -> dict[str, Any]:
    columns = (
        "project_id", "cohort_pk", "sequence_no", "task_id", "task_digest",
        "eligibility", "exclusion_reason", "opportunity", "evidence_refs_json",
        "memory_available_at", "memory_manifest_json", "memory_manifest_digest",
        "source_snapshot_json", "replay_eligible", "previous_entry_digest",
        "entry_digest", "status", "usage_sample_id", "enrolled_at",
    )
    params = {
        **value,
        "evidence_refs_json": encode(value["evidence_refs"]),
        "memory_manifest_json": encode(value["memory_manifest"]),
        "source_snapshot_json": encode(value["source_snapshot"]),
    }
    placeholders = ", ".join("?" for _ in columns)
    try:
        cursor = conn.execute(
            f"INSERT INTO prospective_cohort_tasks({', '.join(columns)}) VALUES ({placeholders})",
            tuple(params[name] for name in columns),
        )
    except sqlite3.IntegrityError as exc:
        raise SystemExit(f"prospective cohort task or sequence already exists: {value['task_id']}") from exc
    row = conn.execute(
        "SELECT * FROM prospective_cohort_tasks WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return decode_row(row)


def complete_task(
    conn: sqlite3.Connection,
    task_pk: int,
    outcome: str,
    verification: str,
    usage: dict[str, Any],
    benchmark: dict[str, Any] | None,
    result_digest: str,
    completed_at: str,
) -> dict[str, Any]:
    cursor = conn.execute(
        """
        UPDATE prospective_cohort_tasks
        SET status = 'completed', outcome = ?, verification = ?, usage_metrics_json = ?,
            benchmark_metrics_json = ?, result_digest = ?, completed_at = ?
        WHERE id = ? AND status = 'active'
        """,
        (
            outcome, verification, encode(usage), encode(benchmark) if benchmark else None,
            result_digest, completed_at, task_pk,
        ),
    )
    if cursor.rowcount != 1:
        raise SystemExit("prospective cohort task is not active or was already completed")
    row = conn.execute(
        "SELECT * FROM prospective_cohort_tasks WHERE id = ?", (task_pk,)
    ).fetchone()
    return decode_row(row)


def decode_row(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    for source, target in JSON_FIELDS.items():
        if source not in value:
            continue
        raw = value.pop(source)
        value[target] = json.loads(raw) if raw else None
    if "replay_eligible" in value:
        value["replay_eligible"] = bool(value["replay_eligible"])
    return value


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
