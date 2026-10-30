# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
from pathlib import Path
from threading import Event, Thread
from time import monotonic
from typing import Any

from .storage import now_iso
from .system_evolution_check_process import stop_process
from .system_evolution_contract import SystemEvolutionError, canonical_json, content_digest, require, text_field


OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


def bounded_output(process: subprocess.Popen, limit: int, timeout: int) -> bytes:
    output = bytearray()
    overflow, read_error = Event(), Event()

    def drain() -> None:
        try:
            while True:
                chunk = process.stdout.read(min(65536, limit + 1 - len(output)))
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > limit:
                    overflow.set()
                    break
        except Exception:
            read_error.set()

    reader = Thread(target=drain, daemon=True)
    reader.start()
    deadline = monotonic() + timeout
    try:
        while process.poll() is None:
            require(not overflow.is_set(), "Git metadata exceeds its byte limit.", "candidate_git_output_limit")
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(process.args, timeout)
            try:
                process.wait(timeout=min(0.1, remaining))
            except subprocess.TimeoutExpired:
                continue
        reader.join(timeout=1)
        require(not reader.is_alive() and not read_error.is_set(), "Git metadata pipe did not finish.", "candidate_git_invalid")
        require(not overflow.is_set(), "Git metadata exceeds its byte limit.", "candidate_git_output_limit")
        return bytes(output)
    finally:
        try:
            stop_process(process)
        finally:
            process.stdout.close()
            reader.join(timeout=1)


def git_command(executable: str, root: Path, args: list[str], *, capture: bool = False,
                timeout: int = 30, output_limit: int = 4096) -> tuple[int, bytes]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0",
               GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0")
    options = ["-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false",
               "-c", "core.autocrlf=false", "-c", "core.eol=lf", "-c", "gc.auto=0",
               "-c", "maintenance.auto=false", "-c", "protocol.allow=never", "-c", "protocol.file.allow=always"]
    process = None
    try:
        process = subprocess.Popen([executable, *options, "-C", str(root), *args], env=env, shell=False, bufsize=0,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=os.name == "posix")
        if capture:
            output = bounded_output(process, output_limit, timeout)
        else:
            process.wait(timeout=timeout)
            output = b""
        return process.returncode, output
    except subprocess.TimeoutExpired as error:
        raise SystemEvolutionError("candidate_git_timeout", "Candidate Git operation exceeded its declared timeout.") from error
    except OSError as error:
        raise SystemEvolutionError("candidate_git_unavailable", "Cannot execute the local candidate Git operation.") from error
    finally:
        if process is not None:
            if not capture or process.poll() is None:
                stop_process(process)
            if process.stdout is not None:
                process.stdout.close()


def git_success(executable: str, root: Path, args: list[str], **kwargs: Any) -> bytes:
    code, raw = git_command(executable, root, args, **kwargs)
    require(code == 0, "Candidate Git operation failed; inspect the retained candidate material.", "candidate_git_failed")
    return raw


def git_oid(executable: str, root: Path, args: list[str]) -> str:
    raw = git_success(executable, root, args, capture=True).decode("ascii").strip()
    require(bool(OID.fullmatch(raw)), "Git did not return one complete object identity.", "candidate_git_invalid")
    return raw


def validate_base(executable: str, root: Path, base: str) -> str:
    require(bool(OID.fullmatch(base)), "Prepared base_version must be a complete Git commit OID.", "invalid_candidate")
    actual_root = git_success(executable, root, ["rev-parse", "--show-toplevel"], capture=True).decode("utf-8").rstrip("\r\n")
    require(Path(actual_root).resolve() == root, "Development root must be the Git worktree root.", "invalid_candidate")
    actual = git_oid(executable, root, ["rev-parse", "--verify", f"{base}^{{commit}}"])
    require(actual == base, "Prepared base must identify a commit directly.", "invalid_candidate")
    return git_oid(executable, root, ["rev-parse", "--verify", f"{base}^{{tree}}"])


def file_bytes(path: Path, limit: int) -> bytes:
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    require(len(raw) <= limit, "Candidate material exceeds its byte limit.", "candidate_observation_limit")
    return raw


def changed_file(root: Path, relative: str) -> dict[str, Any]:
    path = Path(relative)
    text_field(relative, "changed path", 500)
    require(not path.is_absolute() and ".." not in path.parts and "\n" not in relative and "\t" not in relative,
            "Invalid candidate change path.", "candidate_path_invalid")
    parent = root
    for part in path.parts[:-1]:
        parent /= part
        require(not parent.is_symlink(), "Candidate change traverses a symbolic link.", "candidate_path_invalid")
    target = root / path
    try:
        metadata = target.lstat()
    except FileNotFoundError:
        return {"path": relative, "kind": "absent", "bytes": 0, "digest": None, "executable": None}
    if stat.S_ISLNK(metadata.st_mode):
        raw = os.fsencode(os.readlink(target))
        kind, executable = "symlink", None
    else:
        require(stat.S_ISREG(metadata.st_mode), "Candidate change is not a regular file or symlink.", "candidate_path_invalid")
        raw = file_bytes(target, 16_777_216)
        kind, executable = "file", bool(metadata.st_mode & 0o111)
    require(len(raw) <= 16_777_216, "Candidate link exceeds its byte limit.", "candidate_observation_limit")
    return {"path": relative, "kind": kind, "bytes": len(raw), "digest": hashlib.sha256(raw).hexdigest(), "executable": executable}


def changed_snapshot(root: Path, paths: list[str]) -> list[dict[str, Any]]:
    require(1 <= len(paths) <= 100 and len(paths) == len(set(paths)),
            "Candidate patch must change one to 100 distinct paths.", "candidate_observation_limit")
    result = []
    total = 0
    for path in sorted(paths):
        item = changed_file(root, path)
        total += item["bytes"]
        require(total <= 268_435_456, "Candidate changes exceed the 256 MiB observation budget.", "candidate_observation_limit")
        result.append(item)
    return result


def config_digest(root: Path) -> str:
    require((root / ".git").is_dir() and not (root / ".git").is_symlink(),
            "Candidate Git directory is unavailable or changed.", "candidate_binding_changed")
    path = root / ".git" / "config"
    require(not path.is_symlink(), "Candidate Git configuration is a symlink.", "candidate_binding_changed")
    return hashlib.sha256(file_bytes(path, 65536)).hexdigest()


def prepare_git_candidate(executable: str, source: Path, operation: Path, patch: bytes,
                          base: str, base_tree: str, artifact_digest: str) -> dict[str, Any]:
    started = monotonic()
    empty = operation / "empty-template"
    empty.mkdir(mode=0o700)
    patch_copy = operation / "candidate.patch"
    patch_copy.write_bytes(patch)
    root = operation / "source"
    git_success(executable, operation, ["clone", "--local", "--no-hardlinks", "--dissociate", "--no-checkout",
                "--quiet", f"--template={empty}", "--", str(source), str(root)], timeout=300)
    git_success(executable, root, ["checkout", "--detach", "--quiet", base], timeout=60)
    git_success(executable, root, ["apply", "--index", "--check", str(patch_copy)])
    git_success(executable, root, ["apply", "--index", str(patch_copy)])
    tree = git_oid(executable, root, ["write-tree"])
    require(tree != base_tree, "Candidate patch does not change the selected base tree.", "invalid_candidate")
    raw = git_success(executable, root, ["diff-tree", "--no-commit-id", "--raw", "--no-renames",
                      "-r", "-z", base_tree, tree, "--"], capture=True, output_limit=2_097_152)
    parts = raw.split(b"\0")
    require(parts[-1] == b"" and len(parts) % 2 == 1, "Invalid candidate change metadata.", "candidate_git_invalid")
    paths = []
    for index in range(0, len(parts) - 1, 2):
        header = parts[index].split()
        require(len(header) == 5 and header[0].startswith(b":"), "Invalid candidate change header.", "candidate_git_invalid")
        require(header[0][1:] != b"160000" and header[1] != b"160000",
                "Gitlink changes require a separate submodule contract.", "invalid_candidate")
        paths.append(parts[index + 1].decode("utf-8"))
    binding = {"root": str(root), "base_revision": base, "base_tree": base_tree, "candidate_tree": tree,
               "artifact_digest": artifact_digest, "git_executable": executable,
               "config_digest": config_digest(root), "changed_files": changed_snapshot(root, paths)}
    return {"binding": binding, "candidate_digest": content_digest(canonical_json(binding)),
            "elapsed_ms": round((monotonic() - started) * 1000, 3), "observed_at": now_iso(),
            "scope": "git_tracked_tree_and_changed_bytes", "environment_authenticated": False}


def observe_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    binding = candidate["binding"]
    root = Path(binding["root"])
    require(root.resolve(strict=True) == root and config_digest(root) == binding["config_digest"],
            "Candidate root or Git configuration changed.", "candidate_binding_changed")
    executable = binding["git_executable"]
    head = git_oid(executable, root, ["rev-parse", "--verify", "HEAD"])
    index, _ = git_command(executable, root, ["diff-index", "--cached", "--quiet", "--no-ext-diff", "--no-textconv",
                                           binding["candidate_tree"], "--"])
    worktree, _ = git_command(executable, root, ["diff-files", "--quiet", "--no-ext-diff", "--no-textconv", "--ignore-submodules=none", "--"])
    require(index in (0, 1) and worktree in (0, 1), "Candidate Git observation failed.", "candidate_git_failed")
    actual = {**binding, "changed_files": changed_snapshot(root, [item["path"] for item in binding["changed_files"]])}
    digest = content_digest(canonical_json(actual))
    return {"matches": head == binding["base_revision"] and index == worktree == 0 and digest == candidate["candidate_digest"],
            "head_matches": head == binding["base_revision"], "index_matches": index == 0, "worktree_matches": worktree == 0,
            "candidate_digest": digest, "candidate_tree": binding["candidate_tree"], "observed_at": now_iso(),
            "scope": "git_observation_and_changed_bytes", "environment_authenticated": False,
            "untracked_and_ignored_files_authenticated": False}
