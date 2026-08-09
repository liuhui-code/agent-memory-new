# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sqlite3
import stat
import sys
from pathlib import Path
from typing import Any

from .prospective_cohort_snapshot import canonical_digest
from .storage import ensure_dirs, resolve_project, write_config
from .storage_schema import create_schema


PACKAGE_SCHEMA = "paired-replay-package/v1"
ATTESTATION_SCHEMA = "paired-replay-attestation/v1"
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "agent-memory-query"


def replay_selection(protocol: dict[str, Any], prior_tasks: list[dict[str, Any]], eligibility: str) -> bool:
    policy = protocol["paired_replay"]
    if eligibility != "eligible" or policy["mode"] == "disabled":
        return False
    previous_eligible = sum(item["eligibility"] == "eligible" for item in prior_tasks)
    return previous_eligible < int(policy["max_candidates"])


def create_package(
    project: Any,
    conn: sqlite3.Connection,
    cohort: dict[str, Any],
    task: dict[str, Any],
    source: dict[str, Any],
    manifest_digest: str,
    selected: bool,
) -> dict[str, Any]:
    if not selected:
        return replay_state("not_selected")
    if not source.get("replay_eligible"):
        return replay_state("source_ineligible", selected=True)
    policy = cohort["protocol"]["paired_replay"]
    package_id = package_identifier(cohort, task)
    directory = project.runtime_dir / "paired-replay" / package_id
    snapshot = directory / "memory.db"
    try:
        directory.mkdir(parents=True, exist_ok=False)
        backup_database(conn, snapshot)
        size = snapshot.stat().st_size
        if size > int(policy["max_snapshot_bytes"]):
            snapshot.unlink(missing_ok=True)
            directory.rmdir()
            return replay_state("snapshot_exceeded", selected=True, snapshot_bytes=size)
        snapshot_digest = file_digest(snapshot)
        snapshot.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        public = {
            "schema_version": PACKAGE_SCHEMA,
            "package_id": package_id,
            "cohort_id": cohort["cohort_id"],
            "sequence_no": int(task["sequence_no"]),
            "task_id": task["task_id"],
            "task_digest": task["task_digest"],
            "protocol_digest": cohort["protocol_digest"],
            "source_identity_digest": source["identity_digest"],
            "source_revision": source["revision"],
            "source_tree_digest": source["tree_digest"],
            "memory_manifest_digest": manifest_digest,
            "memory_snapshot_digest": snapshot_digest,
            "snapshot_bytes": size,
            "skill_contract_digest": directory_digest(SKILL_ROOT),
            "retention_days": int(policy["retention_days"]),
        }
        package_digest = canonical_digest(public)
        payload = {
            **public,
            "package_digest": package_digest,
            "source_root": str(project.root),
            "source_project_id": project.project_id,
            "snapshot_path": str(snapshot),
        }
        (directory / "manifest.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return {"status": "ready", "package_id": package_id, "package_digest": package_digest,
                "task_digest": task["task_digest"], "source_identity_digest": source["identity_digest"],
                "memory_snapshot_digest": snapshot_digest, "snapshot_bytes": size}
    except OSError as exc:
        shutil.rmtree(directory, ignore_errors=True)
        raise SystemExit("failed to create paired replay package") from exc


def load_package(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"failed to read paired replay package: {path}") from exc
    required = {"package_digest", "source_root", "source_project_id", "snapshot_path"}
    if not isinstance(value, dict) or value.get("schema_version") != PACKAGE_SCHEMA or not required <= set(value):
        raise SystemExit("invalid paired replay package")
    public = {key: value[key] for key in value if key not in {"package_digest", "source_root", "source_project_id", "snapshot_path"}}
    if canonical_digest(public) != value["package_digest"]:
        raise SystemExit("paired replay package digest mismatch")
    snapshot = Path(str(value["snapshot_path"])).expanduser()
    if not snapshot.is_file() or file_digest(snapshot) != value.get("memory_snapshot_digest"):
        raise SystemExit("paired replay Memory snapshot is missing or changed")
    if snapshot.stat().st_size != int(value.get("snapshot_bytes") or -1):
        raise SystemExit("paired replay Memory snapshot size mismatch")
    if snapshot.stat().st_mode & stat.S_IWUSR:
        raise SystemExit("paired replay Memory snapshot must be read-only")
    if directory_digest(SKILL_ROOT) != value.get("skill_contract_digest"):
        raise SystemExit("paired replay Query Skill contract has changed")
    return value


def validate_case(package: dict[str, Any], case: dict[str, Any]) -> None:
    binding = case.get("paired_replay_binding")
    source = case.get("source") if isinstance(case.get("source"), dict) else {}
    if not isinstance(binding, dict) or binding.get("task_digest") != package["task_digest"]:
        raise SystemExit("paired replay case task digest does not match enrolled task")
    if case.get("id") != package["task_id"]:
        raise SystemExit("paired replay case id does not match enrolled task")
    if source.get("before_revision") != package["source_revision"]:
        raise SystemExit("paired replay case source revision does not match enrolled source")
    if source.get("fixture_group") or source.get("mutation"):
        raise SystemExit("paired replay cannot apply a fixture or mutation")


def prepare_replay_memory(workspace: Path, memory_home: Path, package: dict[str, Any], task_type: str) -> dict[str, Any]:
    target = resolve_project(str(workspace), str(memory_home))
    ensure_dirs(target)
    shutil.copyfile(Path(package["snapshot_path"]), target.db_path)
    rebind_project_database(target.db_path, str(package["source_project_id"]), target)
    write_config(target)
    from .benchmark_memory import isolated_memory_access

    access = isolated_memory_access(workspace, memory_home, task_type)
    return {**access, "replay_package_digest": package["package_digest"],
            "readonly_source_snapshot": True, "memory_snapshot_digest": package["memory_snapshot_digest"]}


def build_attestation(
    package: dict[str, Any], runner: str, runner_digest: str, treatment_mode: str, case_pack_digest: str,
) -> dict[str, Any]:
    if file_digest(Path(runner)) != runner_digest:
        raise SystemExit("paired replay runner changed during execution")
    return {
        "schema_version": ATTESTATION_SCHEMA,
        "package_digest": package["package_digest"],
        "task_digest": package["task_digest"],
        "source_identity_digest": package["source_identity_digest"],
        "memory_snapshot_digest": package["memory_snapshot_digest"],
        "skill_contract_digest": package["skill_contract_digest"],
        "runner_digest": runner_digest,
        "environment_digest": canonical_digest({"python": sys.version, "platform": platform.platform()}),
        "treatment_mode": treatment_mode,
        "case_pack_digest": case_pack_digest,
    }


def replay_state(status: str, selected: bool = False, snapshot_bytes: int | None = None) -> dict[str, Any]:
    value = {"schema_version": PACKAGE_SCHEMA, "status": status, "selected": selected}
    if snapshot_bytes is not None:
        value["snapshot_bytes"] = snapshot_bytes
    return value


def package_identifier(cohort: dict[str, Any], task: dict[str, Any]) -> str:
    return canonical_digest({"cohort": cohort["cohort_id"], "task": task["task_id"], "digest": task["task_digest"]})[:24]


def backup_database(source: sqlite3.Connection, target: Path) -> None:
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()


def rebind_project_database(path: Path, source_project_id: str, target: Any) -> None:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        create_schema(conn)
        tables = [row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        for table in tables:
            columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            if "project_id" in columns:
                conn.execute(f"UPDATE {table} SET project_id = ? WHERE project_id = ?", (target.project_id, source_project_id))
        conn.execute("UPDATE projects SET project_path = ?, project_name = ?, updated_at = CURRENT_TIMESTAMP WHERE project_id = ?", (str(target.root), target.project_name, target.project_id))
        conn.commit()
    finally:
        conn.close()


def directory_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
