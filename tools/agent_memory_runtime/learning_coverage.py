# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Shared, deterministic reasons for source selection and indexing skips."""
from __future__ import annotations

from pathlib import Path

from .code_wiki_extractors import language_for, should_skip_dir
from .models import Project


def source_skip_reason(project: Project, path: Path) -> str | None:
    try:
        relative = path.relative_to(project.root)
        path.resolve().relative_to(project.root)
    except ValueError:
        return "outside_source_root"
    if should_skip_dir(relative):
        return "ignored_directory"
    if not path.exists():
        return "missing_path"
    if not path.is_file():
        return "not_regular_file"
    if not language_for(path):
        return "unsupported_extension"
    return None


def record_skip(counts: dict[str, int] | None, reason: str) -> None:
    if counts is not None:
        counts[reason] = counts.get(reason, 0) + 1


def require_learning_target(project: Project, target: Path) -> None:
    """Reject an explicitly selected unusable target before destructive replacement."""
    if target.is_dir():
        reason = "ignored_directory" if should_skip_dir(target.relative_to(project.root)) else None
    else:
        reason = source_skip_reason(project, target)
    if reason:
        raise SystemExit(f"cannot learn {target}: {reason}")


def require_indexable_replacement(
    file_count: int, replace: bool, skipped_by_reason: dict[str, int],
) -> None:
    if replace and skipped_by_reason.get("unreadable_directory", 0):
        raise SystemExit("cannot replace index: source scan incomplete; "
                         f"unreadable_directory={skipped_by_reason['unreadable_directory']}")
    if replace and file_count == 0 and skipped_by_reason:
        reasons = ", ".join(f"{key}={value}" for key, value in sorted(skipped_by_reason.items()))
        raise SystemExit(f"cannot replace index: no indexable files selected; skipped: {reasons}")
