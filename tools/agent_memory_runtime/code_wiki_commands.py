# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from typing import Any

from .code_wiki_followup import semantic_followup_from_db
from .code_wiki_imports import collect_entry_related_files, collect_path_files, collect_project_files, project_for_learning_source, resolve_target
from .code_wiki_indexing import record_learn_scope, write_wiki_index, parse_stats_summary
from .code_wiki_refresh import add_episode_from_values
from .query import collect_matches, record_query_miss_if_empty
from .records import output
from .storage import ensure_initialized, resolve_project

def wiki_index(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, args.source)
    files = collect_project_files(source_project)
    stats = write_wiki_index(source_project, files, replace=True)
    record_learn_scope(
        project,
        source_project.root,
        "project",
        "replace",
        files,
        target_path=".",
    )
    print(f"wiki index updated ({parse_stats_summary(stats)})")



def learn_path(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, args.source)
    target = resolve_target(source_project, args.path)
    files = collect_path_files(source_project, target)
    stats = write_wiki_index(source_project, files, replace=args.replace)
    rel_target = str(target.relative_to(source_project.root))
    scope_id = record_learn_scope(
        project,
        source_project.root,
        "path",
        "replace" if args.replace else "merge",
        files,
        target_path=rel_target,
    )
    task = f"Learn path {target.relative_to(source_project.root)} from {source_project.root}"
    mode = "replaced" if args.replace else "merged"
    summary = f"{mode.capitalize()} {len(files)} files from {target.relative_to(source_project.root)}"
    add_episode_from_values(project, task, summary, "learned")
    payload = {
        "source": str(source_project.root),
        "path": rel_target,
        "scope_id": scope_id,
        "mode": "replace" if args.replace else "merge",
        "files": [str(path.relative_to(source_project.root)) for path in sorted(files)],
        "count": len(files),
        "summary": summary,
        "parse_stats": stats,
    }
    semantic_followup = semantic_followup_from_db(source_project, payload["files"])
    if semantic_followup:
        payload["semantic_followup"] = semantic_followup
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_learn_path.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.json:
        output(payload, True)
    else:
        print(f"{summary} ({parse_stats_summary(stats)})")



def learn_entry(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, args.source)
    entry = resolve_target(source_project, args.entry)
    if not entry.is_file():
        raise SystemExit(f"entry must be a file: {entry}")
    files = collect_entry_related_files(source_project, entry, args.depth)
    stats = write_wiki_index(source_project, files, replace=args.replace)
    rel_files = [str(path.relative_to(source_project.root)) for path in sorted(files)]
    rel_entry = str(entry.relative_to(source_project.root))
    scope_id = record_learn_scope(
        project,
        source_project.root,
        "entry",
        "replace" if args.replace else "merge",
        files,
        entry_path=rel_entry,
        depth=args.depth,
    )
    payload = {
        "source": str(source_project.root),
        "entry": rel_entry,
        "scope_id": scope_id,
        "depth": args.depth,
        "mode": "replace" if args.replace else "merge",
        "files": rel_files,
        "count": len(rel_files),
        "parse_stats": stats,
    }
    semantic_followup = semantic_followup_from_db(source_project, rel_files)
    if semantic_followup:
        payload["semantic_followup"] = semantic_followup
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_learn_entry.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    add_episode_from_values(
        project,
        f"Learn entry {entry.relative_to(source_project.root)} from {source_project.root}",
        f"{'Replaced' if args.replace else 'Merged'} {len(rel_files)} files related to {entry.relative_to(source_project.root)} with depth {args.depth}",
        "learned",
    )
    output(payload, args.json)



def wiki_search(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    matches = collect_matches(project, args.query)
    data = matches["wiki_matches"] + matches["code_log_matches"]
    data.sort(key=lambda item: (item.get("score", 0), item.get("updated_at", "")), reverse=True)
    record_query_miss_if_empty(
        project,
        "wiki-search",
        args.query,
        {
            "semantic_facts": [],
            "reflections": [],
            "episodes": [],
            "wiki_matches": matches["wiki_matches"],
            "code_log_matches": matches["code_log_matches"],
            "edge_matches": matches["edge_matches"],
        },
    )
    output(data[:20], args.json)
