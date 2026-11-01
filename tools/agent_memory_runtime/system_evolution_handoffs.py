# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3
from typing import Any

from .models import Project
from .storage import now_iso
from .system_evolution_contract import canonical_json, content_digest, require
from .system_evolution_handoff_contract import validate_handoff
from .system_evolution_handoff_schema import TABLE, handoffs_available, task_handoff_claimed
from .system_evolution_migrations import no_active_work, version
from .system_evolution_rounds import current_context, event_view, latest_round, record_round
from .system_evolution_rounds_schema import TABLE as ROUNDS_TABLE, rounds_available
from .system_evolution_schema import registry_available
from .system_evolution_store import registry_connection
from .system_evolution_triggers import task_records


def response(reason: str, **extra: Any) -> dict[str, Any]:
    return {"schema_version": "system-evolution-handoff/v1", "decision": "skip", "should_review": False,
            "reason": reason, "advisory_only": True, "records_written": False,
            "model_invoked": False, "model_execution_observed": False, "host_invocation_guaranteed": False,
            "task_identity_authenticated": False, "history_authenticated": False,
            "evidence_verified": False, "efficacy_verified": False, "promotion_eligible": False,
            "application_performed": False, "proposal_state_changed": False, **extra}


def events(conn: sqlite3.Connection, project: Project, key: str) -> dict[str, Any]:
    rows = conn.execute(f"SELECT * FROM {TABLE} WHERE project_id=? AND round_key=? ORDER BY id", (project.project_id, key)).fetchall()
    return {row["phase"]: event_view(row) for row in rows}


def append_event(conn: sqlite3.Connection, project: Project, request: dict[str, Any], receipt: dict[str, Any],
                 phase: str, task: dict[str, str]) -> dict[str, Any]:
    encoded, snapshot = canonical_json(request), canonical_json(receipt)
    require(len(snapshot.encode("utf-8")) <= 131072, "Handoff snapshot exceeds 128 KiB.", "handoff_snapshot_too_large")
    cursor = conn.execute(f"""INSERT INTO {TABLE}(project_id,round_key,phase,task_origin,task_key,
        request_digest,request_json,receipt_digest,receipt_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (project.project_id, request["round_key"], phase, task["origin"], task["key"], content_digest(encoded), encoded,
         content_digest(snapshot), snapshot, now_iso()))
    return event_view(conn.execute(f"SELECT * FROM {TABLE} WHERE id=?", (cursor.lastrowid,)).fetchone())


def skipped_boundary(request: dict[str, Any]) -> str | None:
    if request["user_cancelled"] or request["task_state"] == "cancelled":
        return "user_stopped"
    if not request["review_enabled"]:
        return "review_disabled"
    if not request["budget_available"]:
        return "host_budget_unavailable"
    if request["activity"] in {"system_review", "system_evolution"}:
        return "recursive_review_suppressed"
    if request["task_state"] not in {"completed", "failed", "blocked"}:
        return "task_not_closed"
    return None


def claim_handoff(conn: sqlite3.Connection, project: Project, request: dict[str, Any],
                  stored: dict[str, Any], execute: bool) -> dict[str, Any]:
    if stored:
        return response("round_handoff_already_consumed", handoff=stored)
    task = request["task_ref"]
    claimed, reviewed = task_records(conn, project.project_id, task)
    if claimed or reviewed or task_handoff_claimed(conn, project.project_id, task):
        return response("task_review_already_consumed")
    declared = request["version_refs"].get("archive_project_id")
    require(declared in {None, project.project_id}, "Declared archive differs from --project.", "archive_identity_mismatch")
    latest = latest_round(conn, project.project_id, request["round_key"])
    require(latest is not None, "Round not found.", "not_found")
    require(latest["revision"] == request["expected_revision"], "Round revision changed.", "round_revision_conflict")
    if latest["receipt"]["state"] == "decided":
        return response("round_already_decided")
    previous = latest["receipt"]["context"]
    policy = previous["plan"].get("host_review")
    if policy is None or not policy["enabled"]:
        return response("prebound_host_review_not_enabled")
    no_active_work(conn)
    context = current_context(project, latest["receipt"]["opening"], request["observations_file"])
    require(context["plan_document"] == previous["plan_document"] and context["binding"] == previous["binding"],
            "Round plan/application identity changed.", "handoff_input_drift")
    observed = context["observations"]
    if observed["window_state"] != "declared_complete":
        return response("observation_window_incomplete")
    if not sum(observed["counts"][name] for name in ("pass", "fail", "partial")):
        return response("known_result_declaration_unavailable")
    if observed["tasks"] == previous["observations"].get("tasks"):
        return response("no_new_observations")
    count = conn.execute(f"SELECT COUNT(*) FROM {ROUNDS_TABLE} WHERE project_id=? AND round_key=? AND kind='assessment'",
                         (project.project_id, request["round_key"])).fetchone()[0]
    if count >= latest["receipt"]["budget"]["max_assessments"]:
        return response("assessment_budget_exhausted")
    binding = {"schema_version": "system-evolution-round-record/v1", "kind": "assessment",
               "record_key": "handoff-" + content_digest(canonical_json({"project": project.project_id, "round": request["round_key"]})),
               "study_key": latest["study_key"], "round_key": request["round_key"], "expected_revision": latest["revision"],
               "observations_file": request["observations_file"], "observations_digest": observed["document"]["digest"]}
    minimum_report = {**binding, "finding": "inconclusive", "summary": "?", "evidence_refs": [],
                      "additional_cost": {"tokens": None, "elapsed_ms": None}}
    if len(canonical_json(minimum_report)) > policy["max_report_chars"]:
        return response("host_report_budget_unavailable")
    receipt = {"state": "reserved", "round_revision": latest["revision"], "round_receipt_digest": latest["receipt_digest"],
               "context_digest": content_digest(canonical_json(context)), "context": context,
               "assessment_binding": binding, "policy": policy}
    require(len(canonical_json(receipt).encode("utf-8")) <= 131072, "Handoff snapshot exceeds 128 KiB.", "handoff_snapshot_too_large")
    if not execute:
        return response("claim_required_before_generation", decision="ready", preview=receipt)
    event = append_event(conn, project, request, receipt, "claim", task)
    return response("new_window_handoff_claimed", decision="review", should_review=True,
                    records_written=True, handoff={"claim": event})


def finish_handoff(conn: sqlite3.Connection, project: Project, request: dict[str, Any],
                   stored: dict[str, Any], execute: bool) -> dict[str, Any]:
    require("claim" in stored, "No claimed handoff exists.", "not_found")
    claim = stored["claim"]
    require(request["claim_digest"] == claim["receipt_digest"], "Claim digest differs.", "handoff_binding_mismatch")
    if "finish" in stored:
        require(stored["finish"]["request_digest"] == content_digest(canonical_json(request)),
                "This handoff already has different immutable completion input.", "handoff_finish_conflict")
        return response("existing_finish_reused", decision=stored["finish"]["receipt"]["state"], reused=True, handoff=stored)
    task = claim["request"]["task_ref"]
    receipt: dict[str, Any] = {"claim_digest": claim["receipt_digest"], "state": "failed"}
    if request["action"] == "complete":
        bound = claim["receipt"]
        assessment = request["assessment"]
        require(all(assessment[name] == value for name, value in bound["assessment_binding"].items()),
                "Assessment differs from the frozen handoff binding.", "handoff_binding_mismatch")
        require(len(canonical_json(assessment)) <= bound["policy"]["max_report_chars"],
                "Assessment exceeds its pre-bound report limit.", "handoff_report_budget_exhausted")
        latest = latest_round(conn, project.project_id, request["round_key"])
        require(latest is not None and latest["revision"] == bound["round_revision"]
                and latest["receipt_digest"] == bound["round_receipt_digest"],
                "Round changed after its handoff claim.", "round_revision_conflict")
        no_active_work(conn)
        context = current_context(project, latest["receipt"]["opening"], bound["assessment_binding"]["observations_file"])
        require(content_digest(canonical_json(context)) == bound["context_digest"],
                "Observed context changed after the model handoff; retain the consumed slot.", "handoff_input_drift")
        assessed = record_round(project, assessment, execute, connection=conn)
        receipt.update(state="recorded", assessment_revision=bound["round_revision"] + 1,
                       assessment_receipt_digest=assessed["event"]["receipt_digest"] if execute else assessed["preview"]["receipt_digest"])
    if not execute:
        return response("finish_preview", decision="ready", preview=receipt)
    finished = append_event(conn, project, request, receipt, "finish", task)
    return response("handoff_finished", decision=receipt["state"], records_written=True,
                    handoff={"claim": claim, "finish": finished})


def handoff_round(project: Project, request: dict[str, Any], execute: bool = False) -> dict[str, Any]:
    validate_handoff(request)
    action = request["action"]
    if action == "claim":
        reason = skipped_boundary(request)
        if reason:
            return response(reason)
    if not project.db_path.is_file():
        return response("archive_not_initialized")
    with registry_connection(project, write=execute and action != "inspect") as conn:
        if not registry_available(conn) or not rounds_available(conn) or not handoffs_available(conn):
            return response("handoff_storage_not_installed")
        stored = events(conn, project, request["round_key"])
        if action == "inspect":
            return response("handoff_history", decision="inspect", handoff=stored)
        require(version(conn) == "system-evolution-v2", "Use governance v2 for host handoffs.", "schema_upgrade_required")
        return claim_handoff(conn, project, request, stored, execute) if action == "claim" else finish_handoff(conn, project, request, stored, execute)
