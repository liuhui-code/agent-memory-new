# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path
from time import monotonic
from typing import Any

from .models import Project
from .storage import now_iso
from .system_evolution_candidate_git import file_bytes, prepare_git_candidate, validate_base
from .system_evolution_candidates_schema import (
    active_candidate, candidate_by_key, candidate_view, create_candidates,
)
from .system_evolution_checks_schema import active_check
from .system_evolution_contract import SystemEvolutionError, canonical_json, content_digest, identifier, require, text_field
from .system_evolution_schema import registry_available
from .system_evolution_lifecycle_store import active_operation
from .system_evolution_store import artifact_identity_digest, artifact_manifest, proposal_view, registry_connection


def candidate_result(candidate: dict[str, Any], reused: bool) -> dict[str, Any]:
    return {"schema_version": "system-change-candidate/v1", "candidate": candidate, "reused": reused,
            "proposal_state_changed": False, "evidence_verified": False,
            "promotion_eligible": False, "application_performed": False}


def candidate_request(change_id: int, revision: int, patch_file: str, candidate_home: str) -> dict[str, Any]:
    require(type(change_id) is int and 0 < change_id <= 2**63 - 1 and type(revision) is int and 0 < revision <= 2**31 - 1,
            "Positive proposal ID and prepared revision are required.", "invalid_request")
    text_field(patch_file, "patch_file", 500)
    patch = Path(patch_file)
    require(not patch.is_absolute() and ".." not in patch.parts and "\n" not in patch_file and "\t" not in patch_file,
            "Patch must be a contained relative path.", "invalid_candidate")
    home = Path(candidate_home).expanduser().resolve()
    text_field(str(home), "candidate_home", 1000)
    return {"proposal_id": change_id, "prepared_state_revision": revision,
            "patch_file": patch.as_posix(), "candidate_home": str(home)}


def matching_candidate(existing: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    require(all(existing["request"].get(name) == request[name] for name in
                ("proposal_id", "prepared_state_revision", "patch_file", "candidate_home")),
            "Candidate key already binds a different preparation request.", "candidate_key_conflict")
    require(existing["state"] != "preparing", "Candidate is preparing or unresolved; do not retry it.", "candidate_in_progress")
    return existing


def prepared_candidate_context(project: Project, change_id: int, revision: int, key: str,
                               request: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    with registry_connection(project) as conn:
        require(registry_available(conn), "No system governance registry exists.", "not_found")
        existing = candidate_by_key(conn, project.project_id, key)
        if existing is not None:
            return None, matching_candidate(existing, request)
        row = conn.execute("SELECT * FROM system_change_proposals WHERE project_id=? AND id=?",
                           (project.project_id, change_id)).fetchone()
        require(row is not None, "System-change proposal not found.", "not_found")
        change = proposal_view(row)
        require(not active_operation(conn, project.project_id, change_id), "Lifecycle work is unresolved.", "operation_in_progress")
        require(change["state"] == "prepared" and change["state_revision"] == revision,
                "Inspect the current prepared revision before creating a candidate.", "state_conflict")
        require(not active_check(conn, project.project_id, change_id) and not active_candidate(conn, project.project_id, change_id),
                "A check or candidate preparation is running or unresolved.", "candidate_in_progress")
        return change, None


def reserve_candidate(project: Project, key: str, request: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    with registry_connection(project, write=True) as conn:
        require(registry_available(conn), "No system governance registry exists.", "not_found")
        existing = candidate_by_key(conn, project.project_id, key)
        if existing is not None:
            return matching_candidate(existing, request), False
        row = conn.execute("SELECT * FROM system_change_proposals WHERE project_id=? AND id=?",
                           (project.project_id, request["proposal_id"])).fetchone()
        require(row is not None, "System-change proposal not found.", "not_found")
        change = proposal_view(row)
        require(not active_operation(conn, project.project_id, request["proposal_id"]), "Lifecycle work is unresolved.", "operation_in_progress")
        require(change["state"] == "prepared" and change["state_revision"] == request["prepared_state_revision"]
                and change["artifact_digest"] == request["artifact_digest"], "Prepared artifact changed.", "state_conflict")
        require(not active_check(conn, project.project_id, request["proposal_id"])
                and not active_candidate(conn, project.project_id, request["proposal_id"]),
                "A check or candidate preparation is running or unresolved.", "candidate_in_progress")
        create_candidates(conn)
        encoded = canonical_json(request)
        cur = conn.execute("""INSERT INTO system_change_candidates(project_id, proposal_id, prepared_state_revision,
            candidate_key, request_digest, request_json, state, created_at) VALUES (?, ?, ?, ?, ?, ?, 'preparing', ?)""",
            (project.project_id, request["proposal_id"], request["prepared_state_revision"], key, content_digest(encoded), encoded, now_iso()))
        row = conn.execute("SELECT * FROM system_change_candidates WHERE id=?", (cur.lastrowid,)).fetchone()
        return candidate_view(row), True


def record_candidate(project: Project, row_id: int, state: str, operation: Path | None,
                      receipt: dict[str, Any] | None) -> dict[str, Any]:
    with registry_connection(project, write=True) as conn:
        cur = conn.execute("""UPDATE system_change_candidates SET state=?, operation_root=?, receipt_json=?, completed_at=?
            WHERE project_id=? AND id=? AND state='preparing'""",
            (state, str(operation) if operation else None, canonical_json(receipt) if receipt else None,
             now_iso() if state != "preparing" else None, project.project_id, row_id))
        require(cur.rowcount == 1, "Candidate state changed; do not repeat preparation.", "candidate_state_conflict")
        row = conn.execute("SELECT * FROM system_change_candidates WHERE id=?", (row_id,)).fetchone()
        return candidate_view(row)


def prepare_candidate(project: Project, change_id: int, revision: int, key: str, patch_file: str,
                       candidate_home: str, execute: bool = False) -> dict[str, Any]:
    identifier(key, "candidate_key")
    try:
        request = candidate_request(change_id, revision, patch_file, candidate_home)
        change, existing = prepared_candidate_context(project, change_id, revision, key, request)
        if existing is not None:
            return candidate_result(existing, True)
        manifest = change["artifact_manifest"]
        root = Path(manifest["development_root"]).resolve(strict=True)
        home = Path(request["candidate_home"])
        require(home.is_dir() and home != root and root not in home.parents,
                "Candidate home must be an existing directory outside the development tree.", "invalid_candidate")
        memory_home = project.db_path.parents[2]
        require(home != memory_home and memory_home not in home.parents,
                "Candidate home must be outside Memory Home.", "invalid_candidate")
        path = (root / request["patch_file"]).resolve(strict=True)
        relative = path.relative_to(root).as_posix()
        bound = next((item for item in manifest["artifacts"] if item["path"] == relative), None)
        require(bound is not None and path.is_file(), "Patch is not a prepared artifact.", "invalid_candidate")
        patch = file_bytes(path, 1_048_576)
        require(hashlib.sha256(patch).hexdigest() == bound["digest"], "Prepared patch bytes changed.", "check_binding_mismatch")
        observed = artifact_manifest(str(root), [item["path"] for item in manifest["artifacts"]], manifest["base_version"])
        require(artifact_identity_digest(observed) == change["artifact_digest"], "Prepared artifact binding changed.", "check_binding_mismatch")
        executable = shutil.which("git")
        require(executable is not None, "Local Git is required for candidate preparation.", "candidate_git_unavailable")
        executable = str(Path(executable).resolve(strict=True))
        base_tree = validate_base(executable, root, manifest["base_version"])
        request.update(artifact_digest=change["artifact_digest"], base_revision=manifest["base_version"],
                       base_tree=base_tree, source_root=str(root), patch_digest=bound["digest"])
        if not execute:
            return {"schema_version": "system-change-candidate-preview/v1", "request": request,
                    "candidate_prepared": False, "proposal_state_changed": False,
                    "evidence_verified": False, "promotion_eligible": False, "application_performed": False}
    except (OSError, ValueError, RuntimeError) as error:
        if isinstance(error, SystemEvolutionError):
            raise
        raise SystemEvolutionError("invalid_candidate", "Cannot read the candidate inputs inside their declared bounds.") from error
    record, inserted = reserve_candidate(project, key, request)
    if not inserted:
        return candidate_result(record, True)
    started = monotonic()
    operation = None
    try:
        operation = Path(tempfile.mkdtemp(prefix=f"memory-candidate-{record['id']}-", dir=home))
        operation = operation.resolve(strict=True)
        require(operation.parent == home and root not in operation.parents and memory_home not in operation.parents,
                "Candidate directory binding changed before preparation.", "invalid_candidate")
        record_candidate(project, record["id"], "preparing", operation, None)
        receipt = prepare_git_candidate(executable, root, operation, patch, request["base_revision"], base_tree, request["artifact_digest"])
        receipt.update(preparation_elapsed_ms=round((monotonic() - started) * 1000, 3),
                       patch_applied_to="isolated_candidate_only", installed_product_modified=False)
        finished = record_candidate(project, record["id"], "ready", operation, receipt)
        return candidate_result(finished, False)
    except (SystemEvolutionError, OSError, ValueError) as error:
        code = error.code if isinstance(error, SystemEvolutionError) else "candidate_material_unavailable"
        failed = record_candidate(project, record["id"], "failed", operation,
                                  {"error_code": code, "elapsed_ms": round((monotonic() - started) * 1000, 3), "scope": "isolated_candidate_only"})
        return candidate_result(failed, False)
    except BaseException:
        record_candidate(project, record["id"], "interrupted", operation,
                         {"error_code": "candidate_interrupted", "elapsed_ms": round((monotonic() - started) * 1000, 3)})
        raise
