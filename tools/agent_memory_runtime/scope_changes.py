# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .code_wiki_extractors import language_for, should_skip_dir
from .models import Project


MAX_INCREMENTAL_CANDIDATES = 200
MAX_ENTRY_PATHSPECS = 512
MAX_REPORTED_CANDIDATES = 50


@dataclass(frozen=True)
class ScopeChangeSet:
    provider: str
    baseline_revision: str | None
    current_revision: str | None
    candidate_paths: tuple[str, ...]
    scope_candidate_paths: tuple[str, ...] = ()
    boundary_candidate_paths: tuple[str, ...] = ()
    fallback_reason: str | None = None
    requires_snapshot_scan: bool = False
    overflow: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "scope-change-set/v1",
            "provider": self.provider,
            "baseline_revision": self.baseline_revision,
            "current_revision": self.current_revision,
            "candidate_file_count": len(self.candidate_paths),
            "candidate_paths": list(self.candidate_paths[:MAX_REPORTED_CANDIDATES]),
            "scope_candidate_paths": list(self.scope_candidate_paths[:MAX_REPORTED_CANDIDATES]),
            "boundary_candidate_paths": list(self.boundary_candidate_paths[:MAX_REPORTED_CANDIDATES]),
            "candidate_paths_truncated": len(self.candidate_paths) > MAX_REPORTED_CANDIDATES,
            "scope_filtered": True,
            "fallback_reason": self.fallback_reason,
            "requires_snapshot_scan": self.requires_snapshot_scan,
            "overflow": self.overflow,
            "candidate_limit": MAX_INCREMENTAL_CANDIDATES,
        }


class ScopeChangeProvider(Protocol):
    provider_id: str

    def detect(
        self,
        project: Project,
        scope: Any,
        previous_snapshot: dict[str, str],
        boundary_paths: set[str],
    ) -> ScopeChangeSet:
        ...


class GitScopeChangeProvider:
    provider_id = "git/v1"

    def detect(
        self,
        project: Project,
        scope: Any,
        previous_snapshot: dict[str, str],
        boundary_paths: set[str],
    ) -> ScopeChangeSet:
        baseline = scope_value(scope, "baseline_revision")
        current = git_head(project.root)
        if not current:
            return snapshot_change_set(None, "not_git", boundary_paths)
        if not baseline:
            return snapshot_change_set(current, "baseline_missing", boundary_paths)
        pathspecs = sorted(set(scope_pathspecs(scope, previous_snapshot)) | boundary_paths)
        if not pathspecs or len(pathspecs) > MAX_ENTRY_PATHSPECS:
            return snapshot_change_set(current, "pathspec_overflow", boundary_paths)
        try:
            tracked = git_changed_paths(project.root, baseline, pathspecs)
            untracked = git_untracked_paths(project.root, pathspecs)
            tracked_scope = git_tracked_paths(project.root, pathspecs)
        except GitChangeError:
            return snapshot_change_set(current, "git_query_failed", boundary_paths)
        known_paths = set(previous_snapshot) | boundary_paths
        learned_untracked = known_paths - tracked_scope
        candidates = eligible_paths(
            project.root,
            tracked | untracked | learned_untracked,
            known_paths,
        )
        boundary_candidates = sorted(set(candidates) & boundary_paths)
        scope_candidates = sorted(set(candidates) - boundary_paths)
        return ScopeChangeSet(
            provider=self.provider_id,
            baseline_revision=baseline,
            current_revision=current,
            candidate_paths=tuple(candidates),
            scope_candidate_paths=tuple(scope_candidates),
            boundary_candidate_paths=tuple(boundary_candidates),
            overflow=len(candidates) > MAX_INCREMENTAL_CANDIDATES,
        )


class SnapshotScopeChangeProvider:
    provider_id = "snapshot/v1"

    def detect(
        self,
        project: Project,
        scope: Any,
        previous_snapshot: dict[str, str],
        boundary_paths: set[str],
    ) -> ScopeChangeSet:
        return snapshot_change_set(git_head(project.root), "explicit_snapshot", boundary_paths)


def detect_scope_changes(
    project: Project,
    scope: Any,
    previous_snapshot: dict[str, str],
    boundary_paths: set[str] | None = None,
) -> ScopeChangeSet:
    return GitScopeChangeProvider().detect(
        project, scope, previous_snapshot, boundary_paths or set()
    )


def snapshot_change_set(
    current_revision: str | None,
    reason: str,
    boundary_paths: set[str],
) -> ScopeChangeSet:
    return ScopeChangeSet(
        provider="snapshot/v1",
        baseline_revision=None,
        current_revision=current_revision,
        candidate_paths=tuple(sorted(boundary_paths)),
        boundary_candidate_paths=tuple(sorted(boundary_paths)),
        fallback_reason=reason,
        requires_snapshot_scan=True,
    )


def git_head(root: Path) -> str | None:
    try:
        value = run_git(root, ["rev-parse", "--verify", "HEAD"])
    except GitChangeError:
        return None
    return value.decode("utf-8", errors="replace").strip() or None


def git_changed_paths(root: Path, baseline: str, pathspecs: list[str]) -> set[str]:
    raw = run_git(
        root,
        ["diff", "--relative", "--name-status", "-z", "-M", baseline, "--", *pathspecs],
    )
    return parse_name_status(raw)


def git_untracked_paths(root: Path, pathspecs: list[str]) -> set[str]:
    raw = run_git(
        root,
        ["ls-files", "--others", "--exclude-standard", "-z", "--", *pathspecs],
    )
    return {normalize_path(item) for item in raw.decode("utf-8", errors="replace").split("\0") if item}


def git_tracked_paths(root: Path, pathspecs: list[str]) -> set[str]:
    raw = run_git(root, ["ls-files", "-z", "--", *pathspecs])
    return {
        normalize_path(item)
        for item in raw.decode("utf-8", errors="replace").split("\0")
        if item
    }


def run_git(root: Path, args: list[str]) -> bytes:
    try:
        process = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GitChangeError(str(error)) from error
    if process.returncode != 0:
        raise GitChangeError(process.stderr.decode("utf-8", errors="replace"))
    return process.stdout


def parse_name_status(raw: bytes) -> set[str]:
    fields = raw.decode("utf-8", errors="replace").split("\0")
    paths: set[str] = set()
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        index += 1
        path_count = 2 if status[:1] in {"R", "C"} else 1
        for _unused in range(path_count):
            if index < len(fields) and fields[index]:
                paths.add(normalize_path(fields[index]))
            index += 1
    return paths


def scope_pathspecs(scope: Any, previous_snapshot: dict[str, str]) -> list[str]:
    scope_type = str(scope["scope_type"])
    if scope_type == "project":
        return ["."]
    if scope_type == "path":
        return [str(scope["target_path"] or ".")]
    if scope_type == "entry":
        entry = str(scope["entry_path"] or "").strip()
        return sorted(set(previous_snapshot) | ({entry} if entry else set()))
    return []


def eligible_paths(
    root: Path,
    candidates: set[str],
    known_paths: set[str],
) -> list[str]:
    eligible: list[str] = []
    for relative in sorted(candidates):
        path = root / relative
        if relative in known_paths:
            eligible.append(relative)
            continue
        if not safe_relative(root, path) or should_skip_dir(Path(relative)):
            continue
        if path.is_file() and language_for(path):
            eligible.append(relative)
    return eligible


def safe_relative(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def normalize_path(value: str) -> str:
    normalized = Path(value).as_posix()
    return normalized[2:] if normalized.startswith("./") else normalized


def scope_value(scope: Any, key: str) -> str | None:
    try:
        value = scope[key]
    except (KeyError, IndexError):
        return None
    text = str(value or "").strip()
    return text or None


class GitChangeError(RuntimeError):
    pass
