# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Project
from .system_evolution_acceptance import load_document
from .system_evolution_candidate_git import changed_file
from .system_evolution_candidates_schema import candidate_by_key
from .system_evolution_contract import SystemEvolutionError, identifier, require
from .system_evolution_lifecycle_store import active_operation, operation_by_key, operation_view
from .system_evolution_outcome_contract import validate_observations, validate_outcome_plan
from .system_evolution_schema import registry_available
from .system_evolution_store import artifact_identity_digest, proposal_view, registry_connection


def outcome_document(root: Path, name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(name)
    require(not path.is_absolute() and ".." not in path.parts,
            "Outcome documents must be relative to the prepared development root.", "invalid_outcome_input")
    try:
        return load_document(root, name)
    except (OSError, ValueError, RuntimeError, RecursionError) as error:
        if isinstance(error, SystemEvolutionError):
            raise
        raise SystemEvolutionError("invalid_outcome_input", "Cannot read a bounded outcome document inside its declared root.") from error


def observed_images(application: dict[str, Any]) -> dict[str, Any]:
    request = application["request"]
    root = Path(request["target_root"])
    try:
        current = [changed_file(root, item["path"]) for item in request["after_files"]]
        return {"available": True, "matches_applied_version": current == request["after_files"],
                "matches_original_version": current == request["before_files"], "atomic_snapshot": False}
    except (OSError, ValueError, RuntimeError):
        return {"available": False, "matches_applied_version": None,
                "matches_original_version": None, "atomic_snapshot": False}


def operation_summary(operation: dict[str, Any]) -> dict[str, Any]:
    receipt = operation["receipt"]
    return {**{key: operation[key] for key in ("operation_key", "kind", "state", "created_at", "completed_at")},
            "outcome": receipt.get("outcome"),
            "results": [{key: result[key] for key in ("key", "outcome", "exit_code", "output_error") if key in result}
                        for result in receipt.get("results", [])]}


def outcome_context(project: Project, proposal_id: int, application_key: str, plan_file: str,
                    observations_file: str | None = None) -> dict[str, Any]:
    require(type(proposal_id) is int and 0 < proposal_id <= 2**63 - 1, "Invalid proposal ID.", "invalid_request")
    identifier(application_key, "application_key")
    result: dict[str, Any] = {"schema_version": "system-change-outcome-context/v1", "available": False,
        "project_id": project.project_id, "advisory_only": True, "evidence_verified": False,
        "efficacy_verified": False, "promotion_eligible": False, "requires_agent_review": True,
        "proposal_state_changed": False, "application_performed": False, "records_written": False,
        "model_invoked": False, "causal_effect_established": False}
    if not project.db_path.is_file():
        return {**result, "reason": "archive_not_initialized"}
    with registry_connection(project) as conn:
        require(registry_available(conn), "No governance registry exists.", "not_found")
        row = conn.execute("SELECT * FROM system_change_proposals WHERE project_id=? AND id=?",
                           (project.project_id, proposal_id)).fetchone()
        require(row is not None, "Proposal not found.", "not_found")
        change = proposal_view(row)
        application = operation_by_key(conn, project.project_id, application_key)
        require(application is not None and application["proposal_id"] == proposal_id
                and application["kind"] == "apply" and application["state"] == "completed",
                "Select a completed application of this proposal.", "outcome_binding_mismatch")
        acceptance = operation_by_key(conn, project.project_id, application["request"]["acceptance_key"])
        require(acceptance is not None and acceptance["proposal_id"] == proposal_id
                and acceptance["kind"] == "accept" and acceptance["state"] == "completed",
                "Application acceptance is unavailable.", "outcome_binding_mismatch")
        revision = acceptance["request"]["call"]["expected_revision"]
        candidate = candidate_by_key(conn, project.project_id, application["request"]["candidate"]["candidate_key"])
        manifest = change["artifact_manifest"]
        require(manifest is not None and candidate is not None and candidate["prepared_state_revision"] == revision
                and candidate["request"]["artifact_digest"] == artifact_identity_digest(manifest)
                and candidate["receipt"]["candidate_digest"] == application["request"]["candidate"]["candidate_digest"],
                "Prepared artifacts no longer bind this application.", "outcome_binding_mismatch")
        root = Path(manifest["development_root"])
        plan, plan_binding = outcome_document(root, plan_file)
        require(plan_binding in manifest["artifacts"], "Outcome plan was not bound before checking/application.", "outcome_plan_unbound")
        validate_outcome_plan(plan, proposal_id, revision)
        rows = conn.execute("SELECT * FROM system_change_operations WHERE project_id=? AND proposal_id=? AND id>? ORDER BY id LIMIT 21",
                            (project.project_id, proposal_id, application["id"])).fetchall()
        operations = []
        for stored in rows[:20]:
            operation = operation_view(stored)
            linked = operation["receipt"].get("binding", {}).get("application_key")
            linked = linked or operation["request"]["call"].get("application_key")
            if linked == application_key:
                operations.append(operation_summary(operation))
        unresolved = active_operation(conn, project.project_id, proposal_id)
        review = conn.execute("SELECT review_key,review_revision,payload_digest FROM system_meta_reviews WHERE id=? AND project_id=?",
                              (change["review_id"], project.project_id)).fetchone()
    observations: dict[str, Any] = {"available": False, "window_state": "unavailable"}
    if observations_file is not None:
        value, binding = outcome_document(root, observations_file)
        require(binding["path"] not in {item["path"] for item in manifest["artifacts"]},
                "Later observations must be separate from prepared artifacts.", "outcome_binding_mismatch")
        observations = {"available": True, "document": binding,
                        **validate_observations(value, plan, project.project_id, plan_binding["digest"], application_key)}
    images = observed_images(application)
    gaps = ["task_results_are_caller_declarations", "no_causal_or_long_term_efficacy_measurement"]
    if observations["window_state"] != "declared_complete":
        gaps.append("observation_window_incomplete")
    if observations.get("counts", {}).get("unknown", 0):
        gaps.append("unknown_task_outcomes")
    if any(item["missing_tasks"] for item in observations.get("declared_task_costs", {}).values()):
        gaps.append("task_costs_incomplete")
    if not images["matches_applied_version"]:
        gaps.append("applied_version_drifted_rolled_back_or_unavailable")
    if unresolved or len(rows) > 20:
        gaps.append("unresolved_or_truncated_operation_history")
    return {**result, "available": True,
            "proposal": {"id": proposal_id, "state": change["state"], "state_revision": change["state_revision"],
                         "target_component": change["target_component"], "review": dict(review), "candidate": change["candidate"]},
            "binding": {"prepared_state_revision": revision, "parent_base_version": manifest["base_version"],
                        "parent_base_binding": manifest["base_binding"],
                        "candidate_digest": application["request"]["candidate"]["candidate_digest"],
                        "application_key": application_key, "acceptance_key": acceptance["operation_key"]},
            "plan": plan, "plan_document": plan_binding, "observations": observations,
            "execution": {"application_completed": True, "images": images, "operations": operations,
                          "operations_truncated": len(rows) > 20, "unresolved_operation": unresolved},
            "gaps": gaps, "decision": "current_agent_review_required"}
