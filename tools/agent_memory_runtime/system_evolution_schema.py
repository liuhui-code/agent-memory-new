# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3

from .system_evolution_contract import require


SCHEMA_VERSION = "system-evolution-v1"
SUPPORTED_VERSIONS = {SCHEMA_VERSION, "system-evolution-v2"}
TABLES = {"system_meta_reviews", "system_change_proposals", "system_change_events"}


def registry_available(conn: sqlite3.Connection) -> bool:
    existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    found = existing & TABLES
    if not found:
        if "runtime_schema_versions" in existing:
            version = conn.execute("SELECT version FROM runtime_schema_versions WHERE component = ?", ("system_evolution",)).fetchone()
            require(version is None, "Governance version exists without its tables.", "schema_incomplete")
        return False
    require(found == TABLES and "runtime_schema_versions" in existing,
            "System governance schema is incomplete; do not repair it through query.", "schema_incomplete")
    row = conn.execute("SELECT version FROM runtime_schema_versions WHERE component = ?", ("system_evolution",)).fetchone()
    require(row is not None and row[0] in SUPPORTED_VERSIONS,
            "Unsupported system governance schema version.", "schema_version_unsupported")
    return True


def create_registry(conn: sqlite3.Connection) -> None:
    """Create only on an explicit write, within the caller's transaction."""
    if registry_available(conn):
        return
    conn.execute("CREATE TABLE IF NOT EXISTS runtime_schema_versions(component TEXT PRIMARY KEY, version TEXT NOT NULL)")
    previous = conn.execute("SELECT version FROM runtime_schema_versions WHERE component = ?", ("system_evolution",)).fetchone()
    require(previous is None, "Governance version exists without its tables.", "schema_incomplete")
    conn.execute("""CREATE TABLE system_meta_reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
        review_key TEXT NOT NULL, review_revision INTEGER NOT NULL CHECK(review_revision >= 1),
        task_origin TEXT, task_key TEXT, payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL,
        created_at TEXT NOT NULL, UNIQUE(project_id, review_key, review_revision))""")
    conn.execute("""CREATE INDEX idx_system_reviews_task
        ON system_meta_reviews(project_id, task_origin, task_key, review_revision)""")
    conn.execute("""CREATE TABLE system_change_proposals(
        id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
        review_id INTEGER NOT NULL UNIQUE REFERENCES system_meta_reviews(id),
        target_component TEXT NOT NULL, change_kind TEXT NOT NULL, candidate_json TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('proposed','needs_evidence','prepared','rejected','superseded')),
        state_revision INTEGER NOT NULL DEFAULT 1, artifact_manifest TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    conn.execute("""CREATE INDEX idx_system_changes_state
        ON system_change_proposals(project_id, state, id)""")
    conn.execute("""CREATE TABLE system_change_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
        proposal_id INTEGER NOT NULL REFERENCES system_change_proposals(id),
        state_revision INTEGER NOT NULL, from_state TEXT, to_state TEXT NOT NULL,
        note TEXT NOT NULL, artifact_manifest TEXT, created_at TEXT NOT NULL,
        UNIQUE(proposal_id, state_revision))""")
    conn.execute("INSERT INTO runtime_schema_versions(component, version) VALUES (?, ?)", ("system_evolution", SCHEMA_VERSION))
