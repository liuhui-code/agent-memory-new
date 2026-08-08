# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any


MEMORY_TABLES = {
    "semantic_facts": "updated_at",
    "episodes": "created_at",
    "reflections": "created_at",
    "code_files": "updated_at",
    "code_symbols": "updated_at",
    "code_log_statements": "updated_at",
    "memory_edges": "created_at",
}
EVIDENCE_TABLES = {
    "semantic": ("semantic_facts", "updated_at"),
    "reflection": ("reflections", "created_at"),
    "episode": ("episodes", "created_at"),
    "code_log": ("code_log_statements", "updated_at"),
}
MAX_TASK_BYTES = 1024 * 1024


def task_digest(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SystemExit(f"failed to read cohort task file: {path}") from exc
    if not data or len(data) > MAX_TASK_BYTES:
        raise SystemExit("cohort task file must be non-empty and no larger than 1 MiB")
    return hashlib.sha256(data).hexdigest()


def memory_manifest(
    conn: sqlite3.Connection, project_id: str, captured_at: str,
) -> tuple[dict[str, Any], str]:
    tables: dict[str, Any] = {}
    for table, time_column in MEMORY_TABLES.items():
        row = conn.execute(
            f"SELECT COUNT(*) AS count, MAX(id) AS max_id, MAX({time_column}) AS max_time "
            f"FROM {table} WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        tables[table] = {
            "count": int(row["count"] or 0),
            "max_id": int(row["max_id"] or 0),
            "max_time": row["max_time"],
        }
    code = conn.execute(
        "SELECT generation, source_revision, status, updated_at FROM code_index_state "
        "WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    graph = conn.execute(
        "SELECT graph_revision, updated_at FROM graph_runtime_state WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    value = {
        "schema_version": "prospective-memory-manifest/v1",
        "captured_at": captured_at,
        "tables": tables,
        "code_index": dict(code) if code else None,
        "graph": dict(graph) if graph else None,
    }
    return value, canonical_digest(value)


def verify_evidence_refs(
    conn: sqlite3.Connection,
    project_id: str,
    refs: list[dict[str, Any]],
    available_at: str,
) -> list[dict[str, Any]]:
    verified = []
    for item in refs:
        kind = str(item["record_type"])
        table, time_column = EVIDENCE_TABLES[kind]
        row = conn.execute(
            f"SELECT id, {time_column} AS available_time FROM {table} "
            "WHERE project_id = ? AND id = ?",
            (project_id, int(item["record_id"])),
        ).fetchone()
        if row is None:
            raise SystemExit(f"cohort opportunity evidence does not exist: {kind}:{item['record_id']}")
        observed = str(row["available_time"] or "")
        if observed and observed > available_at:
            raise SystemExit(f"cohort opportunity evidence is newer than task start: {kind}:{item['record_id']}")
        verified.append({
            "record_type": kind,
            "record_id": int(row["id"]),
            "available_time": observed or None,
        })
    return verified


def source_snapshot(root: Path) -> dict[str, Any]:
    revision = run_git(root, "rev-parse", "HEAD")
    status = run_git(root, "status", "--porcelain=v1", "-z")
    if revision.returncode != 0 or status.returncode != 0:
        return {
            "schema_version": "prospective-source-snapshot/v1",
            "revision": "unversioned",
            "dirty": None,
            "status_digest": None,
            "changed_entry_count": None,
            "replay_eligible": False,
        }
    payload = status.stdout.encode("utf-8")
    changed = [item for item in status.stdout.split("\0") if item]
    clean = not changed
    return {
        "schema_version": "prospective-source-snapshot/v1",
        "revision": revision.stdout.strip(),
        "dirty": not clean,
        "status_digest": hashlib.sha256(payload).hexdigest(),
        "changed_entry_count": len(changed),
        "replay_eligible": clean,
    }


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False,
    )


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
