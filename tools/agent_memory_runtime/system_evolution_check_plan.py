# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .storage import now_iso
from .system_evolution_candidate_git import observe_candidate
from .system_evolution_contract import (
    SystemEvolutionError, canonical_json, content_digest, identifier, items,
    object_fields, require, text_field, unique_object_keys,
)
from .system_evolution_store import artifact_identity_digest, artifact_manifest


MAX_PLAN_BYTES = 32768
MAX_FILE_BYTES = 1_048_576
DIGEST_RE = re.compile(r"[0-9a-f]{64}")


def contained_path(root: Path, supplied: str) -> Path:
    path = Path(supplied)
    require(not path.is_absolute() and ".." not in path.parts,
            "Bound file paths must be relative and contained.", "invalid_check_plan")
    resolved = (root / path).resolve(strict=True)
    resolved.relative_to(root)
    require(resolved.is_file(), "A bound file is not a regular file.", "check_binding_unavailable")
    return resolved


def read_bounded_file(path: Path, limit: int) -> bytes:
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    require(len(raw) <= limit, "A bound file exceeds its observation limit.", "check_binding_unavailable")
    return raw


def load_check_plan(path: str, root: Path, proposal_id: int, revision: int,
                    assertion_count: int) -> dict[str, Any]:
    try:
        supplied = Path(path).expanduser().resolve(strict=True)
        supplied.relative_to(root)
        require(supplied.is_file(), "Check plan must be a regular file.")
        raw = read_bounded_file(supplied, MAX_PLAN_BYTES)
        plan = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object_keys)
        validate_check_plan(plan, proposal_id, revision, assertion_count)
        return plan
    except (OSError, ValueError, RuntimeError, RecursionError) as error:
        if isinstance(error, SystemEvolutionError) and error.code == "invalid_check_plan":
            raise
        raise SystemEvolutionError("invalid_check_plan", "Cannot load a valid bounded check plan inside the development root.") from error


def validate_check_plan(plan: Any, proposal_id: int, revision: int, assertion_count: int) -> None:
    require(isinstance(plan, dict), "Check plan must be an object.")
    require(plan.get("schema_version") in ("system-change-check-plan/v1", "system-change-check-plan/v2", "system-change-check-plan/v3"), "Unsupported check plan format.")
    is_candidate = plan["schema_version"] != "system-change-check-plan/v1"
    fields = {"schema_version", "proposal_id", "prepared_state_revision", "artifact_digest", "source_files", "checks"}
    if is_candidate:
        fields |= {"candidate_key", "candidate_digest"}
    object_fields(plan, fields, fields, "check plan")
    if is_candidate:
        identifier(plan["candidate_key"], "candidate_key")
        require(isinstance(plan["candidate_digest"], str) and bool(DIGEST_RE.fullmatch(plan["candidate_digest"])), "Invalid candidate digest.")
    require(type(plan["proposal_id"]) is int and plan["proposal_id"] == proposal_id
            and type(plan["prepared_state_revision"]) is int and plan["prepared_state_revision"] == revision,
            "Check plan must bind the requested proposal and revision.")
    require(isinstance(plan["artifact_digest"], str) and bool(DIGEST_RE.fullmatch(plan["artifact_digest"])),
            "Check plan needs an artifact identity digest.")
    files = items(plan["source_files"], "source_files", 100)
    require(bool(files), "Declare at least one source file.")
    names: set[str] = set()
    for bound in files:
        object_fields(bound, {"path", "digest"}, {"path", "digest"}, "source file")
        text_field(bound["path"], "source path", 500)
        require("\n" not in bound["path"] and "\t" not in bound["path"] and bound["path"] not in names,
                "Source paths must be distinct single-line paths.")
        require(isinstance(bound["digest"], str) and bool(DIGEST_RE.fullmatch(bound["digest"])), "Invalid source digest.")
        names.add(bound["path"])
    checks = items(plan["checks"], "checks", 5)
    require(bool(checks), "Declare at least one check.")
    keys: set[str] = set()
    coverage: set[int] = set()
    timeout_total = 0
    output_names: set[str] = set()
    for check in checks:
        fields = {"key", "argv", "assertion_indices", "timeout_seconds"}
        if plan["schema_version"] == "system-change-check-plan/v3":
            fields.add("result_files")
        object_fields(check, fields, fields, "check")
        if "result_files" in check:
            outputs = items(check["result_files"], "result_files", 10)
            require(bool(outputs), "Declare a result file for a v3 check.")
            for name in outputs:
                text_field(name, "result file", 500)
                require(not Path(name).is_absolute() and ".." not in Path(name).parts
                        and "\n" not in name and "\t" not in name and name not in output_names,
                        "Result paths must be distinct contained relative paths.")
                output_names.add(name)
        key = identifier(check["key"], "check key")
        require(key not in keys, "Check keys must be distinct.")
        keys.add(key)
        argv = items(check["argv"], "argv", 64)
        require(bool(argv), "A check needs an executable.")
        for argument in argv:
            text_field(argument, "argv item", 1000)
        executable = Path(argv[0])
        require(executable.is_absolute(), "Use an absolute executable path.")
        require(os.name != "nt" or executable.suffix.lower() not in {".cmd", ".bat"}, "Batch shell execution is unsupported.")
        indices = items(check["assertion_indices"], "assertion_indices", 5)
        require(bool(indices) and all(type(index) is int and 0 <= index < assertion_count for index in indices)
                and len(set(indices)) == len(indices), "Invalid assertion mapping.")
        coverage.update(indices)
        timeout = check["timeout_seconds"]
        require(type(timeout) is int and 1 <= timeout <= 300, "Each check timeout must be between 1 and 300 seconds.")
        timeout_total += timeout
    require(coverage == set(range(assertion_count)), "Declare check mappings for every proposal assertion.")
    require(timeout_total <= 600, "Combined check timeout exceeds 600 seconds.")
    require(len(canonical_json(plan).encode("utf-8")) <= MAX_PLAN_BYTES, "Canonical check plan is too large.")


def require_executables(plan: dict[str, Any]) -> None:
    for check in plan["checks"]:
        executable = Path(check["argv"][0])
        require(executable.is_file() and os.access(executable, os.X_OK),
                "A planned executable is unavailable.", "invalid_check_plan")


def plan_summary(plan: dict[str, Any], manifest: dict[str, Any], candidate: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "artifact_manifest": manifest, "source_files": plan["source_files"],
        "plan_format": plan["schema_version"],
        "assertion_mapping": "caller_declared", "scope": "candidate_and_declared_files" if candidate else "declared_files_only",
        "candidate": candidate,
        "checks": [{"key": check["key"], "argv_digest": content_digest(canonical_json(check["argv"])),
                    "assertion_indices": check["assertion_indices"], "timeout_seconds": check["timeout_seconds"],
                    **({"result_files": check["result_files"]} if "result_files" in check else {})}
                   for check in plan["checks"]],
    }


def observe_binding(plan: dict[str, Any], manifest: dict[str, Any], candidate: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        root = Path(manifest["development_root"]).resolve(strict=True)
        actual = artifact_manifest(str(root), [item["path"] for item in manifest["artifacts"]], manifest["base_version"])
        digest = artifact_identity_digest(actual)
        mismatches = [] if digest == plan["artifact_digest"] else [{"kind": "artifact"}]
        candidate_observation = None
        if plan["schema_version"] != "system-change-check-plan/v1":
            require(candidate is not None and candidate["candidate_key"] == plan["candidate_key"]
                    and candidate["candidate_digest"] == plan["candidate_digest"], "Candidate binding is missing.", "candidate_binding_changed")
            candidate_observation = observe_candidate(candidate)
            if not candidate_observation["matches"]:
                mismatches.append({"kind": "candidate"})
            root = Path(candidate["binding"]["root"])
        observed = []
        paths: set[Path] = set()
        for bound in plan["source_files"]:
            path = contained_path(root, bound["path"])
            require(path not in paths, "Source paths alias the same file.", "invalid_check_plan")
            paths.add(path)
            raw = read_bounded_file(path, MAX_FILE_BYTES)
            actual_digest = hashlib.sha256(raw).hexdigest()
            observed.append({"path": bound["path"], "bytes": len(raw), "digest": actual_digest})
            if actual_digest != bound["digest"]:
                mismatches.append({"kind": "source", "path": bound["path"]})
        return {"artifact_digest": digest, "source_files": observed, "matches": not mismatches,
                "candidate": candidate_observation, "mismatches": mismatches, "observed_at": now_iso(),
                "scope": "candidate_and_declared_files" if candidate else "declared_files_only"}
    except (OSError, ValueError, RuntimeError) as error:
        if isinstance(error, SystemEvolutionError):
            raise
        raise SystemEvolutionError("check_binding_unavailable", "Cannot observe declared files inside the development root.") from error


def observe_outputs(check: dict[str, Any], root: Path, before: bool = False) -> list[dict[str, Any]]:
    observations = []
    seen: set[Path] = set()
    try:
        for name in check.get("result_files", []):
            path = (root / name).resolve()
            path.relative_to(root)
            require(path not in seen, "Result paths alias the same file.", "check_output_alias")
            seen.add(path)
            if before:
                require(not path.exists() and not path.is_symlink(), "Check result file already exists; use a fresh declared path.", "check_output_exists")
            else:
                require(path.is_file(), "Check did not create a declared result file.", "check_output_unavailable")
                raw = read_bounded_file(path, MAX_FILE_BYTES)
                observations.append({"path": name, "bytes": len(raw), "digest": hashlib.sha256(raw).hexdigest()})
        return observations
    except (OSError, ValueError, RuntimeError) as error:
        if isinstance(error, SystemEvolutionError):
            raise
        raise SystemEvolutionError("check_output_unavailable", "Cannot observe a declared result inside the candidate.") from error
