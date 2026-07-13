# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import Any

from .code_wiki_followup import semantic_followup_from_db
from .code_wiki_imports import collect_entry_related_files, collect_path_files, resolve_target
from .code_wiki_indexing import build_file_snapshot, load_learn_scopes, parse_stats_summary, write_wiki_scope
from .models import Project
from .records import output
from .semantic_refresh import load_refresh_semantic_snapshot, record_refresh_semantic_conflicts
from .storage import connect, ensure_initialized, now_iso, resolve_project

def add_episode_from_values(project: Project, task: str, summary: str, outcome: str | None) -> None:
    with connect(project) as conn:
        conn.execute(
            """
            INSERT INTO episodes(project_id, task, summary, outcome, files_touched, commands_run, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (project.project_id, task, summary, outcome, None, None, now_iso()),
        )
        conn.commit()



def compare_scope_snapshots(
    previous: dict[str, str],
    current: dict[str, str],
) -> tuple[list[str], list[str], list[str], int]:
    previous_paths = set(previous)
    current_paths = set(current)
    added = sorted(current_paths - previous_paths)
    removed = sorted(previous_paths - current_paths)
    changed = sorted(
        path for path in (previous_paths & current_paths) if previous.get(path) != current.get(path)
    )
    unchanged_count = sum(
        1 for path in (previous_paths & current_paths) if previous.get(path) == current.get(path)
    )
    return added, removed, changed, unchanged_count



def files_for_scope(source_project: Project, scope_row: sqlite3.Row) -> list[Path]:
    scope_type = scope_row["scope_type"]
    if scope_type == "project":
        return collect_project_files(source_project)
    if scope_type == "path":
        target_path = str(scope_row["target_path"] or ".")
        target = resolve_target(source_project, target_path)
        return collect_path_files(source_project, target)
    if scope_type == "entry":
        entry_path = str(scope_row["entry_path"] or "").strip()
        if not entry_path:
            raise SystemExit(f"learn scope {scope_row['id']} is missing entry_path")
        entry = resolve_target(source_project, entry_path)
        if not entry.is_file():
            raise SystemExit(f"learn scope entry no longer exists as file: {entry}")
        depth = int(scope_row["depth"] or 2)
        return collect_entry_related_files(source_project, entry, depth)
    raise SystemExit(f"unsupported learn scope type: {scope_type}")



def semantic_review_targets_from_drift(
    added_files: list[str],
    changed_files: list[str],
    removed_files: list[str],
) -> dict[str, Any]:
    affected: list[str] = []
    seen: set[str] = set()
    for value in [*changed_files, *added_files, *removed_files]:
        stripped = str(value).strip()
        normalized = stripped.lower()
        if not stripped or normalized in seen:
            continue
        seen.add(normalized)
        affected.append(stripped)
    return {
        "drift_detected": bool(affected),
        "refresh_semantic_scope": bool(changed_files or added_files),
        "retire_removed_scope": bool(removed_files),
        "file_paths": affected,
    }



def update_scope_refresh_record(
    project: Project,
    scope_row: sqlite3.Row,
    current_snapshot: dict[str, str],
    refresh_summary: dict[str, Any],
) -> None:
    ts = now_iso()
    with connect(project) as conn:
        conn.execute(
            """
            UPDATE learn_scopes
            SET file_snapshot = ?, file_count = ?, updated_at = ?, last_refreshed_at = ?, last_refresh_summary = ?
            WHERE project_id = ? AND id = ?
            """,
            (
                json.dumps(current_snapshot, ensure_ascii=False, sort_keys=True),
                len(current_snapshot),
                ts,
                ts,
                json.dumps(refresh_summary, ensure_ascii=False, sort_keys=True),
                project.project_id,
                scope_row["id"],
            ),
        )
        conn.commit()



def maintain_refresh_scope(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    scope_rows = load_learn_scopes(project, args.scope_id)
    if args.scope_id is not None and not scope_rows:
        raise SystemExit(f"learn scope not found: {args.scope_id}")

    refreshed: list[dict[str, Any]] = []
    for scope_row in scope_rows:
        source_root = Path(scope_row["source_root"]).expanduser().resolve()
        result: dict[str, Any] = {
            "scope_id": scope_row["id"],
            "scope_type": scope_row["scope_type"],
            "source_root": str(source_root),
            "target_path": scope_row["target_path"],
            "entry_path": scope_row["entry_path"],
            "depth": scope_row["depth"],
            "mode": scope_row["mode"],
        }
        if not source_root.exists() or not source_root.is_dir():
            result["status"] = "missing_source"
            result["warning"] = f"source root no longer exists: {source_root}"
            refreshed.append(result)
            continue

        source_project = replace(project, root=source_root, project_name=source_root.name)
        files = files_for_scope(source_project, scope_row)
        current_snapshot = build_file_snapshot(source_project, files)
        previous_snapshot = json.loads(scope_row["file_snapshot"] or "{}")
        added_files, removed_files, changed_files, unchanged_count = compare_scope_snapshots(
            previous_snapshot,
            current_snapshot,
        )
        changed_only = bool(getattr(args, "changed_only", False))
        files_to_refresh = files
        if changed_only:
            changed_set = set(added_files) | set(changed_files)
            files_to_refresh = [
                path
                for path in files
                if str(path.relative_to(source_project.root)) in changed_set
            ]
        semantic_drift_before = load_refresh_semantic_snapshot(source_project, changed_files)
        if files_to_refresh or removed_files or not changed_only:
            stats = write_wiki_scope(
                source_project,
                files_to_refresh,
                replace=False,
                retired_relative_files=removed_files,
            )
        else:
            stats = {
                "files_indexed": 0,
                "symbols_indexed": 0,
                "code_logs_indexed": 0,
                "memory_edges_total": 0,
                "retired_files": [],
            }
        semantic_review_targets = semantic_review_targets_from_drift(
            added_files,
            changed_files,
            removed_files,
        )
        semantic_conflicts = record_refresh_semantic_conflicts(
            source_project,
            changed_files,
            semantic_drift_before,
        )
        refresh_summary = {
            "status": "refreshed",
            "added_files": added_files,
            "changed_files": changed_files,
            "removed_files": removed_files,
            "unchanged_count": unchanged_count,
            "semantic_review_targets": semantic_review_targets,
            "semantic_conflicts": semantic_conflicts,
            "changed_only": changed_only,
            "refreshed_files": sorted([*added_files, *changed_files]) if changed_only else sorted(current_snapshot),
        }
        update_scope_refresh_record(project, scope_row, current_snapshot, refresh_summary)
        summary = (
            f"Refreshed learn scope {scope_row['id']} ({scope_row['scope_type']}) "
            f"added={len(added_files)} changed={len(changed_files)} removed={len(removed_files)}"
        )
        add_episode_from_values(project, f"Refresh learn scope {scope_row['id']}", summary, "refreshed")
        result.update(
            {
                "status": "refreshed",
                "previous_file_count": len(previous_snapshot),
                "current_file_count": len(current_snapshot),
                "added_files": added_files,
                "changed_files": changed_files,
                "removed_files": removed_files,
                "unchanged_count": unchanged_count,
                "parse_stats": stats,
                "semantic_review_targets": semantic_review_targets,
                "semantic_conflicts": semantic_conflicts,
                "changed_only": changed_only,
                "refreshed_files": refresh_summary["refreshed_files"],
            }
        )
        refreshed.append(result)

    payload = {
        "scope_count": len(scope_rows),
        "refreshed_count": sum(1 for item in refreshed if item["status"] == "refreshed"),
        "missing_source_count": sum(1 for item in refreshed if item["status"] == "missing_source"),
        "scopes": refreshed,
    }
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_refresh_scope.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output(payload, args.json)
