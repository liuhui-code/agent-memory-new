# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import Project
from .system_evolution_candidate_git import observe_candidate
from .system_evolution_candidates_schema import candidate_for_plan
from .system_evolution_check_plan import contained_path, read_bounded_file, validate_check_plan
from .system_evolution_checks_schema import check_run_view
from .system_evolution_contract import canonical_json, content_digest, items, object_fields, require, text_field, unique_object_keys
from .system_evolution_lifecycle_store import change_context, finish_operation, lifecycle_result, reserve_operation
from .system_evolution_store import artifact_identity_digest, artifact_manifest, registry_connection


def load_document(root: Path, name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(name).expanduser()
    path = (root / path).resolve(strict=True)
    relative = path.relative_to(root).as_posix()
    raw = read_bounded_file(path, 32768)
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object_keys)
    require(isinstance(value, dict), "Lifecycle document must be an object.", "invalid_acceptance")
    return value, {"path": relative, "digest": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def required_gates(change: dict[str, Any]) -> set[str]:
    required = {"functionality", "negative_cases", "compatibility", "cost", "rollback"}
    if change["change_kind"] == "defect":
        required |= {"independent_reproduction", "public_output_reproduction"}
    if change["change_kind"] == "structural":
        required |= {"independent_defect_class_1", "independent_defect_class_2"}
    if change["target_component"] == "evaluator":
        required.add("known_expected")
    if change["target_component"] in {"query", "learn", "reflect", "evaluator"}:
        required |= {"existing_gates", "performance", "file_size"}
    if change["target_component"] == "data_model":
        required |= {"reader_writer_matrix", "data_preservation", "migration_restart", "post_upgrade_writes"}
    return required


def acceptance_observation(project: Project, change: dict[str, Any], acceptance_file: str, review_file: str) -> dict[str, Any]:
    manifest = change["artifact_manifest"]
    root = Path(manifest["development_root"]).resolve(strict=True)
    observed = artifact_manifest(str(root), [item["path"] for item in manifest["artifacts"]], manifest["base_version"])
    require(artifact_identity_digest(observed) == change["artifact_digest"], "Prepared artifacts changed.", "check_binding_mismatch")
    plan, plan_file = load_document(root, acceptance_file)
    review, review_binding = load_document(root, review_file)
    require(any(item["path"] == plan_file["path"] and item["digest"] == plan_file["digest"] for item in manifest["artifacts"]),
            "The acceptance plan must be a prepared artifact observed before checks.", "acceptance_plan_unbound")
    fields = {"schema_version", "proposal_id", "prepared_state_revision", "gates", "criteria", "follow_up"}
    object_fields(plan, fields, fields, "acceptance plan")
    require(plan["schema_version"] == "system-change-acceptance-plan/v1" and type(plan["proposal_id"]) is int
            and type(plan["prepared_state_revision"]) is int and plan["proposal_id"] == change["id"]
            and plan["prepared_state_revision"] == change["state_revision"], "Acceptance plan has a different subject.", "invalid_acceptance")
    fields = {"schema_version", "proposal_id", "prepared_state_revision", "candidate_key", "candidate_digest", "reviewer_ref",
              "criterion_reviews", "gate_reviews", "source_use_review"}
    object_fields(review, fields, fields, "Agent acceptance review")
    require(review["schema_version"] == "system-change-acceptance-review/v1" and type(review["proposal_id"]) is int
            and type(review["prepared_state_revision"]) is int and review["proposal_id"] == change["id"]
            and review["prepared_state_revision"] == change["state_revision"], "Review has a different subject.", "invalid_acceptance")
    text_field(review["reviewer_ref"], "reviewer_ref", 240)
    text_field(review["source_use_review"], "source_use_review", 1000)
    gates = items(plan["gates"], "gates", 12)
    keys = [gate.get("key") if isinstance(gate, dict) else None for gate in gates]
    require(all(isinstance(key, str) for key in keys) and len(set(keys)) == len(keys)
            and required_gates(change) <= set(keys), "Acceptance plan omits a required change-policy gate.", "acceptance_gate_missing")
    criteria = items(plan["criteria"], "criteria", 5)
    indices = [item.get("index") if isinstance(item, dict) else None for item in criteria]
    require(all(type(index) is int for index in indices) and sorted(indices) == list(range(len(change["candidate"]["acceptance_criteria"]))),
            "Acceptance plan must cover every proposal criterion once.", "invalid_acceptance")
    for name, values, field, expected in (("criterion_reviews", review["criterion_reviews"], "index", set(indices)),
                                          ("gate_reviews", review["gate_reviews"], "key", set(keys))):
        entries = items(values, name, 12)
        found = []
        for entry in entries:
            object_fields(entry, {field, "reason"}, {field, "reason"}, name)
            text_field(entry["reason"], "review reason", 500)
            require(type(entry[field]) is int if field == "index" else isinstance(entry[field], str), "Invalid review identity.", "invalid_acceptance")
            found.append(entry[field])
        require(len(found) == len(set(found)) and set(found) == expected, "Agent review omits an acceptance item.", "acceptance_review_missing")
    with registry_connection(project) as conn:
        candidate = candidate_for_plan(conn, project.project_id, change["id"], change["state_revision"],
                                       review["candidate_key"], review["candidate_digest"], change["artifact_digest"])
        follow = plan["follow_up"]
        object_fields(follow, {"source_files", "checks", "close_condition"}, {"source_files", "checks", "close_condition"}, "follow-up plan")
        text_field(follow["close_condition"], "close_condition", 500)
        follow_plan = {"schema_version": "system-change-check-plan/v3", "proposal_id": change["id"],
                       "prepared_state_revision": change["state_revision"], "artifact_digest": change["artifact_digest"],
                       "candidate_key": candidate["candidate_key"], "candidate_digest": candidate["candidate_digest"],
                       "source_files": follow["source_files"], "checks": follow["checks"]}
        validate_check_plan(follow_plan, change["id"], change["state_revision"], len(criteria))
        require(observe_candidate(candidate)["matches"], "Candidate drifted after checking.", "candidate_binding_changed")
        runs = {}
        evidence = {}
        for entry in [*gates, *criteria]:
            label = "key" if "key" in entry else "index"
            fields = {label, "run_key", "check_key", "result_file"}
            object_fields(entry, fields, fields, "acceptance binding")
            for name in ("run_key", "check_key", "result_file"):
                text_field(entry[name], name, 500)
            key = entry["run_key"]
            if key not in runs:
                row = conn.execute("SELECT * FROM system_change_check_runs WHERE project_id=? AND run_key=?", (project.project_id, key)).fetchone()
                require(row is not None, "A required check run is missing.", "acceptance_run_missing")
                run = check_run_view(row)
                require(run["state"] == "completed" and run["receipt"]["outcome"] == "all_exit_zero"
                        and run["proposal_id"] == change["id"] and run["prepared_state_revision"] == change["state_revision"]
                        and run["artifact_digest"] == change["artifact_digest"]
                        and run["plan_summary"]["plan_format"] == "system-change-check-plan/v3"
                        and run["plan_summary"]["candidate"] == candidate,
                        "A required run did not complete against this bound candidate with v3 outputs.", "acceptance_run_mismatch")
                runs[key] = run
            run = runs[key]
            check = next((item for item in run["plan_summary"]["checks"] if item["key"] == entry["check_key"]), None)
            result = next((item for item in run["receipt"]["results"] if item["key"] == entry["check_key"]), None)
            require(check is not None and result is not None and result["outcome"] == "exit_zero"
                    and (label != "index" or entry["index"] in check["assertion_indices"]),
                    "Acceptance check does not cover this criterion.", "acceptance_check_mismatch")
            bound = next((item for item in result.get("result_files", []) if item["path"] == entry["result_file"]), None)
            require(bound is not None, "Required result was not observed by the runner.", "acceptance_result_missing")
            path = contained_path(Path(candidate["binding"]["root"]), bound["path"])
            raw = read_bounded_file(path, 1_048_576)
            require(hashlib.sha256(raw).hexdigest() == bound["digest"], "A check result changed after observation.", "acceptance_result_changed")
            evidence[key + ":" + bound["path"]] = bound
    if change["change_kind"] == "structural":
        classes = [gate for gate in gates if gate["key"].startswith("independent_defect_class_")]
        require(len({(gate["run_key"], gate["check_key"], gate["result_file"]) for gate in classes}) == 2,
                "Independent defect classes require distinct check evidence.", "acceptance_independence_missing")
    follow_summary = {"source_files": follow["source_files"], "close_condition": follow["close_condition"],
                      "checks": [{"key": check["key"], "argv_digest": content_digest(canonical_json(check["argv"])),
                                  "result_files": check["result_files"]} for check in follow["checks"]]}
    return {"candidate": candidate, "acceptance_plan": plan_file, "review_file": review_binding,
            "follow_up_digest": content_digest(canonical_json(follow)), "follow_up_summary": follow_summary,
            "run_keys": sorted(runs), "observed_results": evidence, "gate_keys": sorted(keys),
            "agent_review": review, "agent_review_authenticated": False,
            "command_source_use_verified": False, "assertion_semantics": "current_agent_reviewed",
            "external_release_eligible": False}


def accept_change(project: Project, proposal_id: int, revision: int, key: str, acceptance_file: str,
                  review_file: str, execute: bool = False) -> dict[str, Any]:
    call = {"proposal_id": proposal_id, "expected_revision": revision, "kind": "accept",
            "acceptance_file": acceptance_file, "review_file": review_file}
    change, previous = change_context(project, proposal_id, key, call)
    if previous:
        require(previous["state"] in {"completed", "failed"}, "Acceptance operation is unresolved.", "operation_in_progress")
        return lifecycle_result(previous, True)
    require(change["state"] == "prepared" and change["state_revision"] == revision,
            "Accept only the current prepared revision.", "state_conflict")
    observation = acceptance_observation(project, change, acceptance_file, review_file)
    if not execute:
        return {"schema_version": "system-change-acceptance-preview/v1", "observation": observation,
                "proposal_state_changed": False, "promotion_eligible": False, "evidence_verified": False}
    operation = reserve_operation(project, change, key, "accept", {"call": call, "observation_digest": content_digest(canonical_json(observation))}, observation)
    try:
        require(acceptance_observation(project, change, acceptance_file, review_file) == observation,
                "Acceptance inputs changed before commit.", "check_binding_mismatch")
        return lifecycle_result(finish_operation(project, operation, observation, proposal_state="checked"))
    except BaseException:
        finish_operation(project, operation, {"error": "acceptance_not_committed"}, state="failed")
        raise
