# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sys
from pathlib import Path
from time import monotonic
from typing import Any

from .models import Project
from .storage import now_iso
from .system_evolution_check_plan import load_check_plan, observe_binding, observe_outputs, plan_summary, require_executables
from .system_evolution_check_process import execute_check
from .system_evolution_checks_schema import active_check, check_run_view, checks_available, create_checks
from .system_evolution_candidates_schema import active_candidate, candidate_for_plan
from .system_evolution_contract import SystemEvolutionError, canonical_json, content_digest, identifier, require
from .system_evolution_schema import registry_available
from .system_evolution_lifecycle_store import active_operation
from .system_evolution_store import proposal_view, registry_connection


def check_context(project: Project, change_id: int, run_key: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    with registry_connection(project) as conn:
        require(registry_available(conn), "No system governance registry exists.", "not_found")
        row = conn.execute("SELECT * FROM system_change_proposals WHERE project_id=? AND id=?",
                           (project.project_id, change_id)).fetchone()
        require(row is not None, "System-change proposal not found.", "not_found")
        existing = None
        if checks_available(conn):
            saved = conn.execute("SELECT * FROM system_change_check_runs WHERE project_id=? AND run_key=?",
                                 (project.project_id, run_key)).fetchone()
            existing = check_run_view(saved) if saved else None
        return proposal_view(row), existing


def prepared_binding(change: dict[str, Any], revision: int, digest: str) -> None:
    require(change["state"] == "prepared" and change["state_revision"] == revision,
            "Inspect the current prepared proposal revision before checking.", "state_conflict")
    require(change["artifact_digest"] == digest, "Check plan does not bind the prepared artifact.", "check_binding_mismatch")


def binding_observation(plan: dict[str, Any], manifest: dict[str, Any], candidate: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        value = observe_binding(plan, manifest, candidate)
        files = value.pop("source_files")
        value["observed_files_digest"] = content_digest(canonical_json(files))
        return value
    except SystemEvolutionError as error:
        return {"matches": False, "observation_error": error.code, "observed_at": now_iso(),
                "scope": "candidate_and_declared_files" if candidate else "declared_files_only"}


def run_result(run: dict[str, Any], reused: bool) -> dict[str, Any]:
    return {"schema_version": "system-change-check-run/v1", "run": run, "reused": reused,
            "evidence_verified": False, "promotion_eligible": False, "application_performed": False,
            "proposal_state_changed": False}


def matching_run(existing: dict[str, Any], change_id: int, revision: int, digest: str) -> dict[str, Any]:
    require(existing["proposal_id"] == change_id and existing["prepared_state_revision"] == revision
            and existing["plan_digest"] == digest, "Run key already binds a different check request.", "run_key_conflict")
    require(existing["state"] != "running", "Check run is running or unresolved; it cannot be retried.", "check_run_in_progress")
    return run_result(existing, True)


def reserve_run(project: Project, change_id: int, revision: int, run_key: str, plan: dict[str, Any],
                summary: dict[str, Any], receipt: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    digest = content_digest(canonical_json(plan))
    with registry_connection(project, write=True) as conn:
        require(registry_available(conn), "No system governance registry exists.", "not_found")
        create_checks(conn)
        existing = conn.execute("SELECT * FROM system_change_check_runs WHERE project_id=? AND run_key=?",
                                (project.project_id, run_key)).fetchone()
        if existing is not None:
            return matching_run(check_run_view(existing), change_id, revision, digest)["run"], False
        row = conn.execute("SELECT * FROM system_change_proposals WHERE project_id=? AND id=?",
                           (project.project_id, change_id)).fetchone()
        require(row is not None, "System-change proposal not found.", "not_found")
        prepared_binding(proposal_view(row), revision, plan["artifact_digest"])
        require(not active_check(conn, project.project_id, change_id),
                "Another check run is running or unresolved for this proposal.", "check_run_in_progress")
        require(not active_candidate(conn, project.project_id, change_id),
                "Candidate preparation is still running or unresolved.", "candidate_in_progress")
        require(not active_operation(conn, project.project_id, change_id), "Lifecycle work is unresolved.", "operation_in_progress")
        if plan["schema_version"] != "system-change-check-plan/v1":
            candidate_for_plan(conn, project.project_id, change_id, revision, plan["candidate_key"],
                               plan["candidate_digest"], plan["artifact_digest"])
        cur = conn.execute("""INSERT INTO system_change_check_runs(
            project_id, proposal_id, run_key, prepared_state_revision, artifact_digest,
            plan_digest, plan_summary_json, state, receipt_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)""",
            (project.project_id, change_id, run_key, revision, plan["artifact_digest"], digest,
             canonical_json(summary), canonical_json(receipt), now_iso()))
        created = conn.execute("SELECT * FROM system_change_check_runs WHERE id=?", (cur.lastrowid,)).fetchone()
        return check_run_view(created), True


def record_progress(project: Project, run_id: int, receipt: dict[str, Any], state: str = "running") -> dict[str, Any]:
    with registry_connection(project, write=True) as conn:
        require(registry_available(conn) and checks_available(conn), "Check-run storage is unavailable.", "schema_incomplete")
        completed = now_iso() if state != "running" else None
        cur = conn.execute("""UPDATE system_change_check_runs SET receipt_json=?, state=?, completed_at=?
            WHERE project_id=? AND id=? AND state='running'""",
            (canonical_json(receipt), state, completed, project.project_id, run_id))
        require(cur.rowcount == 1, "Check-run state changed; do not repeat the execution.", "check_run_conflict")
        row = conn.execute("SELECT * FROM system_change_check_runs WHERE id=?", (run_id,)).fetchone()
        return check_run_view(row)


def check_change(project: Project, change_id: int, revision: int, run_key: str,
                 plan_file: str, execute: bool = False) -> dict[str, Any]:
    require(type(change_id) is int and 0 < change_id <= 2**63 - 1
            and type(revision) is int and 0 < revision <= 2**31 - 1,
            "Positive proposal ID and prepared revision are required.", "invalid_request")
    identifier(run_key, "run_key")
    change, existing = check_context(project, change_id, run_key)
    manifest = existing["plan_summary"]["artifact_manifest"] if existing else change["artifact_manifest"]
    require(manifest is not None, "Prepare an artifact before creating a check plan.", "artifact_required")
    root = Path(manifest["development_root"])
    plan = load_check_plan(plan_file, root, change_id, revision, len(change["candidate"]["acceptance_criteria"]))
    digest = content_digest(canonical_json(plan))
    if existing is not None:
        return matching_run(existing, change_id, revision, digest)
    require_executables(plan)
    prepared_binding(change, revision, plan["artifact_digest"])
    candidate = None
    if plan["schema_version"] != "system-change-check-plan/v1":
        with registry_connection(project) as conn:
            candidate = candidate_for_plan(conn, project.project_id, change_id, revision, plan["candidate_key"],
                                           plan["candidate_digest"], plan["artifact_digest"])
    observed = binding_observation(plan, manifest, candidate)
    require(observed["matches"], "Declared artifact/source files do not match the check plan.", "check_binding_mismatch")
    summary = plan_summary(plan, manifest, candidate)
    execution_root = Path(candidate["binding"]["root"]) if candidate else root
    for check in plan["checks"]:
        observe_outputs(check, execution_root, before=True)
    suffix = plan["schema_version"].rsplit("/", 1)[1]
    if not execute:
        return {"schema_version": "system-change-check-preview/" + suffix, "proposal_id": change_id,
                "prepared_state_revision": revision, "plan_digest": digest, "plan_summary": summary,
                "binding": observed, "checks_executed": False, "evidence_verified": False,
                "promotion_eligible": False, "application_performed": False, "proposal_state_changed": False}
    receipt: dict[str, Any] = {
        "schema_version": "system-change-execution/" + suffix,
        "started_at": now_iso(), "completed_at": None,
        "binding_before": observed, "binding_after": None, "results": [], "outcome": "unknown",
        "checks_executed": False, "elapsed_ms": None, "tokens": None, "stdout_stored": False,
        "elapsed_scope": "after_reservation_before_final_write",
        "stderr_stored": False, "argv_stored": False,
        "scope": "candidate_and_declared_files" if candidate else "declared_files_only",
        "execution_root": str(execution_root), "candidate_key": plan.get("candidate_key"),
        "command_source_use_verified": False,
        "collector_python": sys.version.split()[0], "collector_platform": sys.platform,
        "environment_authenticated": False, "assertion_mapping": "caller_declared",
        "active_check_key": None,
    }
    run, inserted = reserve_run(project, change_id, revision, run_key, plan, summary, receipt)
    if not inserted:
        return run_result(run, True)
    started = monotonic()
    try:
        for check in plan["checks"]:
            before = binding_observation(plan, manifest, candidate)
            if not before["matches"]:
                receipt.update(outcome="binding_changed", binding_after=before)
                break
            try:
                observe_outputs(check, execution_root, before=True)
            except SystemEvolutionError as error:
                receipt.update(outcome="output_binding_error", output_error=error.code)
                break
            receipt["active_check_key"] = check["key"]
            record_progress(project, run["id"], receipt)
            result = execute_check(check, execution_root)
            if "result_files" in check:
                try:
                    result["result_files"] = observe_outputs(check, execution_root)
                except SystemEvolutionError as error:
                    result.update(outcome="output_unavailable", output_error=error.code, result_files=[])
            result["binding_before"] = before
            result["binding_after"] = binding_observation(plan, manifest, candidate)
            receipt["results"].append(result)
            receipt["active_check_key"] = None
            receipt["checks_executed"] = any(item["process_started"] for item in receipt["results"])
            receipt["binding_after"] = result["binding_after"]
            receipt["outcome"] = "binding_changed" if not result["binding_after"]["matches"] else result["outcome"]
            record_progress(project, run["id"], receipt)
            if receipt["outcome"] != "exit_zero":
                break
        if receipt["outcome"] == "exit_zero":
            receipt["outcome"] = "all_exit_zero"
    except BaseException:
        receipt.update(outcome="interrupted", completed_at=now_iso(), elapsed_ms=round((monotonic() - started) * 1000, 3))
        if receipt["active_check_key"] is not None:
            receipt["interrupted_check_key"] = receipt["active_check_key"]
            receipt["checks_executed"] = True if receipt["checks_executed"] else None
            receipt["execution_observation_incomplete"] = True
        receipt["binding_after"] = binding_observation(plan, manifest, candidate)
        record_progress(project, run["id"], receipt, "interrupted")
        raise
    receipt.update(completed_at=now_iso(), elapsed_ms=round((monotonic() - started) * 1000, 3),
                   unexecuted_check_keys=[item["key"] for item in plan["checks"][len(receipt["results"]):]])
    finished = record_progress(project, run["id"], receipt, "completed")
    return run_result(finished, False)
