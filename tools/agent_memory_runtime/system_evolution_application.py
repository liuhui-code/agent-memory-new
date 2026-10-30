# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .models import Project
from .system_evolution_acceptance import acceptance_observation
from .system_evolution_candidate_git import changed_file, file_bytes, git_success
from .system_evolution_contract import SystemEvolutionError, canonical_json, require
from .system_evolution_lifecycle_store import (
    change_context, finish_operation, lifecycle_result, operation_by_key, operation_view, reserve_operation,
)
from .system_evolution_store import registry_connection


LOCK_NAME = ".agent-memory-system.lock"


@contextmanager
def target_lock(root: Path) -> Iterator[None]:
    require(os.name == "posix", "This file-application lock requires POSIX.", "application_platform_unsupported")
    import fcntl
    path = root / LOCK_NAME
    descriptor = os.open(str(path), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), "Application lock is not a regular file.", "application_lock_invalid")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SystemEvolutionError("application_in_progress", "Another Runtime still holds the target application lock.") from error
        yield
    finally:
        os.close(descriptor)


def base_file(candidate: dict[str, Any], relative: str) -> dict[str, Any]:
    binding = candidate["binding"]
    root, executable = Path(binding["root"]), binding["git_executable"]
    raw = git_success(executable, root, ["--literal-pathspecs", "ls-tree", "-z", binding["base_tree"], "--", relative], capture=True)
    if not raw:
        return {"path": relative, "kind": "absent", "bytes": 0, "digest": None, "executable": None}
    header, name = raw.rstrip(b"\0").split(b"\t", 1)
    mode, kind, oid = header.split()
    require(name.decode("utf-8") == relative and kind == b"blob" and mode in {b"100644", b"100755", b"120000"},
            "Unsupported base file kind.", "application_path_unsupported")
    material = git_success(executable, root, ["cat-file", "blob", oid.decode("ascii")], capture=True, output_limit=16_777_216)
    return {"path": relative, "kind": "symlink" if mode == b"120000" else "file", "bytes": len(material),
            "digest": hashlib.sha256(material).hexdigest(), "executable": None if mode == b"120000" else mode == b"100755"}


def material(root: Path, item: dict[str, Any]) -> bytes:
    if item["kind"] == "absent":
        return b""
    path = root / item["path"]
    if item["kind"] == "symlink":
        raw = os.fsencode(os.readlink(path))
    else:
        descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as handle:
            raw = handle.read(16_777_217)
    require(len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["digest"],
            "Material changed during capture.", "application_binding_changed")
    return raw


def safe_target(project: Project, supplied: str, paths: list[str]) -> Path:
    root = Path(supplied).expanduser().resolve(strict=True)
    require(root.is_dir(), "Application target is not a directory.", "invalid_application_target")
    memory_home = project.memory_home.resolve()
    for name in paths:
        path = Path(name)
        require(not path.is_absolute() and ".." not in path.parts and ".git" not in path.parts
                and ".agent-memory" not in path.parts and path.name != LOCK_NAME
                and path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"},
                "Application changes code/rules only; use a versioned migration for archive data.", "application_path_unsupported")
        target = root / path
        require(target != memory_home and memory_home not in target.parents,
                "Application must not overwrite Memory Home.", "invalid_application_target")
        changed_file(root, name)  # Reject special files and symlink ancestors before any write.
    return root


@contextmanager
def parent_handle(root: Path, relative: str) -> Iterator[tuple[int, str]]:
    parts = Path(relative).parts
    descriptor = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            try:
                os.mkdir(part, mode=0o755, dir_fd=descriptor)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor, parts[-1]
    finally:
        os.close(descriptor)


def replace_file(root: Path, desired: dict[str, Any], raw: bytes, permissions: int | None = None) -> None:
    with parent_handle(root, desired["path"]) as (parent, name):
        if desired["kind"] == "absent":
            try:
                os.unlink(name, dir_fd=parent)
            except FileNotFoundError:
                pass
        else:
            temporary = ".memory-apply-" + os.urandom(12).hex()
            try:
                if desired["kind"] == "symlink":
                    os.symlink(os.fsdecode(raw), temporary, dir_fd=parent)
                else:
                    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                    with os.fdopen(descriptor, "wb") as handle:
                        handle.write(raw)
                        handle.flush()
                        os.fchmod(handle.fileno(), permissions if permissions is not None else (0o755 if desired["executable"] else 0o644))
                        os.fsync(handle.fileno())
                os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
            finally:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    pass
        os.fsync(parent)


def application_snapshot(root: Path, before: list[dict[str, Any]], after: list[dict[str, Any]]) -> None:
    for old, new in zip(before, after):
        require(changed_file(root, old["path"]) in (old, new),
                "Target has an unexpected edit; preserve it and resolve the conflict.", "application_target_conflict")


def capture_journal(project: Project, operation: dict[str, Any]) -> dict[str, Any]:
    request = operation["request"]
    recovery = Path(request["recovery_root"])
    before, after = request["before_files"], request["after_files"]
    target = Path(request["target_root"])
    require(all(changed_file(target, item["path"]) == item for item in before),
            "Target changed before its rollback material was captured.", "application_target_conflict")
    source = Path(request["candidate"]["binding"]["root"])
    for index, (old, new) in enumerate(zip(before, after)):
        for label, root, item in (("before", target, old), ("after", source, new)):
            source_item = {**item, "path": request["source_paths"][index]} if label == "after" else item
            raw = material(root, source_item)
            path = recovery / f"{label}-{index}"
            with path.open("wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
    journal = {"schema_version": "system-application-journal/v1", "target_root": str(target),
               "before_files": before, "after_files": after,
               "before_modes": request["before_modes"], "after_modes": request["after_modes"]}
    raw = canonical_json(journal).encode("utf-8")
    require(len(raw) <= 2_097_152, "Application journal exceeds its metadata budget.", "application_journal_limit")
    with (recovery / "journal.json").open("wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    descriptor = os.open(str(recovery), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    receipt = {"journal_digest": hashlib.sha256(raw).hexdigest(), "recovery_root": str(recovery),
               "completed_paths": [], "phase": "journal_ready", "atomicity": "per_file", "data_restore_performed": False}
    return finish_operation(project, operation, receipt, state="running")


def perform_application(project: Project, operation: dict[str, Any]) -> dict[str, Any]:
    request = operation["request"]
    root = safe_target(project, request["target_root"], [item["path"] for item in request["after_files"]])
    recovery = Path(request["recovery_root"]).resolve(strict=True)
    if not operation["receipt"].get("journal_digest"):
        require(operation["kind"] == "apply", "Rollback journal is missing.", "application_journal_missing")
        operation = capture_journal(project, operation)
    receipt = dict(operation["receipt"])
    raw_journal = file_bytes(recovery / "journal.json", 2_097_152)
    require(hashlib.sha256(raw_journal).hexdigest() == receipt["journal_digest"], "Recovery journal changed.", "application_journal_changed")
    journal = json.loads(raw_journal)
    require(journal["target_root"] == str(root) and journal["before_files"] == request["before_files"]
            and journal["after_files"] == request["after_files"] and journal["before_modes"] == request["before_modes"]
            and journal["after_modes"] == request["after_modes"], "Journal has another subject.", "application_journal_changed")
    before, after = request["before_files"], request["after_files"]
    application_snapshot(root, before, after)
    rollback = operation["kind"] == "rollback"
    receipt["completed_paths"] = []
    try:
        for index, (old, new) in enumerate(zip(before, after)):
            desired, original = (old, new) if rollback else (new, old)
            modes = request["before_modes"] if rollback else request["after_modes"]
            opposite_modes = request["after_modes"] if rollback else request["before_modes"]
            current = changed_file(root, desired["path"])
            require(current in (desired, original), "Target changed during application.", "application_target_conflict")
            if current["kind"] == "file":
                expected_mode = modes.get(current["path"]) if current == desired else opposite_modes.get(current["path"])
                require(stat.S_IMODE((root / current["path"]).stat().st_mode) == expected_mode,
                        "Target permissions changed.", "application_target_conflict")
            if current != desired:
                raw = file_bytes(recovery / f"{'before' if rollback else 'after'}-{index}", 16_777_216)
                require((desired["kind"] == "absent" and not raw) or
                        (len(raw) == desired["bytes"] and hashlib.sha256(raw).hexdigest() == desired["digest"]),
                        "Captured application material changed.", "application_journal_changed")
                replace_file(root, desired, raw, modes.get(desired["path"]))
            receipt["completed_paths"].append(desired["path"])
            receipt["phase"] = "writing"
            operation = finish_operation(project, operation, receipt, state="running")
        desired_files = before if rollback else after
        require(all(changed_file(root, item["path"]) == item for item in desired_files), "Target verification failed.", "application_binding_changed")
        receipt.update(phase="complete", files_verified=True, code_rollback_performed=rollback,
                       candidate_digest=request["candidate"]["candidate_digest"])
        return lifecycle_result(finish_operation(project, operation, receipt, proposal_state="rolled_back" if rollback else "applied"))
    except BaseException:
        receipt["phase"] = "interrupted"
        finish_operation(project, operation, receipt, state="interrupted")
        raise


def apply_change(project: Project, proposal_id: int, revision: int, key: str, target_root: str,
                 recovery_home: str, execute: bool = False, layout: str = "source") -> dict[str, Any]:
    require(layout in {"source", "installed"}, "Unknown application layout.", "invalid_request")
    call = {"proposal_id": proposal_id, "expected_revision": revision, "kind": "apply", "target_root": target_root,
            "recovery_home": recovery_home, "layout": layout}
    change, previous = change_context(project, proposal_id, key, call)
    if previous:
        require(previous["state"] in {"completed", "failed"}, "Application is unresolved; use explicit resume.", "operation_in_progress")
        return lifecycle_result(previous, True)
    require(change["state"] == "checked" and change["state_revision"] == revision, "Apply only the current checked revision.", "state_conflict")
    with registry_connection(project) as conn:
        row = conn.execute("SELECT * FROM system_change_operations WHERE project_id=? AND proposal_id=? AND kind='accept' AND state='completed' ORDER BY id DESC LIMIT 1",
                           (project.project_id, proposal_id)).fetchone()
        require(row is not None, "No completed acceptance record exists.", "acceptance_run_missing")
        acceptance = operation_view(row)
    require(acceptance["request"]["call"]["expected_revision"] + 1 == revision, "Acceptance revision is stale.", "state_conflict")
    prepared = {**change, "state_revision": revision - 1}
    observation = acceptance_observation(project, prepared, acceptance["request"]["call"]["acceptance_file"], acceptance["request"]["call"]["review_file"])
    require(observation == acceptance["receipt"], "Accepted inputs changed; check the new revision.", "check_binding_mismatch")
    candidate = observation["candidate"]
    after, before, source_paths, skipped = [], [], [], []
    skill_names = {"agent-memory-query", "agent-memory-learn", "agent-memory-reflect", "agent-memory-maintain"}
    for item in candidate["binding"]["changed_files"]:
        name = item["path"]
        parts = Path(name).parts
        mapped = name
        if layout == "installed":
            if len(parts) >= 3 and parts[0] == "skills" and parts[1] in skill_names:
                mapped = ".agents/" + name
            elif name == "tools/agent_memory.py" or name.startswith("tools/agent_memory_runtime/"):
                pass
            else:
                skipped.append(name)
                continue
        source_paths.append(name)
        after.append({**item, "path": mapped})
        before.append({**base_file(candidate, name), "path": mapped})
    require(bool(after), "Candidate has no files in the declared delivery layout.", "application_payload_empty")
    require(sum(item["bytes"] for item in before) <= 268_435_456,
            "Rollback preimages exceed the 256 MiB capture budget.", "application_observation_limit")
    target = safe_target(project, target_root, [item["path"] for item in after])
    require(target != Path(candidate["binding"]["root"]), "Apply to a distinct target, not the checked candidate.", "invalid_application_target")
    require(all(changed_file(target, item["path"]) == item for item in before), "Target does not match the declared base files.", "application_target_conflict")
    home = Path(recovery_home).expanduser().resolve(strict=True)
    require(home.is_dir() and home != target and target not in home.parents
            and home != project.memory_home.resolve() and project.memory_home.resolve() not in home.parents,
            "Choose an existing recovery directory outside target and Memory Home.", "invalid_recovery_home")
    request = {"call": call, "target_root": str(target), "candidate": candidate, "before_files": before, "after_files": after,
               "acceptance_key": acceptance["operation_key"], "source_paths": source_paths,
               "delivery_layout": layout, "skipped_delivery_paths": skipped}
    before_modes, after_modes = {}, {}
    for old, new in zip(before, after):
        permission = stat.S_IMODE((target / old["path"]).stat().st_mode) if old["kind"] == "file" else None
        require(permission is None or not permission & 0o7000, "Privileged file modes are unsupported.", "application_path_unsupported")
        if permission is not None:
            before_modes[old["path"]] = permission
        if new["kind"] == "file":
            mode = 0o755 if new["executable"] else 0o644
            if permission is not None:
                if new["executable"] == old["executable"]:
                    mode = permission
                else:
                    mode = permission | ((permission & 0o444) >> 2) if new["executable"] else permission & ~0o111
            after_modes[new["path"]] = mode
    request.update(before_modes=before_modes, after_modes=after_modes)
    if not execute:
        return {"schema_version": "system-change-application-preview/v1", "request": request, "application_performed": False}
    with target_lock(target):
        request["recovery_root"] = tempfile.mkdtemp(prefix="system-application-", dir=home)
        descriptor = os.open(str(home), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        operation = reserve_operation(project, change, key, "apply", request, {"phase": "capture_pending"})
        return perform_application(project, operation)


def resume_application(project: Project, key: str, execute: bool = False) -> dict[str, Any]:
    with registry_connection(project) as conn:
        operation = operation_by_key(conn, project.project_id, key)
    require(operation is not None and operation["kind"] in {"apply", "rollback"}, "Application operation not found.", "not_found")
    if operation["state"] == "completed":
        return lifecycle_result(operation, True)
    require(operation["state"] in {"running", "interrupted"}, "Operation cannot resume.", "operation_state_conflict")
    request = operation["request"]
    root = safe_target(project, request["target_root"], [item["path"] for item in request["after_files"]])
    application_snapshot(root, request["before_files"], request["after_files"])
    if not execute:
        return {"schema_version": "system-change-resume-preview/v1", "operation": operation, "application_performed": False}
    with target_lock(root):
        return perform_application(project, operation)


def rollback_change(project: Project, proposal_id: int, revision: int, key: str, application_key: str, execute: bool = False) -> dict[str, Any]:
    call = {"proposal_id": proposal_id, "expected_revision": revision, "kind": "rollback", "application_key": application_key}
    change, previous = change_context(project, proposal_id, key, call)
    if previous:
        require(previous["state"] == "completed", "Rollback is unresolved; use explicit resume.", "operation_in_progress")
        return lifecycle_result(previous, True)
    require(change["state"] in {"applied", "monitoring", "closed"} and change["state_revision"] == revision,
            "Rollback needs the current applied version.", "state_conflict")
    with registry_connection(project) as conn:
        application = operation_by_key(conn, project.project_id, application_key)
    require(application is not None and application["kind"] == "apply" and application["state"] == "completed"
            and application["proposal_id"] == proposal_id, "Completed application record not found.", "not_found")
    request = {**application["request"], "call": call}
    root = safe_target(project, request["target_root"], [item["path"] for item in request["after_files"]])
    application_snapshot(root, request["before_files"], request["after_files"])
    if not execute:
        return {"schema_version": "system-change-rollback-preview/v1", "request": request, "application_performed": False}
    with target_lock(root):
        operation = reserve_operation(project, change, key, "rollback", request, application["receipt"])
        return perform_application(project, operation)
