# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .models import IGNORE_DIRS


@contextmanager
def materialized_workspace(root: Path, case: dict[str, Any]) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="agent-memory-benchmark-") as directory:
        workspace = Path(directory) / "workspace"
        revision = str(case.get("source", {}).get("before_revision") or "working-tree")
        if revision != "working-tree" and git_archive(root, revision, workspace):
            pass
        else:
            copy_working_tree(root, workspace)
        mutation = case.get("source", {}).get("mutation")
        if isinstance(mutation, dict):
            apply_mutation(workspace, mutation)
        yield workspace


def git_archive(root: Path, revision: str, workspace: Path) -> bool:
    archive = workspace.parent / "source.tar"
    process = subprocess.run(
        ["git", "archive", "--format=tar", f"--output={archive}", revision],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        return False
    workspace.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as handle:
        members = handle.getmembers()
        for member in members:
            target = (workspace / member.name).resolve()
            if workspace.resolve() not in target.parents and target != workspace.resolve():
                raise SystemExit("unsafe path in Git archive")
            if member.issym() or member.islnk():
                link_base = workspace if member.islnk() else target.parent
                link_target = (link_base / member.linkname).resolve()
                if workspace.resolve() not in link_target.parents and link_target != workspace.resolve():
                    raise SystemExit("unsafe link in Git archive")
        handle.extractall(workspace)
    return True


def copy_working_tree(root: Path, workspace: Path) -> None:
    shutil.copytree(
        root,
        workspace,
        ignore=shutil.ignore_patterns(*sorted(IGNORE_DIRS)),
        symlinks=True,
    )


def apply_mutation(workspace: Path, mutation: dict[str, Any]) -> None:
    relative = safe_relative_path(str(mutation.get("file_path") or ""))
    path = workspace / relative
    if not path.is_file():
        raise SystemExit(f"mutation source file not found: {relative}")
    text = path.read_text(encoding="utf-8")
    expected_digest = str(mutation.get("source_digest") or "")
    actual_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if expected_digest and expected_digest != actual_digest:
        raise SystemExit(f"mutation source digest mismatch: {relative}")
    original = str(mutation.get("original") or "")
    replacement = str(mutation.get("replacement") or "")
    occurrence = max(1, int(mutation.get("occurrence") or 1))
    start = nth_occurrence(text, original, occurrence)
    if start < 0:
        raise SystemExit(f"mutation target not found: {relative}")
    changed = text[:start] + replacement + text[start + len(original):]
    path.write_text(changed, encoding="utf-8")


def nth_occurrence(text: str, needle: str, occurrence: int) -> int:
    if not needle:
        return -1
    start = -1
    for _ in range(occurrence):
        start = text.find(needle, start + 1)
        if start < 0:
            break
    return start


def safe_relative_path(value: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"unsafe benchmark source path: {value}")
    return path
