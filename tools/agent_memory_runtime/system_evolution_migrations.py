# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path
from time import monotonic
from typing import Any

from .models import Project
from .storage import now_iso
from .system_evolution_contract import EDITABLE_STATES, PROTECTED_STATES, SystemEvolutionError, require
from .system_evolution_schema import SUPPORTED_VERSIONS, registry_available
from .system_evolution_store import registry_connection


def version(conn: sqlite3.Connection) -> str:
    require(registry_available(conn), "No system governance registry exists.", "not_found")
    return conn.execute("SELECT version FROM runtime_schema_versions WHERE component='system_evolution'").fetchone()[0]


def no_active_work(conn: sqlite3.Connection) -> None:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, state in (("system_change_check_runs", "running"), ("system_change_candidates", "preparing"),
                         ("system_change_operations", "running")):
        if table in tables:
            blocked = ("running", "interrupted") if table == "system_change_operations" else (state, state)
            require(conn.execute(f"SELECT 1 FROM {table} WHERE state IN (?,?) LIMIT 1", blocked).fetchone() is None,
                    "Resolve active or unknown work before changing the archive schema.", "schema_work_in_progress")


def rebuild_proposals(conn: sqlite3.Connection, target: str) -> int:
    allowed = EDITABLE_STATES | (PROTECTED_STATES if target == "system-evolution-v2" else set())
    states = {row[0] for row in conn.execute("SELECT DISTINCT state FROM system_change_proposals")}
    require(states <= allowed, "Downgrade would discard lifecycle state; keep the compatible Runtime.", "schema_downgrade_blocked")
    count = conn.execute("SELECT COUNT(*) FROM system_change_proposals").fetchone()[0]
    sequence = conn.execute("SELECT seq FROM sqlite_sequence WHERE name='system_change_proposals'").fetchone()
    objects = conn.execute("SELECT sql FROM sqlite_master WHERE tbl_name='system_change_proposals' AND sql IS NOT NULL AND type IN ('index','trigger')").fetchall()
    require(conn.execute("SELECT 1 FROM sqlite_master WHERE name='system_change_proposals_upgrade'").fetchone() is None,
            "Migration staging table already exists; inspect the archive.", "schema_incomplete")
    state_sql = ",".join("'" + item + "'" for item in sorted(allowed))
    conn.execute(f"""CREATE TABLE system_change_proposals_upgrade(
        id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
        review_id INTEGER NOT NULL UNIQUE REFERENCES system_meta_reviews(id),
        target_component TEXT NOT NULL, change_kind TEXT NOT NULL, candidate_json TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ({state_sql})),
        state_revision INTEGER NOT NULL DEFAULT 1, artifact_manifest TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    conn.execute("INSERT INTO system_change_proposals_upgrade SELECT * FROM system_change_proposals")
    conn.execute("DROP TABLE system_change_proposals")
    conn.execute("ALTER TABLE system_change_proposals_upgrade RENAME TO system_change_proposals")
    for row in objects:
        conn.execute(row[0])
    if sequence is not None:
        conn.execute("UPDATE sqlite_sequence SET seq=MAX(seq,?) WHERE name='system_change_proposals'", (sequence[0],))
    require(conn.execute("SELECT COUNT(*) FROM system_change_proposals").fetchone()[0] == count,
            "Proposal preservation check failed.", "schema_preservation_failed")
    return count


def migrate_governance(project: Project, target: str, backup_file: str, execute: bool = False) -> dict[str, Any]:
    require(target in SUPPORTED_VERSIONS, "Unsupported governance schema target.", "invalid_request")
    with registry_connection(project) as conn:
        current = version(conn)
        no_active_work(conn)
    result = {"schema_version": "system-schema-migration/v1", "from_version": current, "to_version": target,
              "migration_performed": False, "user_data_restore_performed": False}
    if current == target:
        return {**result, "reused": True}
    backup = Path(backup_file).expanduser().absolute()
    parent = backup.parent.resolve(strict=True)
    backup = parent / backup.name
    require(not backup.exists() and not backup.is_symlink() and parent.is_dir()
            and project.memory_home.resolve() not in backup.parents,
            "Choose a new backup file outside Memory Home in an existing directory.", "invalid_backup")
    result.update(backup_file=str(backup), backup_scope="committed_archive_under_write_lock")
    if not execute:
        return result
    options: dict[str, Any] = {"uri": True, "isolation_level": None, "timeout": 5}
    if hasattr(sqlite3, "LEGACY_TRANSACTION_CONTROL"):
        options["autocommit"] = sqlite3.LEGACY_TRANSACTION_CONTROL
    conn = sqlite3.connect(project.db_path.as_uri() + "?mode=rw", **options)
    conn.row_factory = sqlite3.Row
    try:
        # OFF must precede BEGIN; the separate backup reader sees the locked committed state.
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN IMMEDIATE")
        require(version(conn) == current, "Schema changed before migration.", "state_conflict")
        require(conn.execute("SELECT 1 FROM projects WHERE project_id=?", (project.project_id,)).fetchone() is not None,
                "Archive project identity changed.", "archive_identity_mismatch")
        no_active_work(conn)
        require(conn.execute("PRAGMA foreign_key_check").fetchone() is None, "Archive has foreign-key violations.", "schema_integrity_failed")
        descriptor = os.open(str(backup), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        deadline = monotonic() + 60
        def progress(status: int, remaining: int, total: int) -> None:
            require(monotonic() < deadline, "Backup exceeded its time limit.", "schema_backup_timeout")
        source = sqlite3.connect(project.db_path.as_uri() + "?mode=ro", uri=True, isolation_level=None)
        destination = sqlite3.connect(str(backup))
        try:
            source.backup(destination, pages=64, progress=progress)
            require(destination.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "Backup is not valid.", "schema_integrity_failed")
        finally:
            destination.close()
            source.close()
        digest = hashlib.sha256()
        with backup.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1_048_576), b""):
                digest.update(chunk)
        count = rebuild_proposals(conn, target)
        conn.execute("UPDATE runtime_schema_versions SET version=? WHERE component='system_evolution'", (target,))
        require(conn.execute("PRAGMA foreign_key_check").fetchone() is None, "Migration broke a foreign key.", "schema_integrity_failed")
        require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "Migration integrity check failed.", "schema_integrity_failed")
        conn.execute("""CREATE TABLE IF NOT EXISTS system_schema_migrations(
            id INTEGER PRIMARY KEY, from_version TEXT NOT NULL, to_version TEXT NOT NULL,
            backup_file TEXT NOT NULL, backup_digest TEXT NOT NULL, created_at TEXT NOT NULL)""")
        conn.execute("INSERT INTO system_schema_migrations(from_version,to_version,backup_file,backup_digest,created_at) VALUES (?,?,?,?,?)",
                     (current, target, str(backup), digest.hexdigest(), now_iso()))
        conn.commit()
        return {**result, "migration_performed": True, "reused": False, "proposal_rows_preserved": count,
                "backup_digest": digest.hexdigest(), "post_upgrade_writes_policy": "preserve_on_supported_downgrade_otherwise_forward_repair"}
    except (sqlite3.Error, OSError) as error:
        raise SystemEvolutionError("schema_migration_failed", "Migration failed; the transaction was rolled back. Inspect the retained backup.") from error
    finally:
        conn.rollback()
        conn.close()
