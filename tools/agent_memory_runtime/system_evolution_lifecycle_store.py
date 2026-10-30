# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .models import Project
from .storage import now_iso
from .system_evolution_contract import canonical_json, content_digest, identifier, require
from .system_evolution_schema import registry_available


TABLE = "system_change_operations"


def operations_available(conn: sqlite3.Connection) -> bool:
    found = conn.execute("SELECT 1 FROM sqlite_master WHERE name=? AND type='table'", (TABLE,)).fetchone()
    version = conn.execute("SELECT version FROM runtime_schema_versions WHERE component='system_evolution_operations'").fetchone()
    require((found is None and version is None) or (found is not None and version is not None and version[0] == "system-operations-v1"),
            "Unsupported or partial lifecycle storage.", "schema_incomplete")
    return found is not None


def create_operations(conn: sqlite3.Connection) -> None:
    if operations_available(conn):
        return
    conn.execute("""CREATE TABLE system_change_operations(
        id INTEGER PRIMARY KEY, project_id TEXT NOT NULL, proposal_id INTEGER NOT NULL REFERENCES system_change_proposals(id),
        operation_key TEXT NOT NULL, kind TEXT NOT NULL, request_digest TEXT NOT NULL, request_json TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('running','completed','failed','interrupted')),
        receipt_json TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT, UNIQUE(project_id,operation_key))""")
    conn.execute("""CREATE UNIQUE INDEX idx_system_operation_active ON system_change_operations(project_id,proposal_id)
        WHERE state IN ('running','interrupted')""")
    conn.execute("INSERT INTO runtime_schema_versions(component,version) VALUES ('system_evolution_operations','system-operations-v1')")


def operation_view(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["request"] = json.loads(item.pop("request_json"))
    item["receipt"] = json.loads(item.pop("receipt_json"))
    return item


def operation_by_key(conn: sqlite3.Connection, project_id: str, key: str) -> dict[str, Any] | None:
    if not operations_available(conn):
        return None
    row = conn.execute("SELECT * FROM system_change_operations WHERE project_id=? AND operation_key=?", (project_id, key)).fetchone()
    return operation_view(row) if row else None


def active_operation(conn: sqlite3.Connection, project_id: str, proposal_id: int) -> bool:
    return operations_available(conn) and conn.execute(
        "SELECT 1 FROM system_change_operations WHERE project_id=? AND proposal_id=? AND state IN ('running','interrupted') LIMIT 1",
        (project_id, proposal_id)).fetchone() is not None


def operation_history(conn: sqlite3.Connection, project_id: str, proposal_id: int, limit: int) -> dict[str, Any]:
    if not operations_available(conn):
        return {"operations": [], "operations_truncated": False}
    rows = conn.execute("SELECT id,operation_key,kind,state,created_at,completed_at FROM system_change_operations WHERE project_id=? AND proposal_id=? ORDER BY id DESC LIMIT ?",
                        (project_id, proposal_id, limit + 1)).fetchall()
    return {"operations": [dict(row) for row in rows[:limit]], "operations_truncated": len(rows) > limit}


def change_context(project: Project, proposal_id: int, key: str, call: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    from .system_evolution_store import proposal_view, registry_connection
    identifier(key, "operation_key")
    with registry_connection(project) as conn:
        require(registry_available(conn), "No governance registry exists.", "not_found")
        row = conn.execute("SELECT * FROM system_change_proposals WHERE project_id=? AND id=?", (project.project_id, proposal_id)).fetchone()
        require(row is not None, "Proposal not found.", "not_found")
        previous = operation_by_key(conn, project.project_id, key)
        if previous:
            require(previous["request"]["call"] == call, "Operation key binds a different request.", "operation_key_conflict")
        return proposal_view(row), previous


def reserve_operation(project: Project, change: dict[str, Any], key: str, kind: str,
                      request: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    from .system_evolution_store import registry_connection
    from .system_evolution_checks_schema import active_check
    from .system_evolution_candidates_schema import active_candidate
    with registry_connection(project, write=True) as conn:
        require(registry_available(conn), "No governance registry exists.", "not_found")
        require(conn.execute("SELECT version FROM runtime_schema_versions WHERE component='system_evolution'").fetchone()[0] == "system-evolution-v2",
                "Explicitly migrate governance to v2 before lifecycle writes.", "schema_upgrade_required")
        create_operations(conn)
        require(operation_by_key(conn, project.project_id, key) is None, "Operation key was reserved; read its result before retrying.", "operation_in_progress")
        row = conn.execute("SELECT state,state_revision FROM system_change_proposals WHERE project_id=? AND id=?", (project.project_id, change["id"])).fetchone()
        require(row is not None and row["state"] == change["state"] and row["state_revision"] == change["state_revision"],
                "Proposal changed before the operation.", "state_conflict")
        require(not active_operation(conn, project.project_id, change["id"]) and not active_check(conn, project.project_id, change["id"])
                and not active_candidate(conn, project.project_id, change["id"]), "Other work is active or unresolved.", "operation_in_progress")
        encoded = canonical_json(request)
        cur = conn.execute("INSERT INTO system_change_operations(project_id,proposal_id,operation_key,kind,request_digest,request_json,state,receipt_json,created_at) VALUES (?,?,?,?,?,?,'running',?,?)",
                           (project.project_id, change["id"], key, kind, content_digest(encoded), encoded, canonical_json(receipt), now_iso()))
        return operation_view(conn.execute("SELECT * FROM system_change_operations WHERE id=?", (cur.lastrowid,)).fetchone())


def finish_operation(project: Project, operation: dict[str, Any], receipt: dict[str, Any], *, state: str = "completed",
                     proposal_state: str | None = None) -> dict[str, Any]:
    from .system_evolution_store import registry_connection
    with registry_connection(project, write=True) as conn:
        row = conn.execute("SELECT * FROM system_change_operations WHERE project_id=? AND id=?", (project.project_id, operation["id"])).fetchone()
        require(row is not None and row["state"] in {"running", "interrupted"}, "Operation has already completed.", "operation_state_conflict")
        timestamp = now_iso()
        if proposal_state:
            change = conn.execute("SELECT * FROM system_change_proposals WHERE project_id=? AND id=?", (project.project_id, operation["proposal_id"])).fetchone()
            expected = operation["request"]["call"]["expected_revision"]
            require(change["state_revision"] == expected, "Proposal revision changed during execution.", "state_conflict")
            conn.execute("UPDATE system_change_proposals SET state=?,state_revision=state_revision+1,updated_at=? WHERE id=?", (proposal_state, timestamp, change["id"]))
            conn.execute("INSERT INTO system_change_events(project_id,proposal_id,state_revision,from_state,to_state,note,artifact_manifest,created_at) VALUES (?,?,?,?,?,?,?,?)",
                         (project.project_id, change["id"], expected + 1, change["state"], proposal_state,
                          "Lifecycle operation " + operation["operation_key"], change["artifact_manifest"], timestamp))
        conn.execute("UPDATE system_change_operations SET state=?,receipt_json=?,completed_at=? WHERE id=?",
                     (state, canonical_json(receipt), timestamp if state in {"completed", "failed"} else None, operation["id"]))
        return operation_view(conn.execute("SELECT * FROM system_change_operations WHERE id=?", (operation["id"],)).fetchone())


def lifecycle_result(operation: dict[str, Any], reused: bool = False) -> dict[str, Any]:
    return {"schema_version": "system-change-lifecycle/v1", "operation": operation, "reused": reused,
            "evidence_verified": False, "promotion_eligible": False,
            "application_performed": not reused and operation["kind"] == "apply" and operation["state"] == "completed",
            "partial_side_effects_possible": operation["kind"] in {"apply", "rollback"} and operation["state"] in {"running", "interrupted"}}
