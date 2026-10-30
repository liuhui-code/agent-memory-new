# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .system_evolution_contract import require
from .system_evolution_schema import registry_available


COMPONENT = "system_evolution_checks"
VERSION = "system-checks-v1"
TABLE = "system_change_check_runs"


def checks_available(conn: sqlite3.Connection) -> bool:
    table = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone()
    version = conn.execute("SELECT version FROM runtime_schema_versions WHERE component=?", (COMPONENT,)).fetchone()
    if table is None:
        require(version is None, "Check-run metadata exists without its table.", "schema_incomplete")
        return False
    require(version is not None and version[0] == VERSION,
            "Unsupported check-run schema version.", "schema_version_unsupported")
    return True


def create_checks(conn: sqlite3.Connection) -> None:
    require(registry_available(conn), "System governance registry is required.", "not_found")
    if checks_available(conn):
        return
    conn.execute("""CREATE TABLE system_change_check_runs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
        proposal_id INTEGER NOT NULL REFERENCES system_change_proposals(id),
        run_key TEXT NOT NULL, prepared_state_revision INTEGER NOT NULL,
        artifact_digest TEXT NOT NULL, plan_digest TEXT NOT NULL, plan_summary_json TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('running','completed','interrupted')),
        receipt_json TEXT, created_at TEXT NOT NULL, completed_at TEXT,
        UNIQUE(project_id, run_key))""")
    conn.execute("""CREATE UNIQUE INDEX idx_system_check_active
        ON system_change_check_runs(project_id, proposal_id) WHERE state='running'""")
    conn.execute("INSERT INTO runtime_schema_versions(component, version) VALUES (?, ?)", (COMPONENT, VERSION))


def active_check(conn: sqlite3.Connection, project_id: str, proposal_id: int) -> bool:
    if not checks_available(conn):
        return False
    return conn.execute("""SELECT 1 FROM system_change_check_runs
        WHERE project_id=? AND proposal_id=? AND state='running' LIMIT 1""",
        (project_id, proposal_id)).fetchone() is not None


def check_run_view(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    value["plan_summary"] = json.loads(value.pop("plan_summary_json"))
    raw = value.pop("receipt_json")
    value["receipt"] = json.loads(raw) if raw else None
    value.update(evidence_verified=False, promotion_eligible=False, application_performed=False)
    return value


def check_history(conn: sqlite3.Connection, project_id: str, proposal_id: int, limit: int) -> dict[str, Any]:
    if not checks_available(conn):
        return {"check_runs": [], "check_runs_truncated": False}
    rows = conn.execute("""SELECT id, run_key, prepared_state_revision, artifact_digest,
        plan_digest, state, created_at, completed_at, receipt_json FROM system_change_check_runs
        WHERE project_id=? AND proposal_id=? ORDER BY id DESC LIMIT ?""",
        (project_id, proposal_id, limit + 1)).fetchall()
    history = []
    for row in rows[:limit]:
        item = dict(row)
        receipt = json.loads(item.pop("receipt_json") or "{}")
        item.update(outcome=receipt.get("outcome", "unknown"), checks_executed=receipt.get("checks_executed"))
        history.append(item)
    return {"check_runs": history, "check_runs_truncated": len(rows) > limit}
