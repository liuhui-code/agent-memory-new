# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .models import Project
from .storage import now_iso
from .system_evolution_contract import (
    EDITABLE_STATES, PROTECTED_STATES, SystemEvolutionError, canonical_json,
    content_digest, identifier, require, text_field, validate_report,
)
from .system_evolution_schema import create_registry, registry_available
from .system_evolution_lifecycle_store import active_operation, operation_by_key, operation_history
from .system_evolution_checks_schema import active_check, check_history, check_run_view, checks_available
from .system_evolution_candidates_schema import active_candidate, candidate_by_key, candidate_history
from .system_evolution_trigger_schema import (
    record_claim_report, require_claim_binding, trigger_history, trigger_view, triggers_available,
)


TRANSITIONS = {
    "proposed": {"needs_evidence", "prepared", "rejected", "superseded"},
    "needs_evidence": {"proposed", "prepared", "rejected", "superseded"},
    "prepared": {"prepared", "needs_evidence", "rejected", "superseded"},
    "rejected": set(), "superseded": set(),
}


@contextmanager
def registry_connection(project: Project, write: bool = False) -> Iterator[sqlite3.Connection]:
    require(project.db_path.is_file(), "Initialize the selected archive before saving a system review.", "archive_not_initialized")
    conn = None
    try:
        mode = "rw" if write else "ro"
        options: dict[str, Any] = {"uri": True, "timeout": 5.0, "isolation_level": None}
        if hasattr(sqlite3, "LEGACY_TRANSACTION_CONTROL"):
            options["autocommit"] = sqlite3.LEGACY_TRANSACTION_CONTROL
        conn = sqlite3.connect(project.db_path.as_uri() + "?mode=" + mode, **options)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        registered = conn.execute("SELECT 1 FROM projects WHERE project_id = ?", (project.project_id,)).fetchone()
        require(registered is not None, "Archive does not contain the selected project identity.", "archive_identity_mismatch")
        yield conn
        if write:
            conn.commit()
        else:
            conn.rollback()
    except sqlite3.Error as error:
        if conn is not None:
            conn.rollback()
        raise SystemEvolutionError("storage_error", "System governance storage could not complete the operation.") from error
    except (json.JSONDecodeError, UnicodeError, OverflowError) as error:
        if conn is not None:
            conn.rollback()
        raise SystemEvolutionError("stored_record_invalid", "Stored governance metadata cannot be safely decoded.") from error
    except BaseException:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if conn is not None:
            conn.close()


def review_summary(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in (
        "id", "review_key", "review_revision", "task_origin", "task_key", "payload_digest", "created_at",
    )}


def proposal_view(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    value["candidate"] = json.loads(value.pop("candidate_json"))
    value["artifact_manifest"] = json.loads(value["artifact_manifest"]) if value["artifact_manifest"] else None
    value["artifact_digest"] = artifact_identity_digest(value["artifact_manifest"]) if value["artifact_manifest"] else None
    value.update(advisory_only=True, evidence_verified=False, application_performed=False)
    return value


def save_review(project: Project, review_key: str, report: dict[str, Any]) -> dict[str, Any]:
    identifier(review_key, "review_key")
    encoded = validate_report(report)
    declared_project = report["version_refs"].get("archive_project_id")
    require(declared_project in (None, project.project_id), "Declared archive identity does not match --project.", "archive_identity_mismatch")
    digest = content_digest(encoded)
    revision = report["review_revision"]
    task = report["task_ref"] or {}
    task_identity = (task.get("origin"), task.get("key"))
    with registry_connection(project, write=True) as conn:
        create_registry(conn)
        latest = conn.execute("""SELECT * FROM system_meta_reviews
            WHERE project_id = ? AND review_key = ? ORDER BY review_revision DESC LIMIT 1""",
            (project.project_id, review_key)).fetchone()
        existing = conn.execute("""SELECT * FROM system_meta_reviews
            WHERE project_id = ? AND review_key = ? AND review_revision = ?""",
            (project.project_id, review_key, revision)).fetchone()
        if existing is not None:
            require(existing["payload_digest"] == digest, "An immutable review revision already has different content.", "revision_conflict")
            proposal = conn.execute("SELECT id FROM system_change_proposals WHERE project_id = ? AND review_id = ?",
                                    (project.project_id, existing["id"])).fetchone()
            return saved_result(existing, int(proposal["id"]) if proposal else None, False)
        require_claim_binding(conn, project.project_id, review_key, report)
        expected = int(latest["review_revision"]) + 1 if latest else 1
        require(revision == expected, f"Next review_revision must be {expected}.", "revision_conflict")
        if latest is not None:
            require((latest["task_origin"], latest["task_key"]) == task_identity,
                    "A review thread cannot change task identity.", "task_identity_conflict")
        if task:
            other = conn.execute("""SELECT review_key FROM system_meta_reviews
                WHERE project_id = ? AND task_origin = ? AND task_key = ? AND review_key != ? LIMIT 1""",
                (project.project_id, *task_identity, review_key)).fetchone()
            require(other is None, "This task already belongs to another review_key; revise that thread.", "task_identity_conflict")
        created_at = now_iso()
        cur = conn.execute("""INSERT INTO system_meta_reviews(
            project_id, review_key, review_revision, task_origin, task_key, payload_json, payload_digest, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (project.project_id, review_key, revision, *task_identity, encoded, digest, created_at))
        review_id = int(cur.lastrowid)
        record_claim_report(conn, project.project_id, report, review_id, created_at)
        proposal_id = None
        if report["change_proposals"]:
            candidate = report["change_proposals"][0]
            cur = conn.execute("""INSERT INTO system_change_proposals(
                project_id, review_id, target_component, change_kind, candidate_json, state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (project.project_id, review_id, candidate["target_component"], candidate["change_kind"],
                 canonical_json(candidate), candidate["proposal_state"], created_at, created_at))
            proposal_id = int(cur.lastrowid)
            conn.execute("""INSERT INTO system_change_events(
                project_id, proposal_id, state_revision, from_state, to_state, note, created_at)
                VALUES (?, ?, 1, NULL, ?, ?, ?)""",
                (project.project_id, proposal_id, candidate["proposal_state"], "Created from an advisory review.", created_at))
        row = conn.execute("SELECT * FROM system_meta_reviews WHERE id = ?", (review_id,)).fetchone()
        return saved_result(row, proposal_id, True)


def saved_result(row: sqlite3.Row, proposal_id: int | None, inserted: bool) -> dict[str, Any]:
    return {
        "schema_version": "system-meta-review-save/v1", "review": review_summary(row),
        "proposal_id": proposal_id, "inserted": inserted, "advisory_only": True,
        "evidence_verified": False, "ranking_updated": False,
    }


def read_registry(project: Project, limit: int = 5, review_key: str | None = None,
                  change_id: int | None = None, state: str | None = None,
                  run_key: str | None = None, trigger_id: int | None = None,
                  candidate_key: str | None = None, operation_key: str | None = None) -> dict[str, Any]:
    require(type(limit) is int and 1 <= limit <= 20, "--limit must be between 1 and 20.", "invalid_request")
    require(sum(value is not None for value in (review_key, change_id, run_key, trigger_id, candidate_key, operation_key)) <= 1,
            "Select one review-key, change-id, run-key, trigger-id or candidate-key.", "invalid_request")
    require(state is None or all(value is None for value in (review_key, change_id, run_key, trigger_id, candidate_key, operation_key)),
            "State filters apply only to the summary list.", "invalid_request")
    if review_key is not None:
        identifier(review_key, "review_key")
    if run_key is not None:
        identifier(run_key, "run_key")
    if candidate_key is not None:
        identifier(candidate_key, "candidate_key")
    if operation_key is not None:
        identifier(operation_key, "operation_key")
    if change_id is not None:
        require(type(change_id) is int and 0 < change_id <= 2**63 - 1, "Invalid change ID.", "invalid_request")
    if trigger_id is not None:
        require(type(trigger_id) is int and 0 < trigger_id <= 2**63 - 1, "Invalid trigger ID.", "invalid_request")
    require(state is None or state in EDITABLE_STATES | PROTECTED_STATES, "Unsupported state filter.", "invalid_request")
    result: dict[str, Any] = {
        "schema_version": "system-evolution-review/v1", "project_id": project.project_id,
        "available": False, "advisory_only": True, "evidence_verified": False,
    }
    if not project.db_path.is_file():
        return {**result, "reason": "archive_not_initialized"}
    with registry_connection(project) as conn:
        core_available = registry_available(conn)
        if not core_available and not triggers_available(conn):
            return {**result, "reason": "system_governance_not_initialized"}
        result["available"] = True
        if trigger_id is not None:
            require(triggers_available(conn), "No trigger slots have been recorded.", "not_found")
            row = conn.execute("SELECT * FROM system_meta_review_triggers WHERE project_id=? AND id=?",
                               (project.project_id, trigger_id)).fetchone()
            require(row is not None, "Trigger slot not found.", "not_found")
            result["trigger_claim"] = trigger_view(row, full=True)
            return result
        if not core_available:
            require(review_key is None and change_id is None and run_key is None and candidate_key is None and operation_key is None,
                    "No review or check records have been saved.", "not_found")
            result.update(counts={"review_revisions": 0, "review_threads": 0, "changes": 0}, reviews=[],
                          changes=[], reviews_truncated=False, changes_truncated=False, change_filter=state)
            result.update(trigger_history(conn, project.project_id, limit))
            return result
        if operation_key is not None:
            operation = operation_by_key(conn, project.project_id, operation_key)
            require(operation is not None, "Lifecycle operation not found.", "not_found")
            result["operation"] = operation
            return result
        if candidate_key is not None:
            candidate = candidate_by_key(conn, project.project_id, candidate_key)
            require(candidate is not None, "Candidate record not found.", "not_found")
            result["candidate"] = candidate
            return result
        if run_key is not None:
            require(checks_available(conn), "No check runs have been recorded.", "not_found")
            run = conn.execute("SELECT * FROM system_change_check_runs WHERE project_id=? AND run_key=?",
                               (project.project_id, run_key)).fetchone()
            require(run is not None, "Check run not found.", "not_found")
            result["check_run"] = check_run_view(run)
            return result
        if change_id is not None:
            row = conn.execute("SELECT * FROM system_change_proposals WHERE project_id = ? AND id = ?",
                               (project.project_id, change_id)).fetchone()
            require(row is not None, "System-change proposal not found.", "not_found")
            result["change"] = proposal_view(row)
            events = conn.execute("""SELECT * FROM system_change_events
                WHERE project_id = ? AND proposal_id = ? ORDER BY state_revision DESC LIMIT ?""",
                (project.project_id, change_id, limit + 1)).fetchall()
            result["events"] = []
            for event in events[:limit]:
                item = dict(event)
                item["artifact_manifest"] = json.loads(item["artifact_manifest"]) if item["artifact_manifest"] else None
                result["events"].append(item)
            result["events_truncated"] = len(events) > limit
            result.update(check_history(conn, project.project_id, change_id, limit))
            result.update(candidate_history(conn, project.project_id, change_id, limit))
            result.update(operation_history(conn, project.project_id, change_id, limit))
            return result
        if review_key is not None:
            rows = conn.execute("""SELECT * FROM system_meta_reviews WHERE project_id = ? AND review_key = ?
                ORDER BY review_revision DESC LIMIT ?""", (project.project_id, review_key, limit + 1)).fetchall()
            require(bool(rows), "System review thread not found.", "not_found")
            result["report"] = json.loads(rows[0]["payload_json"])
            result["revisions"] = [review_summary(row) for row in rows[:limit]]
            result["revisions_truncated"] = len(rows) > limit
            return result
        result["counts"] = dict(conn.execute("""SELECT COUNT(*) AS review_revisions,
            COUNT(DISTINCT review_key) AS review_threads FROM system_meta_reviews WHERE project_id = ?""",
            (project.project_id,)).fetchone())
        reviews = conn.execute("SELECT * FROM system_meta_reviews WHERE project_id = ? ORDER BY id DESC LIMIT ?",
                               (project.project_id, limit + 1)).fetchall()
        result["reviews"] = [review_summary(row) for row in reviews[:limit]]
        result["reviews_truncated"] = len(reviews) > limit
        result["counts"]["changes"] = conn.execute("SELECT COUNT(*) FROM system_change_proposals WHERE project_id = ?",
                                                     (project.project_id,)).fetchone()[0]
        sql = "SELECT * FROM system_change_proposals WHERE project_id = ?"
        values: list[Any] = [project.project_id]
        if state:
            sql += " AND state = ?"
            values.append(state)
        changes = conn.execute(sql + " ORDER BY id DESC LIMIT ?", (*values, limit + 1)).fetchall()
        result["changes"] = [{key: row[key] for key in (
            "id", "review_id", "target_component", "change_kind", "state", "state_revision", "updated_at",
        )} for row in changes[:limit]]
        result["changes_truncated"] = len(changes) > limit
        result["change_filter"] = state
        result.update(trigger_history(conn, project.project_id, limit))
        return result


def artifact_identity_digest(manifest: dict[str, Any]) -> str:
    identity = {"development_root": manifest["development_root"], "base_version": manifest["base_version"],
                "artifacts": sorted(manifest["artifacts"], key=lambda item: item["path"])}
    return content_digest(canonical_json(identity))


def artifact_manifest(development_root: str | None, artifact_files: list[str], base_version: str | None) -> dict[str, Any]:
    require(bool(development_root) and bool(base_version) and 1 <= len(artifact_files) <= 3,
            "Prepared state needs --development-root, --base-version and one to three --artifact-file values.", "artifact_required")
    text_field(base_version, "base_version", 240)
    try:
        root = Path(development_root).expanduser().resolve(strict=True)
        text_field(str(root), "development_root", 1000)
        require(root.is_dir(), "Development root must be a directory.", "invalid_artifact")
        artifacts = []
        seen: set[str] = set()
        for supplied in artifact_files:
            require(not Path(supplied).is_absolute(), "Artifact files must be relative to the development root.", "invalid_artifact")
            path = (root / supplied).resolve(strict=True)
            relative = path.relative_to(root).as_posix()
            text_field(relative, "artifact path", 500)
            require(path.is_file() and relative not in seen, "Artifacts must be distinct regular files.", "invalid_artifact")
            seen.add(relative)
            with path.open("rb") as handle:
                raw = handle.read(1_048_577)
            require(len(raw) <= 1_048_576, "An artifact exceeds the 1 MiB observation limit.", "invalid_artifact")
            artifacts.append({"path": relative, "bytes": len(raw), "digest": hashlib.sha256(raw).hexdigest()})
    except (OSError, ValueError, RuntimeError) as error:
        if isinstance(error, SystemEvolutionError):
            raise
        raise SystemEvolutionError("invalid_artifact", "Cannot observe artifact inside the declared development root.") from error
    return {
        "development_root": str(root), "base_version": base_version, "base_binding": "caller_declared",
        "artifacts": artifacts, "observed_at": now_iso(), "contents_stored": False,
        "checks_executed": False, "repository_snapshot_verified": False,
    }


def transition_change(project: Project, change_id: int, expected_revision: int, target: str,
                      note: str, development_root: str | None = None, artifact_files: list[str] | None = None,
                      base_version: str | None = None) -> dict[str, Any]:
    require(type(change_id) is int and 0 < change_id <= 2**63 - 1
            and type(expected_revision) is int and 0 < expected_revision < 2**31 - 1,
            "Positive proposal ID and expected state revision are required.", "invalid_request")
    require(target not in PROTECTED_STATES, "Verified/application transitions require complete reviewed evidence; this status writer cannot perform them.", "verification_gate_unavailable")
    require(target in EDITABLE_STATES, "Unsupported proposal state.", "invalid_request")
    text_field(note, "note", 500)
    files = artifact_files or []
    if target != "prepared":
        require(not files and development_root is None and base_version is None,
                "Artifact observation options apply only to prepared state.", "invalid_request")
    with registry_connection(project, write=True) as conn:
        require(registry_available(conn), "No system governance registry exists.", "not_found")
        row = conn.execute("SELECT * FROM system_change_proposals WHERE project_id = ? AND id = ?",
                           (project.project_id, change_id)).fetchone()
        require(row is not None, "System-change proposal not found.", "not_found")
        require(not active_check(conn, project.project_id, change_id),
                "A check run is still running or unresolved; proposal state cannot change.", "check_run_in_progress")
        require(not active_candidate(conn, project.project_id, change_id),
                "Candidate preparation is still running or unresolved; proposal state cannot change.", "candidate_in_progress")
        require(not active_operation(conn, project.project_id, change_id), "Lifecycle work is running or unresolved.", "operation_in_progress")
        require(row["state_revision"] == expected_revision, "Proposal state changed; inspect it before retrying.", "state_conflict")
        require(target in TRANSITIONS.get(row["state"], set()), "Unsupported transition from the current proposal state.", "invalid_transition")
        manifest = artifact_manifest(development_root, files, base_version) if target == "prepared" else None
        encoded_manifest = canonical_json(manifest) if manifest else None
        revision = expected_revision + 1
        timestamp = now_iso()
        cur = conn.execute("""UPDATE system_change_proposals SET state = ?, state_revision = ?,
            artifact_manifest = ?, updated_at = ? WHERE project_id = ? AND id = ? AND state_revision = ?""",
            (target, revision, encoded_manifest, timestamp, project.project_id, change_id, expected_revision))
        require(cur.rowcount == 1, "Proposal state changed concurrently.", "state_conflict")
        conn.execute("""INSERT INTO system_change_events(
            project_id, proposal_id, state_revision, from_state, to_state, note, artifact_manifest, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (project.project_id, change_id, revision, row["state"], target, note, encoded_manifest, timestamp))
        updated = conn.execute("SELECT * FROM system_change_proposals WHERE id = ?", (change_id,)).fetchone()
        return {"schema_version": "system-change-status/v1", "change": proposal_view(updated),
                "ranking_updated": False, "checks_executed": False, "application_performed": False}
