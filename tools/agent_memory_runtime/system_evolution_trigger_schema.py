# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .system_evolution_contract import require


COMPONENT = "system_evolution_triggers"
VERSION = "system-triggers-v1"
POLICY = "system-meta-trigger-policy/v1"
TABLE = "system_meta_review_triggers"


def triggers_available(conn: sqlite3.Connection) -> bool:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    version = None
    if "runtime_schema_versions" in tables:
        version = conn.execute("SELECT version FROM runtime_schema_versions WHERE component=?", (COMPONENT,)).fetchone()
    if TABLE not in tables:
        require(version is None, "Trigger version exists without its table.", "schema_incomplete")
        return False
    require(version is not None and version[0] == VERSION, "Unsupported trigger schema version.", "schema_version_unsupported")
    return True


def create_triggers(conn: sqlite3.Connection) -> None:
    if triggers_available(conn):
        return
    conn.execute("CREATE TABLE IF NOT EXISTS runtime_schema_versions(component TEXT PRIMARY KEY, version TEXT NOT NULL)")
    conn.execute("""CREATE TABLE system_meta_review_triggers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
        task_origin TEXT NOT NULL, task_key TEXT NOT NULL, review_key TEXT NOT NULL,
        "trigger" TEXT NOT NULL, policy_version TEXT NOT NULL, request_digest TEXT NOT NULL,
        request_json TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('reserved','recorded')),
        review_id INTEGER, review_revision INTEGER, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(project_id, task_origin, task_key), UNIQUE(project_id, review_key))""")
    conn.execute("INSERT INTO runtime_schema_versions(component, version) VALUES (?, ?)", (COMPONENT, VERSION))


def trigger_view(row: sqlite3.Row, full: bool = False) -> dict[str, Any]:
    value = {key: row[key] for key in ("id", "task_origin", "task_key", "review_key", "trigger",
             "policy_version", "request_digest", "state", "review_id", "review_revision", "created_at", "updated_at")}
    if full:
        value["request"] = json.loads(row["request_json"])
    value.update(slot_allocated=True, model_execution_observed=False, evidence_verified=False)
    return value


def task_claim(conn: sqlite3.Connection, project_id: str, task: dict[str, str] | None) -> sqlite3.Row | None:
    if task is None or not triggers_available(conn):
        return None
    return conn.execute("SELECT * FROM system_meta_review_triggers WHERE project_id=? AND task_origin=? AND task_key=?",
                        (project_id, task["origin"], task["key"])).fetchone()


def require_claim_binding(conn: sqlite3.Connection, project_id: str, review_key: str, report: dict[str, Any]) -> None:
    if not triggers_available(conn):
        return
    by_key = conn.execute("SELECT * FROM system_meta_review_triggers WHERE project_id=? AND review_key=?",
                          (project_id, review_key)).fetchone()
    claim = task_claim(conn, project_id, report["task_ref"])
    require(by_key is None or (claim is not None and by_key["id"] == claim["id"]),
            "Claimed review key cannot change task identity.", "trigger_claim_conflict")
    if claim is not None:
        require(claim["review_key"] == review_key, "Use the claimed task's existing review key.", "trigger_claim_conflict")
        require(report["trigger"] == "manual" or (report["trigger"] == claim["trigger"] and claim["state"] == "reserved"),
                "Automatic report needs its unused allocated slot; explicit revisions use manual trigger.", "trigger_claim_conflict")


def record_claim_report(conn: sqlite3.Connection, project_id: str, report: dict[str, Any], review_id: int, timestamp: str) -> None:
    claim = task_claim(conn, project_id, report["task_ref"])
    if claim is not None:
        conn.execute("""UPDATE system_meta_review_triggers SET state='recorded', review_id=?,
            review_revision=?, updated_at=? WHERE id=? AND (review_revision IS NULL OR review_revision < ?)""",
            (review_id, report["review_revision"], timestamp, claim["id"], report["review_revision"]))


def trigger_history(conn: sqlite3.Connection, project_id: str, limit: int) -> dict[str, Any]:
    if not triggers_available(conn):
        return {"trigger_claims": [], "trigger_claims_truncated": False}
    rows = conn.execute("SELECT * FROM system_meta_review_triggers WHERE project_id=? ORDER BY id DESC LIMIT ?",
                        (project_id, limit + 1)).fetchall()
    return {"trigger_claims": [trigger_view(row) for row in rows[:limit]], "trigger_claims_truncated": len(rows) > limit}
