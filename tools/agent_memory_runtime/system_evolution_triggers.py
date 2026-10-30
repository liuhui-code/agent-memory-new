# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3
from typing import Any

from .models import Project
from .storage import now_iso
from .system_evolution_contract import canonical_json, content_digest, require
from .system_evolution_schema import registry_available
from .system_evolution_store import registry_connection
from .system_evolution_trigger_contract import trigger_choice, validate_trigger
from .system_evolution_trigger_schema import (
    POLICY, create_triggers, task_claim, trigger_view,
)


def task_records(conn: sqlite3.Connection, project_id: str, task: dict[str, str]) -> tuple[sqlite3.Row | None, sqlite3.Row | None]:
    claim = task_claim(conn, project_id, task)
    latest = None
    if registry_available(conn):
        threads = conn.execute("""SELECT review_key, MAX(review_revision) AS review_revision
            FROM system_meta_reviews WHERE project_id=? AND task_origin=? AND task_key=?
            GROUP BY review_key LIMIT 2""", (project_id, task["origin"], task["key"])).fetchall()
        require(len(threads) <= 1, "Task identity has multiple review threads; resolve the ambiguity.", "task_identity_conflict")
        if threads:
            latest = conn.execute("""SELECT * FROM system_meta_reviews
                WHERE project_id=? AND review_key=? AND review_revision=?""",
                (project_id, threads[0]["review_key"], threads[0]["review_revision"])).fetchone()
    require(claim is None or latest is None or claim["review_key"] == latest["review_key"],
            "Claim and report have conflicting task bindings.", "trigger_claim_conflict")
    return claim, latest


def report_binding(request: dict[str, Any], trigger: str, revision: int) -> dict[str, Any]:
    return {"report_format": "system-meta-review/v1", "review_revision": revision, "trigger": trigger,
            **{key: request[key] for key in ("task_ref", "task_state", "task_outcome", "memory_use", "version_refs", "query_refs")}}


def allow_review(result: dict[str, Any], request: dict[str, Any], trigger: str,
                 review_key: str | None, revision: int) -> dict[str, Any]:
    result.update(decision="review", should_review=True, trigger=trigger, review_key=review_key,
                  next_review_revision=revision, report_binding=report_binding(request, trigger, revision))
    return result


def decide_trigger(project: Project, request: dict[str, Any], claim_requested: bool = False) -> dict[str, Any]:
    encoded = validate_trigger(request)
    trigger, reason = trigger_choice(request)
    result: dict[str, Any] = {
        "schema_version": "system-meta-trigger-decision/v1", "policy_version": POLICY,
        "decision": "skip", "should_review": False, "reason": reason, "trigger": None,
        "project_id": project.project_id, "archive_available": None,
        "review_key": None, "next_review_revision": None, "report_binding": None,
        "claim_requested": claim_requested, "claim_created": False, "claim": None,
        "claim_unavailable_reason": None, "model_invoked": False, "evidence_verified": False,
        "task_identity_authenticated": False, "task_boundary_observed": False,
        "host_invocation_guaranteed": False, "application_performed": False,
        "budget": {"max_report_chars": 4000, "max_evidence_refs": 8, "max_checks": 5,
                   "max_proposals": 1, "automatic_retries": 0},
    }
    if trigger is None:
        return result
    declared_project = request["version_refs"].get("archive_project_id")
    require(declared_project in (None, project.project_id), "Declared archive differs from --project.", "archive_identity_mismatch")
    task = request["task_ref"]
    if task is None:
        result["claim_unavailable_reason"] = "task_identity_unavailable"
        return allow_review(result, request, trigger, None, 1)
    result["archive_available"] = project.db_path.is_file()
    key = "meta-" + content_digest(canonical_json({"project_id": project.project_id, "task_ref": task}))
    if not result["archive_available"]:
        result["claim_unavailable_reason"] = "archive_not_initialized"
        if claim_requested and trigger != "manual":
            result["reason"] = "archive_not_initialized"
            return result
        return allow_review(result, request, trigger, key, 1)
    with registry_connection(project, write=claim_requested) as conn:
        claimed, latest = task_records(conn, project.project_id, task)
        if claimed is not None:
            key = claimed["review_key"]
            result["claim"] = trigger_view(claimed)
        elif latest is not None:
            key = latest["review_key"]
        revision = int(latest["review_revision"]) + 1 if latest else 1
        if trigger != "manual" and (claimed is not None or latest is not None):
            result.update(reason="already_reviewed" if latest else "already_claimed", review_key=key)
            return result
        if revision > 2**31 - 1:
            result.update(reason="review_revision_limit", review_key=key)
            return result
        if claim_requested and claimed is None:
            if latest is None and registry_available(conn):
                collision = conn.execute("SELECT 1 FROM system_meta_reviews WHERE project_id=? AND review_key=? LIMIT 1",
                                         (project.project_id, key)).fetchone()
                require(collision is None, "Derived review key belongs to another task; resolve the conflict.", "trigger_claim_conflict")
            create_triggers(conn)
            timestamp = now_iso()
            cur = conn.execute("""INSERT INTO system_meta_review_triggers(
                project_id, task_origin, task_key, review_key, "trigger", policy_version,
                request_digest, request_json, state, review_id, review_revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (project.project_id, task["origin"], task["key"], key, trigger, POLICY,
                 content_digest(encoded), encoded, "recorded" if latest else "reserved",
                 latest["id"] if latest else None, latest["review_revision"] if latest else None, timestamp, timestamp))
            created = conn.execute("SELECT * FROM system_meta_review_triggers WHERE id=?", (cur.lastrowid,)).fetchone()
            result.update(claim_created=True, claim=trigger_view(created))
        return allow_review(result, request, trigger, key, revision)
