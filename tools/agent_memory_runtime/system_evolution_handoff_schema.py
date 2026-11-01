# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3
from typing import Any

from .system_evolution_contract import require


COMPONENT = "system_evolution_handoffs"
VERSION = "system-handoffs-v1"
TABLE = "system_evolution_handoff_events"


def handoffs_available(conn: sqlite3.Connection) -> bool:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    version = conn.execute("SELECT version FROM runtime_schema_versions WHERE component=?", (COMPONENT,)).fetchone() if "runtime_schema_versions" in tables else None
    if TABLE not in tables and version is None:
        return False
    require(TABLE in tables and version is not None and version[0] == VERSION,
            "Handoff storage is incomplete or unsupported.", "handoff_schema_unsupported")
    guards = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (TABLE,))}
    require({"system_handoffs_no_update", "system_handoffs_no_delete"} <= guards,
            "Handoff immutability guards are missing.", "handoff_schema_unsupported")
    return True


def task_handoff_claimed(conn: sqlite3.Connection, project_id: str, task: dict[str, Any]) -> bool:
    return handoffs_available(conn) and conn.execute(f"SELECT 1 FROM {TABLE} WHERE project_id=? AND task_origin=? AND task_key=? AND phase='claim'",
                                                    (project_id, task["origin"], task["key"])).fetchone() is not None


def create_handoffs_schema(conn: sqlite3.Connection) -> None:
    require(not handoffs_available(conn), "Handoff storage already exists.", "state_conflict")
    conn.execute(f"""CREATE TABLE {TABLE}(
        id INTEGER PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id),
        round_key TEXT NOT NULL, phase TEXT NOT NULL CHECK(phase IN ('claim','finish')),
        task_origin TEXT NOT NULL, task_key TEXT NOT NULL, request_digest TEXT NOT NULL, request_json TEXT NOT NULL,
        receipt_digest TEXT NOT NULL, receipt_json TEXT NOT NULL, created_at TEXT NOT NULL,
        UNIQUE(project_id,round_key,phase), CHECK(length(CAST(request_json AS BLOB))<=32768),
        CHECK(length(CAST(receipt_json AS BLOB))<=131072))""")
    conn.execute(f"CREATE UNIQUE INDEX idx_system_handoffs_task ON {TABLE}(project_id,task_origin,task_key) WHERE phase='claim'")
    for action in ("UPDATE", "DELETE"):
        conn.execute(f"CREATE TRIGGER system_handoffs_no_{action.lower()} BEFORE {action} ON {TABLE} "
                     "BEGIN SELECT RAISE(ABORT,'Handoff events are immutable'); END")
    conn.execute("INSERT INTO runtime_schema_versions(component,version) VALUES (?,?)", (COMPONENT, VERSION))
