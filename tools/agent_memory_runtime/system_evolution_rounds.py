# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from contextlib import nullcontext
from typing import Any

from .models import Project
from .storage import now_iso
from .system_evolution_contract import canonical_json, content_digest, identifier, require
from .system_evolution_migrations import no_active_work, version
from .system_evolution_outcomes import outcome_context
from .system_evolution_rounds_contract import validate_round_record
from .system_evolution_rounds_schema import TABLE, rounds_available
from .system_evolution_schema import registry_available
from .system_evolution_store import registry_connection


def event_view(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for name in ("request", "receipt"):
        value = json.loads(item.pop(name + "_json"))
        require(content_digest(canonical_json(value)) == item[name + "_digest"],
                "Stored round content does not match its digest.", "round_record_corrupt")
        item[name] = value
    return item


def latest_round(conn: sqlite3.Connection, project_id: str, key: str) -> dict[str, Any] | None:
    row = conn.execute(f"SELECT * FROM {TABLE} WHERE project_id=? AND round_key=? ORDER BY revision DESC LIMIT 1",
                       (project_id, key)).fetchone()
    return event_view(row) if row else None


def study_rounds(conn: sqlite3.Connection, project_id: str, key: str) -> list[dict[str, Any]]:
    rows = conn.execute(f"""SELECT e.* FROM {TABLE} e JOIN
        (SELECT round_key,MAX(revision) AS revision FROM {TABLE} WHERE project_id=? AND study_key=? GROUP BY round_key) latest
        ON e.round_key=latest.round_key AND e.revision=latest.revision
        WHERE e.project_id=? AND e.study_key=? ORDER BY e.id LIMIT 11""", (project_id, key, project_id, key)).fetchall()
    return sorted((event_view(row) for row in rows), key=lambda event: event["receipt"]["round_index"])


def result(event: dict[str, Any] | None = None, *, written: bool = False, reused: bool = False) -> dict[str, Any]:
    value = {"schema_version": "system-evolution-round/v1", "available": event is not None,
             "advisory_only": True, "records_written": written, "reused": reused,
             "proposal_state_changed": False, "application_performed": False, "model_invoked": False,
             "evidence_verified": False, "efficacy_verified": False, "promotion_eligible": False,
             "causal_effect_established": False, "history_authenticated": False}
    if event is not None:
        value["event"] = event
    return value


def read_round(project: Project, key: str | None, revision: int | None = None, limit: int = 5) -> dict[str, Any]:
    require(type(limit) is int and 1 <= limit <= 20, "Round history limit must be 1–20.", "invalid_request")
    require(revision is None or (key is not None and type(revision) is int and 1 <= revision <= 22),
            "A revision requires its round key.", "invalid_request")
    if key is not None:
        identifier(key, "round_key")
    if not project.db_path.is_file():
        return {**result(), "reason": "archive_not_initialized"}
    with registry_connection(project) as conn:
        if not registry_available(conn) or not rounds_available(conn):
            return {**result(), "reason": "round_storage_not_installed"}
        if key is None:
            rows = conn.execute(f"SELECT round_key,MAX(revision) AS revision FROM {TABLE} WHERE project_id=? GROUP BY round_key ORDER BY MAX(id) DESC LIMIT ?",
                                (project.project_id, limit + 1)).fetchall()
            return {**result(), "available": True, "rounds": [dict(row) for row in rows[:limit]], "rounds_truncated": len(rows) > limit}
        if revision is not None:
            row = conn.execute(f"SELECT * FROM {TABLE} WHERE project_id=? AND round_key=? AND revision=?",
                               (project.project_id, key, revision)).fetchone()
            require(row is not None, "Round revision not found.", "not_found")
            return result(event_view(row))
        latest = latest_round(conn, project.project_id, key)
        require(latest is not None, "Round not found.", "not_found")
        rows = conn.execute(f"SELECT revision,kind,record_key,request_digest,receipt_digest,created_at FROM {TABLE} WHERE project_id=? AND round_key=? ORDER BY revision DESC LIMIT ?",
                            (project.project_id, key, limit + 1)).fetchall()
        return {**result(latest), "history": [dict(row) for row in rows[:limit]], "history_truncated": len(rows) > limit}


def current_context(project: Project, opening: dict[str, Any], observations: str | None = None) -> dict[str, Any]:
    return outcome_context(project, opening["proposal_id"], opening["application_key"], opening["plan_file"], observations)


def record_round(project: Project, request: dict[str, Any], execute: bool = False, *,
                 connection: sqlite3.Connection | None = None) -> dict[str, Any]:
    validate_round_record(request)
    encoded = canonical_json(request)
    require(len(encoded.encode("utf-8")) <= 32768, "Round record exceeds its byte limit.")
    digest = content_digest(encoded)
    with (nullcontext(connection) if connection is not None else registry_connection(project, write=execute)) as conn:
        require(version(conn) == "system-evolution-v2" and rounds_available(conn),
                "Explicitly migrate round storage before recording.", "schema_upgrade_required")
        row = conn.execute(f"SELECT * FROM {TABLE} WHERE project_id=? AND record_key=?",
                           (project.project_id, request["record_key"])).fetchone()
        if row:
            old = event_view(row)
            require(old["request_digest"] == digest, "Record key binds different immutable input.", "round_key_conflict")
            return result(old, reused=True)
        key, kind = request["round_key"], request["kind"]
        latest = latest_round(conn, project.project_id, key)
        require((latest["revision"] if latest else 0) == request["expected_revision"],
                "Round revision changed.", "round_revision_conflict")
        if kind != "decision" or request["decision"] not in {"stop", "inconclusive"}:
            no_active_work(conn)
        if kind == "open":
            require(latest is None, "Round identity already exists.", "round_key_conflict")
            rounds = study_rounds(conn, project.project_id, request["study_key"])
            budget = request["budget"]
            if rounds:
                parent = rounds[-1]
                require(len(rounds) < rounds[0]["receipt"]["budget"]["max_rounds"], "Study round budget exhausted.", "round_budget_exhausted")
                require(parent["receipt"]["state"] == "decided" and parent["receipt"]["decision"] != "stop"
                        and parent["round_key"] == request["parent_round_key"],
                        "The latest parent round must have a non-stop terminal decision.", "round_parent_conflict")
                require(budget == rounds[0]["receipt"]["budget"], "Study count budgets are frozen.", "round_budget_conflict")
            else:
                require(request["parent_round_key"] is None, "Parent does not exist in this study.", "round_parent_conflict")
            context = current_context(project, request)
            require(context["available"] and context["plan"]["round_key"] == key,
                    "Round key must match its pre-bound R1 plan.", "round_binding_mismatch")
            if rounds:
                previous = rounds[-1]["receipt"]["context"]
                require(context["plan_document"]["digest"] != previous["plan_document"]["digest"]
                        or context["binding"]["candidate_digest"] != previous["binding"]["candidate_digest"],
                        "A new round needs a new bound plan or candidate, not another review of identical input.", "round_no_new_input")
            receipt = {"state": "open", "round_index": len(rounds) + 1, "budget": budget,
                       "opening": request, "context": context}
        else:
            require(latest is not None and latest["study_key"] == request["study_key"],
                    "Round belongs to a different study.", "round_binding_mismatch")
            decided = latest["receipt"]["state"] == "decided"
            require(not decided or (kind == "assessment" and latest["receipt"]["decision"] != "stop"),
                    "A decision cannot be replaced, and a stopped round cannot resume.", "round_closed")
            receipt = {**latest["receipt"]}
            opening = receipt["opening"]
            if kind == "assessment":
                count = conn.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE project_id=? AND round_key=? AND kind='assessment'",
                                     (project.project_id, key)).fetchone()[0]
                require(count < receipt["budget"]["max_assessments"], "Assessment record budget exhausted.", "round_budget_exhausted")
                context = current_context(project, opening, request["observations_file"])
                require(context["observations"]["document"]["digest"] == request["observations_digest"],
                        "Observation file differs from its declared digest.", "round_binding_mismatch")
                require(context["plan_document"] == receipt["context"]["plan_document"]
                        and context["binding"] == receipt["context"]["binding"],
                        "Round plan/application identity changed.", "round_binding_mismatch")
                require(not decided or context != receipt["context"],
                        "A late assessment needs new observed input, not another opinion on identical context.", "round_no_new_input")
                receipt.update(state="decided" if decided else "assessed", context=context, assessment=request,
                               assessments_recorded=count + 1, late_assessment=decided)
            else:
                reference = request["assessment_revision"]
                require(request["decision"] == "stop" and reference is None or
                        (latest["kind"] == "assessment" and reference == latest["revision"]),
                        "Decision must reference the latest assessment, or stop without one.", "round_assessment_required")
                if request["decision"] == "adopt_candidate":
                    require(latest["request"]["finding"] == "supported", "Adoption recommendation needs a supported Agent assessment.", "round_decision_incomplete")
                    fresh = current_context(project, opening, latest["request"]["observations_file"])
                    require(fresh["observations"]["document"] == receipt["context"]["observations"]["document"],
                            "Observation input changed after assessment.", "round_binding_mismatch")
                    counts = fresh["observations"]["counts"]
                    blockers = set(fresh["gaps"]) - {"task_results_are_caller_declarations", "no_causal_or_long_term_efficacy_measurement"}
                    require(not blockers and counts["included"] > 0 and counts["pass"] == counts["included"]
                            and all(item["state"] == "completed" for item in fresh["execution"]["operations"] if item["kind"] == "monitoring"),
                            "Missing, negative, drifted or unresolved context cannot recommend adoption.", "round_decision_incomplete")
                receipt.update(state="decided", decision=request["decision"], decision_revision=request["expected_revision"] + 1)
        receipt["previous_digest"] = latest["receipt_digest"] if latest else None
        stored = canonical_json(receipt)
        require(len(stored.encode("utf-8")) <= 131072, "Round snapshot exceeds 128 KiB.", "round_snapshot_too_large")
        if not execute:
            return {**result(), "available": True, "preview": {"request_digest": digest, "next_revision": request["expected_revision"] + 1,
                                                               "state": receipt["state"], "receipt_digest": content_digest(stored)}}
        stamp = now_iso()
        cursor = conn.execute(f"""INSERT INTO {TABLE}(project_id,study_key,round_key,revision,kind,record_key,
            request_digest,request_json,receipt_digest,receipt_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (project.project_id, request["study_key"], key, request["expected_revision"] + 1, kind, request["record_key"], digest, encoded,
             content_digest(stored), stored, stamp))
        return result(event_view(conn.execute(f"SELECT * FROM {TABLE} WHERE id=?", (cursor.lastrowid,)).fetchone()), written=True)
