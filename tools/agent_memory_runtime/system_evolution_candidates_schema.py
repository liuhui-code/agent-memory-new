# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .system_evolution_contract import require


COMPONENT = "system_evolution_candidates"
VERSION = "system-candidates-v1"
TABLE = "system_change_candidates"


def candidates_available(conn: sqlite3.Connection) -> bool:
    table = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone()
    version = conn.execute("SELECT version FROM runtime_schema_versions WHERE component=?", (COMPONENT,)).fetchone()
    if table is None:
        require(version is None, "Candidate version exists without its table.", "schema_incomplete")
        return False
    require(version is not None and version[0] == VERSION, "Unsupported candidate schema version.", "schema_version_unsupported")
    return True


def create_candidates(conn: sqlite3.Connection) -> None:
    if candidates_available(conn):
        return
    conn.execute("""CREATE TABLE system_change_candidates(
        id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
        proposal_id INTEGER NOT NULL REFERENCES system_change_proposals(id),
        prepared_state_revision INTEGER NOT NULL, candidate_key TEXT NOT NULL,
        request_digest TEXT NOT NULL, request_json TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('preparing','ready','failed','interrupted')),
        operation_root TEXT, receipt_json TEXT, created_at TEXT NOT NULL, completed_at TEXT,
        UNIQUE(project_id, candidate_key))""")
    conn.execute("""CREATE UNIQUE INDEX idx_system_candidate_preparing
        ON system_change_candidates(project_id, proposal_id) WHERE state='preparing'""")
    conn.execute("INSERT INTO runtime_schema_versions(component, version) VALUES (?, ?)", (COMPONENT, VERSION))


def active_candidate(conn: sqlite3.Connection, project_id: str, proposal_id: int) -> bool:
    if not candidates_available(conn):
        return False
    return conn.execute("""SELECT 1 FROM system_change_candidates
        WHERE project_id=? AND proposal_id=? AND state='preparing' LIMIT 1""", (project_id, proposal_id)).fetchone() is not None


def candidate_view(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    value["request"] = json.loads(value.pop("request_json"))
    raw = value.pop("receipt_json")
    value["receipt"] = json.loads(raw) if raw else None
    value.update(evidence_verified=False, promotion_eligible=False, application_performed=False)
    return value


def candidate_by_key(conn: sqlite3.Connection, project_id: str, key: str) -> dict[str, Any] | None:
    if not candidates_available(conn):
        return None
    row = conn.execute("SELECT * FROM system_change_candidates WHERE project_id=? AND candidate_key=?", (project_id, key)).fetchone()
    return candidate_view(row) if row else None


def candidate_for_plan(conn: sqlite3.Connection, project_id: str, proposal_id: int, revision: int,
                       key: str, digest: str, artifact_digest: str) -> dict[str, Any]:
    row = candidate_by_key(conn, project_id, key)
    require(row is not None and row["state"] == "ready", "Candidate is not ready for a bound check.", "candidate_binding_changed")
    require(row["proposal_id"] == proposal_id and row["prepared_state_revision"] == revision
            and row["request"]["artifact_digest"] == artifact_digest
            and row["receipt"]["candidate_digest"] == digest,
            "Candidate does not bind this prepared proposal and plan.", "candidate_binding_changed")
    return {"candidate_key": key, "candidate_digest": digest, "binding": row["receipt"]["binding"]}


def candidate_history(conn: sqlite3.Connection, project_id: str, proposal_id: int, limit: int) -> dict[str, Any]:
    if not candidates_available(conn):
        return {"candidates": [], "candidates_truncated": False}
    rows = conn.execute("""SELECT id, candidate_key, prepared_state_revision, state, created_at, completed_at
        FROM system_change_candidates WHERE project_id=? AND proposal_id=? ORDER BY id DESC LIMIT ?""",
        (project_id, proposal_id, limit + 1)).fetchall()
    return {"candidates": [dict(row) for row in rows[:limit]], "candidates_truncated": len(rows) > limit}
