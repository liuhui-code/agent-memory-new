# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .models import Project
from .system_evolution_acceptance import load_document
from .system_evolution_application import target_lock
from .system_evolution_candidate_git import changed_file
from .system_evolution_check_plan import contained_path, observe_outputs, read_bounded_file, require_executables
from .system_evolution_check_process import execute_check
from .system_evolution_contract import SystemEvolutionError, canonical_json, content_digest, require, text_field
from .system_evolution_lifecycle_store import (
    change_context, finish_operation, lifecycle_result, operation_by_key, operation_view, reserve_operation,
)
from .system_evolution_store import registry_connection


def applied_context(project: Project, change: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    with registry_connection(project) as conn:
        row = conn.execute("SELECT * FROM system_change_operations WHERE project_id=? AND proposal_id=? AND kind='apply' AND state='completed' ORDER BY id DESC LIMIT 1",
                           (project.project_id, change["id"])).fetchone()
        require(row is not None, "No completed application exists.", "not_found")
        application = operation_view(row)
        acceptance = operation_by_key(conn, project.project_id, application["request"]["acceptance_key"])
    root = Path(change["artifact_manifest"]["development_root"])
    plan, binding = load_document(root, acceptance["request"]["call"]["acceptance_file"])
    require(binding == acceptance["receipt"]["acceptance_plan"], "The accepted follow-up plan changed.", "check_binding_mismatch")
    follow = plan["follow_up"]
    require(content_digest(canonical_json(follow)) == acceptance["receipt"]["follow_up_digest"], "Follow-up plan changed.", "check_binding_mismatch")
    return application, follow


def observe_applied(application: dict[str, Any], follow: dict[str, Any]) -> dict[str, Any]:
    root = Path(application["request"]["target_root"])
    require(all(changed_file(root, item["path"]) == item for item in application["request"]["after_files"]),
            "Applied code changed; preserve and inspect the drift.", "application_binding_changed")
    files = []
    for bound in follow["source_files"]:
        path = contained_path(root, bound["path"])
        raw = read_bounded_file(path, 1_048_576)
        digest = hashlib.sha256(raw).hexdigest()
        require(digest == bound["digest"], "Follow-up source changed.", "check_binding_mismatch")
        files.append({"path": bound["path"], "digest": digest, "bytes": len(raw)})
    return {"target_root": str(root), "candidate_digest": application["request"]["candidate"]["candidate_digest"],
            "application_key": application["operation_key"], "source_files": files}


def follow_up_change(project: Project, proposal_id: int, revision: int, key: str, target: str,
                     note: str, execute: bool = False) -> dict[str, Any]:
    text_field(note, "note", 500)
    require(target in {"monitoring", "closed", "needs_evidence"}, "Unsupported lifecycle follow-up.", "invalid_request")
    call = {"proposal_id": proposal_id, "expected_revision": revision, "kind": target, "note": note}
    change, previous = change_context(project, proposal_id, key, call)
    if previous:
        require(previous["state"] in {"completed", "failed"}, "Follow-up is unresolved.", "operation_in_progress")
        return lifecycle_result(previous, True)
    require(change["state_revision"] == revision, "Proposal revision changed.", "state_conflict")
    allowed = {"monitoring": {"applied", "monitoring"}, "closed": {"monitoring"}, "needs_evidence": {"checked"}}
    require(change["state"] in allowed[target], "Follow-up is invalid for this proposal state.", "invalid_transition")
    if target == "needs_evidence":
        if not execute:
            return {"schema_version": "system-change-follow-up-preview/v1", "proposal_state_changed": False}
        operation = reserve_operation(project, change, key, target, {"call": call}, {"note": note})
        return lifecycle_result(finish_operation(project, operation, {"note": note, "acceptance_invalidated": True}, proposal_state=target))
    application, follow = applied_context(project, change)
    binding = observe_applied(application, follow)
    if target == "closed":
        with registry_connection(project) as conn:
            row = conn.execute("SELECT * FROM system_change_operations WHERE project_id=? AND proposal_id=? AND kind='monitoring' AND state='completed' ORDER BY id DESC LIMIT 1",
                               (project.project_id, proposal_id)).fetchone()
            require(row is not None, "A successful post-application check is required.", "monitoring_required")
            monitoring = operation_view(row)
        require(monitoring["receipt"].get("outcome") == "all_exit_zero" and monitoring["receipt"]["binding"] == binding
                and monitoring["request"]["call"]["expected_revision"] + 1 == revision,
                "Monitoring does not cover this current application/revision.", "monitoring_required")
        for result in monitoring["receipt"]["results"]:
            for output in result["result_files"]:
                raw = read_bounded_file(contained_path(Path(binding["target_root"]), output["path"]), 1_048_576)
                require(hashlib.sha256(raw).hexdigest() == output["digest"], "Monitoring evidence changed.", "acceptance_result_changed")
    else:
        require_executables({"checks": follow["checks"]})
        for check in follow["checks"]:
            observe_outputs(check, Path(binding["target_root"]), before=True)
    if not execute:
        return {"schema_version": "system-change-follow-up-preview/v1", "binding": binding, "proposal_state_changed": False}
    with target_lock(Path(binding["target_root"])):
        require(observe_applied(application, follow) == binding, "Applied binding changed.", "application_binding_changed")
        receipt = {"binding": binding, "note": note, "results": [], "outcome": "unknown",
                   "close_condition": follow["close_condition"], "claim_scope": "declared_post_application_checks",
                   "command_source_use_verified": False, "efficacy_verified": False, "active_check_key": None,
                   "checks_executed": False}
        operation = reserve_operation(project, change, key, target, {"call": call, "target_root": binding["target_root"]}, receipt)
        if target == "closed":
            receipt.update(outcome="closed_after_declared_checks", monitoring_key=monitoring["operation_key"])
            return lifecycle_result(finish_operation(project, operation, receipt, proposal_state="closed"))
        try:
            for check in follow["checks"]:
                require(observe_applied(application, follow) == binding, "Applied binding changed.", "application_binding_changed")
                observe_outputs(check, Path(binding["target_root"]), before=True)
                receipt["active_check_key"] = check["key"]
                operation = finish_operation(project, operation, receipt, state="running")
                result = execute_check(check, Path(binding["target_root"]))
                receipt["results"].append(result)
                receipt["active_check_key"] = None
                receipt["checks_executed"] = any(item["process_started"] for item in receipt["results"])
                try:
                    result["result_files"] = observe_outputs(check, Path(binding["target_root"]))
                except SystemEvolutionError as error:
                    result.update(result_files=[], output_error=error.code)
                    if result["outcome"] == "exit_zero":
                        result["outcome"] = "output_unavailable"
                require(observe_applied(application, follow) == binding, "Applied binding changed during the check.", "application_binding_changed")
                operation = finish_operation(project, operation, receipt, state="running")
                if result["outcome"] != "exit_zero":
                    receipt["outcome"] = result["outcome"]
                    return lifecycle_result(finish_operation(project, operation, receipt, state="failed"))
            receipt["outcome"] = "all_exit_zero"
            return lifecycle_result(finish_operation(project, operation, receipt, proposal_state="monitoring"))
        except BaseException as error:
            receipt["outcome"] = "interrupted_or_unobserved"
            receipt["observation_error"] = error.code if isinstance(error, SystemEvolutionError) else "interrupted"
            receipt["execution_observation_incomplete"] = receipt["active_check_key"] is not None
            if receipt["active_check_key"] is not None and not receipt["checks_executed"]:
                receipt["checks_executed"] = None
            finish_operation(project, operation, receipt, state="failed")
            raise


def resolve_nonapplication(project: Project, key: str, execute: bool = False) -> dict[str, Any]:
    with registry_connection(project) as conn:
        operation = operation_by_key(conn, project.project_id, key)
    require(operation is not None and operation["kind"] in {"accept", "monitoring", "closed", "needs_evidence"},
            "File application recovery uses explicit resume.", "invalid_request")
    if operation["state"] in {"completed", "failed"}:
        return lifecycle_result(operation, True)
    require(operation["receipt"].get("active_check_key") is None,
            "A hard-crashed check may still have a child process; retain unknown state until independently reconciled.", "execution_observation_required")
    if not execute:
        return {"schema_version": "system-change-resolve-preview/v1", "operation": operation}
    def resolve() -> dict[str, Any]:
        receipt = {**operation["receipt"], "outcome": "aborted_without_success_claim", "unknown_observations_preserved": True}
        return lifecycle_result(finish_operation(project, operation, receipt, state="failed"))
    target = operation["request"].get("target_root")
    if target:
        with target_lock(Path(target)):
            return resolve()
    return resolve()
