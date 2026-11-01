# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from .campaign_input_contract import REAL_TASKS, validate_manifest
from .models import Project
from .prospective_cohort_contract import validate_protocol
from .system_evolution_candidate_git import git_command
from .system_evolution_check_plan import read_bounded_file
from .system_evolution_contract import SystemEvolutionError, canonical_json, content_digest, require, unique_object_keys


REQUIREMENTS = {
    "campaign_project": ("project.local_path", "project.project_owner_role"),
    "future_task_stream": ("task_stream.source_description", "task_stream.continuity_owner_role", "task_stream.starts_at"),
    "task_start_memory_home": ("memory.task_start_memory_home",),
    "objective_verification": ("verification.allowed_methods",),
    "raw_task_custody": ("raw_task_custody.outside_sqlite_location", "raw_task_custody.retention_days"),
    "fixed_stopping_rule": ("cohort.fixed_presented_count", "cohort.allowed_exclusion_reasons", "cohort.optional_stopping"),
}


def git_observation(root: Path) -> dict[str, Any]:
    executable = shutil.which("git")
    empty = {"available": False, "revision": None, "tree": None, "dirty": None, "status_digest": None}
    if executable is None or not root.is_dir():
        return empty
    try:
        outputs = [git_command(executable, root, args, capture=True, timeout=5, output_limit=262144)
                   for args in (["rev-parse", "HEAD"], ["rev-parse", "HEAD^{tree}"], ["status", "--porcelain=v1", "-z"])]
        if any(code != 0 for code, _ in outputs):
            return empty
        revision, tree, status = (raw for _, raw in outputs)
        return {"available": True, "revision": revision.decode("ascii").strip(), "tree": tree.decode("ascii").strip(),
                "dirty": bool(status), "status_digest": hashlib.sha256(status).hexdigest()}
    except (SystemEvolutionError, OSError, UnicodeError):
        return empty


def runtime_identity() -> dict[str, Any]:
    package = Path(__file__).resolve().parent
    root = package.parent.parent
    paths = [root / "tools/agent_memory.py", *sorted(package.rglob("*.py"))]
    require(len(paths) <= 512, "Runtime source manifest exceeds its bound.", "readiness_identity_unavailable")
    manifest = {path.relative_to(root).as_posix(): hashlib.sha256(read_bounded_file(path, 1048576)).hexdigest() for path in paths}
    return {"code_digest": content_digest(canonical_json(manifest)), "file_count": len(paths),
            "hosting_checkout": git_observation(root), "atomic_snapshot": False,
            "scope": "runtime_python_only_not_model_skills_or_environment"}


def document(path: str | None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if path is None:
        return None, {"status": "not_supplied", "digest": None}
    try:
        value = json.loads(read_bounded_file(Path(path).expanduser(), 32768).decode("utf-8"), object_pairs_hook=unique_object_keys)
        require(isinstance(value, dict), "Readiness document must be an object.")
        return value, {"status": "provided_unvalidated", "digest": content_digest(canonical_json(value))}
    except (OSError, ValueError, RecursionError):
        return None, {"status": "invalid", "digest": None, "error": "invalid_bounded_json"}


def supplied(value: dict[str, Any] | None, path: str) -> bool:
    item: Any = value
    for key in path.split("."):
        item = item.get(key) if isinstance(item, dict) else None
    return item is not None and item != "" and item != [] and item != {}


def campaign_readiness(project: Project, protocol_file: str | None = None, manifest_file: str | None = None,
                       intent: str = "system_evolution") -> dict[str, Any]:
    require(intent in {"system_evolution", "diagnosis_query"}, "Unsupported readiness intent.")
    protocol_input, protocol_state = document(protocol_file)
    manifest, manifest_state = document(manifest_file)
    missing = [name for name, fields in REQUIREMENTS.items() if not all(supplied(manifest, field) for field in fields)]
    blockers = ["missing_" + name for name in missing]
    normalized = None
    if protocol_input is None:
        blockers.append("frozen_protocol_unavailable")
    else:
        try:
            normalized = validate_protocol(protocol_input)
            protocol_state["status"] = "validated_declaration"
        except SystemExit as error:
            protocol_state.update(status="invalid", error=str(error)[:240])
            blockers.append("invalid_or_unsupported_protocol")
    if normalized is not None and normalized["evidence_origin"] != REAL_TASKS:
        blockers.append("calibration_is_not_a_real_task_source")
    valid_manifest = False
    if manifest is None:
        blockers.append("campaign_manifest_unavailable")
    elif normalized is not None and normalized["evidence_origin"] == REAL_TASKS:
        try:
            validate_manifest(manifest, normalized, project.root, project.memory_home)
            manifest_state["status"] = "validated_declaration"
            valid_manifest = True
        except SystemExit as error:
            manifest_state.update(status="invalid", error=str(error)[:240])
            blockers.append("invalid_campaign_manifest_binding")
        except (ValueError, RuntimeError, OSError):
            manifest_state.update(status="invalid", error="invalid_campaign_manifest_binding")
            blockers.append("invalid_campaign_manifest_binding")
    if intent == "system_evolution":
        blockers.append("unsupported_campaign_contract")
    inputs_valid = intent == "diagnosis_query" and valid_manifest and not blockers
    return {"schema_version": "system-meta-campaign-readiness/v1", "decision": "inputs_valid_only" if inputs_valid else "no_go",
            "intent": intent, "observed_project_id": project.project_id, "target_source": git_observation(project.root),
            "runtime_identity": runtime_identity(), "atomic_snapshot": False,
            "sections": {"internal": {"status": "supported" if intent == "diagnosis_query" else "unsupported",
                                      "supported_contract": "diagnosis/selective-query-skill/v1",
                                      "archive_file_present": project.db_path.is_file(), "archive_identity_checked": False},
                         "external": {"status": "missing" if missing else "declared_only", "missing_requirements": missing,
                                      "source_authenticated": False, "continuity_authenticated": False},
                         "campaign": {"protocol": protocol_state, "manifest": manifest_state,
                                      "target_presented": normalized["target_presented_tasks"] if normalized else None},
                         "evidence": {"status": "not_assessed", "existing_task_records_read": False,
                                      "causal_effect_established": False, "miss_rate": None}},
            "blockers": blockers, "records_written": False, "archive_initialized": False, "activity_started": False,
            "execution_authorized": False, "model_invoked": False, "evidence_verified": False,
            "efficacy_verified": False, "promotion_eligible": False}
