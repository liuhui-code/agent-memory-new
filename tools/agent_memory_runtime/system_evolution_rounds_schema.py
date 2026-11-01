# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3

from .system_evolution_contract import require


COMPONENT = "system_evolution_rounds"
VERSION = "system-rounds-v1"
TABLE = "system_evolution_round_events"


def rounds_available(conn: sqlite3.Connection) -> bool:
    table = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone()
    version = conn.execute("SELECT version FROM runtime_schema_versions WHERE component=?", (COMPONENT,)).fetchone()
    if table is None and version is None:
        return False
    require(table is not None and version is not None and version[0] == VERSION,
            "Round storage is incomplete or unsupported; use a compatible Runtime.", "round_schema_unsupported")
    triggers = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (TABLE,)).fetchall()
    require({"system_rounds_no_update", "system_rounds_no_delete"} <= {row[0] for row in triggers},
            "Round immutability guards are missing.", "round_schema_unsupported")
    return True


def create_rounds_schema(conn: sqlite3.Connection) -> None:
    require(not rounds_available(conn), "Round storage already exists.", "state_conflict")
    conn.execute("""CREATE TABLE system_evolution_round_events(
        id INTEGER PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id),
        study_key TEXT NOT NULL, round_key TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
        kind TEXT NOT NULL CHECK(kind IN ('open','assessment','decision')), record_key TEXT NOT NULL,
        request_digest TEXT NOT NULL, request_json TEXT NOT NULL,
        receipt_digest TEXT NOT NULL, receipt_json TEXT NOT NULL, created_at TEXT NOT NULL,
        UNIQUE(project_id,round_key,revision), UNIQUE(project_id,record_key),
        CHECK(length(CAST(request_json AS BLOB))<=32768),
        CHECK(length(CAST(receipt_json AS BLOB))<=131072))""")
    conn.execute("CREATE INDEX idx_system_rounds_study ON system_evolution_round_events(project_id,study_key,id)")
    for action in ("UPDATE", "DELETE"):
        conn.execute(f"CREATE TRIGGER system_rounds_no_{action.lower()} BEFORE {action} ON {TABLE} "
                     "BEGIN SELECT RAISE(ABORT,'Round events are immutable'); END")
    conn.execute("INSERT INTO runtime_schema_versions(component,version) VALUES (?,?)", (COMPONENT, VERSION))
