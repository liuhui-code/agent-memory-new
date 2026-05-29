#!/usr/bin/env python3
# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Local Agent Memory runtime.

This is the stable script API used by Agent Memory skills.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import re
import sqlite3
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_memory_runtime.cli import build_parser
from agent_memory_runtime.governance import (
    duplicate_candidates,
    maintain_health,
    maintain_merge,
    maintain_plan,
    maintain_promote,
    maintain_review,
    maintain_status,
    mark_stale,
    reflect_review,
    reflection_quality_issues,
)
from agent_memory_runtime.models import (
    ACTIVE_STATUS,
    CODE_EXTENSIONS,
    IGNORE_DIRS,
    PROJECT_FINGERPRINT,
    PROJECT_FINGERPRINT_SCHEME,
    Project,
    REQUIRED_TABLES,
)
from agent_memory_runtime.query import (
    collect_matches,
    limited_context,
    normalize_query_miss,
    record_query_miss_if_empty,
)
from agent_memory_runtime.records import (
    output,
    parse_ids,
    row_dict,
    table_for_type,
)
from agent_memory_runtime.storage import (
    connect,
    create_schema,
    ensure_dirs,
    ensure_initialized,
    now_iso,
    resolve_project,
    upsert_project,
    write_config,
    write_global_config,
)
from agent_memory_runtime.text import (
    json_list,
    json_list_text,
    reflection_list_text,
    score_text,
    terms_from_text,
    unique_list,
)


def init_project(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_dirs(project)
    with connect(project) as conn:
        create_schema(conn)
        upsert_project(conn, project)
    write_global_config(project)
    write_config(project)
    vault_index(args)
    print(f"initialized agent memory for {project.root} at {project.memory_dir}")


def doctor(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    checks: list[tuple[str, bool]] = [
        ("memory home exists", project.memory_home.exists()),
        ("project memory directory exists", project.memory_dir.exists()),
        ("global config.json exists", (project.memory_home / "config.json").exists()),
        ("config.json exists", (project.memory_dir / "config.json").exists()),
        ("memory.db exists", project.db_path.exists()),
        ("vault directory exists", project.vault_dir.exists()),
        ("runtime directory exists", project.runtime_dir.exists()),
    ]
    table_ok = False
    if project.db_path.exists():
        with connect(project) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            existing = {row["name"] for row in rows}
            table_ok = REQUIRED_TABLES.issubset(existing)
    checks.append(("required tables exist", table_ok))

    failed = False
    for label, ok in checks:
        print(f"{'OK' if ok else 'FAIL'} {label}")
        failed = failed or not ok
    if failed:
        raise SystemExit(1)


def add_semantic(args: argparse.Namespace, project: Project) -> None:
    if not args.fact:
        raise SystemExit("--fact is required for --type semantic")
    ts = now_iso()
    with connect(project) as conn:
        cur = conn.execute(
            """
            INSERT INTO semantic_facts(
              project_id, fact, source, confidence, category, scope, evidence,
              created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                args.fact,
                args.source or "manual",
                args.confidence,
                args.category,
                args.scope,
                args.evidence,
                ts,
                ts,
            ),
        )
        conn.commit()
    print(f"semantic fact #{cur.lastrowid} written")


def add_episode(args: argparse.Namespace, project: Project) -> None:
    if not args.task or not args.summary:
        raise SystemExit("--task and --summary are required for --type episode")
    with connect(project) as conn:
        cur = conn.execute(
            """
            INSERT INTO episodes(
              project_id, task, summary, outcome, files_touched, commands_run,
              importance, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                args.task,
                args.summary,
                args.outcome,
                args.files_touched,
                args.commands_run,
                args.importance,
                now_iso(),
            ),
        )
        conn.commit()
    print(f"episode #{cur.lastrowid} written")


def update(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    if args.type == "semantic":
        add_semantic(args, project)
    elif args.type == "episode":
        add_episode(args, project)
    else:
        raise SystemExit(f"unsupported update type: {args.type}")


def search(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = collect_matches(project, args.query)
    record_query_miss_if_empty(project, "search", args.query, data)
    output(data, args.json)


def context(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = limited_context(project, args.query)
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_context.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output(data, args.json)


REFLECTION_PAYLOAD_TASK_TYPES = {"diagnosis", "design", "execution", "workflow"}
REFLECTION_PAYLOAD_OUTCOMES = {"success", "failure", "partial"}


def load_reflection_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.payload and args.payload_file:
        raise SystemExit("provide only one of --payload or --payload-file")
    if args.payload_file:
        try:
            raw = Path(args.payload_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise SystemExit(f"cannot read --payload-file: {exc}") from exc
    else:
        raw = args.payload
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid reflection payload JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("reflection payload must be a JSON object")
    task_type = payload.get("task_type")
    if task_type and task_type not in REFLECTION_PAYLOAD_TASK_TYPES:
        raise SystemExit(
            "--payload task_type must be one of diagnosis, design, execution, workflow"
        )
    outcome = payload.get("outcome")
    if outcome and outcome not in REFLECTION_PAYLOAD_OUTCOMES:
        raise SystemExit("--payload outcome must be one of success, failure, partial")
    return payload


def reflection_value(args: argparse.Namespace, payload: dict[str, Any], key: str) -> Any:
    return payload.get(key) if key in payload else getattr(args, key, None)


def reflect(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    payload = load_reflection_payload(args)
    task = reflection_value(args, payload, "task")
    lesson = reflection_value(args, payload, "lesson")
    if not task or not lesson:
        raise SystemExit("--task and --lesson are required")
    data = {
        "project_id": project.project_id,
        "task": task,
        "summary": reflection_value(args, payload, "summary"),
        "mistake": reflection_value(args, payload, "mistake"),
        "lesson": lesson,
        "future_rule": reflection_value(args, payload, "future_rule"),
        "task_type": payload.get("task_type"),
        "outcome": payload.get("outcome"),
        "problem": payload.get("problem"),
        "reasoning_summary": payload.get("reasoning_summary"),
        "context_used": reflection_list_text(payload.get("context_used")),
        "what_worked": reflection_list_text(payload.get("what_worked")),
        "what_failed": reflection_list_text(payload.get("what_failed")),
        "scope": reflection_value(args, payload, "scope"),
        "evidence": reflection_value(args, payload, "evidence"),
        "confidence": float(reflection_value(args, payload, "confidence") or args.confidence),
        "trigger_condition": reflection_value(args, payload, "trigger_condition"),
        "anti_pattern": reflection_value(args, payload, "anti_pattern"),
        "repair_action": reflection_value(args, payload, "repair_action"),
        "applies_to": reflection_value(args, payload, "applies_to"),
        "does_not_apply_to": reflection_value(args, payload, "does_not_apply_to"),
        "created_at": now_iso(),
    }
    with connect(project) as conn:
        cur = conn.execute(
            """
            INSERT INTO reflections(
              project_id, task, summary, mistake, lesson, future_rule,
              task_type, outcome, problem, reasoning_summary, context_used,
              what_worked, what_failed, scope, evidence, confidence, trigger_condition, anti_pattern,
              repair_action, applies_to, does_not_apply_to, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                data["task"],
                data["summary"],
                data["mistake"],
                data["lesson"],
                data["future_rule"],
                data["task_type"],
                data["outcome"],
                data["problem"],
                data["reasoning_summary"],
                data["context_used"],
                data["what_worked"],
                data["what_failed"],
                data["scope"],
                data["evidence"],
                data["confidence"],
                data["trigger_condition"],
                data["anti_pattern"],
                data["repair_action"],
                data["applies_to"],
                data["does_not_apply_to"],
                data["created_at"],
            ),
        )
        if args.used_reflection_ids:
            ids = parse_ids(args.used_reflection_ids)
            conn.execute(
                f"""
                UPDATE reflections
                SET applied_count = COALESCE(applied_count, 0) + 1,
                    last_applied_at = ?,
                    last_outcome = ?
                WHERE project_id = ? AND id IN ({','.join('?' for _ in ids)})
                """,
                [data["created_at"], args.reflection_outcome, project.project_id, *ids],
            )
        conn.commit()
        data["id"] = cur.lastrowid
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_reflection.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"reflection #{data['id']} written")


def list_records(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    table = table_for_type(args.type)
    with connect(project) as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE project_id = ? ORDER BY id DESC LIMIT ?",
            (project.project_id, args.limit),
        ).fetchall()
    output([row_dict(row) for row in rows], args.json)


def miss_list(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    status_filter = "AND status = ?" if args.status else ""
    values: list[Any] = [project.project_id]
    if args.status:
        values.append(args.status)
    values.append(args.limit)
    with connect(project) as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM query_misses
            WHERE project_id = ? {status_filter}
            ORDER BY id DESC
            LIMIT ?
            """,
            values,
        ).fetchall()
    output([row_dict(row) for row in rows], args.json)


def miss_status(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    if args.status not in {"open", "reviewed", "resolved", "ignored"}:
        raise SystemExit(f"unsupported query miss status: {args.status}")
    with connect(project) as conn:
        conn.execute(
            """
            UPDATE query_misses
            SET status = ?, resolution = ?, reviewed_at = ?
            WHERE project_id = ? AND id = ?
            """,
            (args.status, args.resolution, now_iso(), project.project_id, args.id),
        )
        conn.commit()
    print(f"query miss #{args.id} status set to {args.status}")


def slugify(text: str, fallback: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text.strip().lower()).strip("-")
    return slug[:80] or fallback


def frontmatter(record_type: str, project: Project, created_at: str) -> str:
    return (
        "---\n"
        f"type: {record_type}\n"
        f"project_id: {project.project_id}\n"
        f"created_at: {created_at}\n"
        "tags:\n"
        "  - agent-memory\n"
        f"  - {record_type}\n"
        "---\n\n"
    )


def vault_init(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    ensure_dirs(project)
    vault_index(args)
    print(f"vault initialized at {project.vault_dir}")


def write_vault_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def vault_export(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    ensure_dirs(project)
    with connect(project) as conn:
        episodes = conn.execute(
            "SELECT * FROM episodes WHERE project_id = ? ORDER BY id DESC",
            (project.project_id,),
        ).fetchall()
        facts = conn.execute(
            "SELECT * FROM semantic_facts WHERE project_id = ? ORDER BY id DESC",
            (project.project_id,),
        ).fetchall()
        reflections = conn.execute(
            "SELECT * FROM reflections WHERE project_id = ? ORDER BY id DESC",
            (project.project_id,),
        ).fetchall()
        files = conn.execute(
            "SELECT * FROM code_files WHERE project_id = ? ORDER BY file_path",
            (project.project_id,),
        ).fetchall()
        symbols = conn.execute(
            "SELECT * FROM code_symbols WHERE project_id = ? ORDER BY file_path, symbol",
            (project.project_id,),
        ).fetchall()
        logs = conn.execute(
            "SELECT * FROM code_log_statements WHERE project_id = ? ORDER BY file_path, line",
            (project.project_id,),
        ).fetchall()
        edges = conn.execute(
            "SELECT * FROM memory_edges WHERE project_id = ? ORDER BY source_type, source_id, relation",
            (project.project_id,),
        ).fetchall()
        query_misses = conn.execute(
            "SELECT * FROM query_misses WHERE project_id = ? ORDER BY id DESC",
            (project.project_id,),
        ).fetchall()

    for row in episodes:
        slug = slugify(row["task"], f"episode-{row['id']}")
        content = frontmatter("episode", project, row["created_at"])
        content += f"# Episode: {row['task']}\n\n"
        content += f"## Summary\n\n{row['summary']}\n\n"
        if row["outcome"]:
            content += f"## Outcome\n\n{row['outcome']}\n"
        write_vault_file(project.vault_dir / "Episodes" / f"{row['id']:04d}-{slug}.md", content)

    for row in reflections:
        slug = slugify(row["task"], f"reflection-{row['id']}")
        content = frontmatter("reflection", project, row["created_at"])
        content += f"# Reflection: {row['task']}\n\n"
        content += f"- Status: {row['status'] or ACTIVE_STATUS}\n"
        content += f"- Confidence: {row['confidence'] or 0.8}\n"
        if row["scope"]:
            content += f"- Scope: {row['scope']}\n"
        if row["evidence"]:
            content += f"- Evidence: {row['evidence']}\n"
        if row["task_type"]:
            content += f"- Task type: {row['task_type']}\n"
        if row["outcome"]:
            content += f"- Outcome: {row['outcome']}\n"
        content += "\n"
        if row["problem"]:
            content += f"## Problem\n\n{row['problem']}\n\n"
        if row["summary"]:
            content += f"## Summary\n\n{row['summary']}\n\n"
        if row["reasoning_summary"]:
            content += f"## Reasoning Summary\n\n{row['reasoning_summary']}\n\n"
        list_sections = [
            ("Context Used", row["context_used"]),
            ("What Worked", row["what_worked"]),
            ("What Failed", row["what_failed"]),
        ]
        for heading, raw_items in list_sections:
            items = json_list(raw_items)
            if items:
                content += f"## {heading}\n\n"
                for item in items:
                    content += f"- {item}\n"
                content += "\n"
        if row["mistake"]:
            content += f"## Mistake\n\n{row['mistake']}\n\n"
        content += f"## Lesson\n\n{row['lesson']}\n\n"
        if row["future_rule"]:
            content += f"## Future Rule\n\n{row['future_rule']}\n"
        quality_sections = [
            ("Trigger Condition", row["trigger_condition"]),
            ("Anti Pattern", row["anti_pattern"]),
            ("Repair Action", row["repair_action"]),
            ("Applies To", row["applies_to"]),
            ("Does Not Apply To", row["does_not_apply_to"]),
        ]
        for heading, value in quality_sections:
            if value:
                content += f"\n## {heading}\n\n{value}\n"
        content += "\n## Reuse\n\n"
        content += f"- Applied count: {row['applied_count'] or 0}\n"
        content += f"- Last applied at: {row['last_applied_at'] or ''}\n"
        content += f"- Last outcome: {row['last_outcome'] or ''}\n"
        write_vault_file(project.vault_dir / "Reflections" / f"{row['id']:04d}-{slug}.md", content)

    facts_content = frontmatter("semantic-facts", project, now_iso())
    facts_content += "# Semantic Facts\n\n"
    for row in facts:
        status = row["status"] or ("stale" if row["is_stale"] else ACTIVE_STATUS)
        details = f"{row['source']}, status {status}, confidence {row['confidence']}"
        if row["scope"]:
            details += f", scope {row['scope']}"
        facts_content += f"- #{row['id']} ({details}): {row['fact']}\n"
    write_vault_file(project.vault_dir / "Semantic Facts" / "project-facts.md", facts_content)

    files_content = frontmatter("codebase-wiki", project, now_iso())
    files_content += "# Code Files\n\n"
    for row in files:
        files_content += f"- `{row['file_path']}` ({row['language'] or 'unknown'}): {row['summary'] or ''}\n"
        if row["business_summary"]:
            files_content += f"  - Business: {row['business_summary']}\n"
        terms = json_list(row["business_terms"])
        if terms:
            files_content += f"  - Terms: {', '.join(terms)}\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "files.md", files_content)

    symbols_content = frontmatter("codebase-wiki", project, now_iso())
    symbols_content += "# Code Symbols\n\n"
    for row in symbols:
        symbols_content += f"- `{row['file_path']}` :: `{row['symbol']}` ({row['symbol_type'] or 'symbol'})\n"
        if row["business_summary"]:
            symbols_content += f"  - Business: {row['business_summary']}\n"
        terms = json_list(row["business_terms"])
        if terms:
            symbols_content += f"  - Terms: {', '.join(terms)}\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "symbols.md", symbols_content)

    logs_content = frontmatter("codebase-wiki", project, now_iso())
    logs_content += "# Code Log Statements\n\n"
    for row in logs:
        location = f"{row['file_path']}:{row['line']}" if row["line"] else row["file_path"]
        function = f" in `{row['function']}`" if row["function"] else ""
        logs_content += (
            f"- `{location}`{function} [{row['level'] or 'log'}] "
            f"{row['message_template']}\n"
        )
        if row["business_summary"]:
            logs_content += f"  - Business: {row['business_summary']}\n"
        terms = json_list(row["business_terms"])
        if terms:
            logs_content += f"  - Terms: {', '.join(terms)}\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "log-statements.md", logs_content)

    edges_content = frontmatter("codebase-wiki", project, now_iso())
    edges_content += "# Memory Edges\n\n"
    for row in edges:
        edges_content += (
            f"- {row['source_type']} #{row['source_id']} "
            f"--{row['relation']}--> {row['target_type']} #{row['target_id']}"
        )
        if row["evidence"]:
            edges_content += f" ({row['evidence']})"
        edges_content += "\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "memory-edges.md", edges_content)

    daily = project.vault_dir / "Daily" / f"{datetime.now().date().isoformat()}.md"
    daily_content = frontmatter("daily", project, now_iso())
    daily_content += "# Daily Agent Memory\n\n"
    daily_content += f"- Exported at {now_iso()}\n"
    write_vault_file(daily, daily_content)

    write_governance_dashboard(project, facts, reflections, episodes, query_misses)
    vault_index(args)
    print(f"vault exported to {project.vault_dir}")


def write_governance_dashboard(
    project: Project,
    facts: list[sqlite3.Row],
    reflections: list[sqlite3.Row],
    episodes: list[sqlite3.Row],
    query_misses: list[sqlite3.Row],
) -> None:
    fact_rows = [row_dict(row) for row in facts]
    reflection_rows = [row_dict(row) for row in reflections]
    episode_rows = [row_dict(row) for row in episodes]
    query_miss_rows = [row_dict(row) for row in query_misses]
    active_facts = [row for row in fact_rows if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")]
    active_reflections = [row for row in reflection_rows if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")]
    stale = [
        row for row in fact_rows + reflection_rows
        if row.get("is_stale") or row.get("status") == "stale"
    ]
    low_confidence = [
        row for row in fact_rows + reflection_rows
        if float(row.get("confidence") or 0.8) < 0.6
    ]
    duplicates = duplicate_candidates(active_facts, "semantic") + duplicate_candidates(active_reflections, "reflection")
    unreviewed_reflections = [
        row for row in reflection_rows
        if not row.get("reviewed_at") and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS
    ]

    header = frontmatter("governance", project, now_iso())
    notice = "This file is generated. Edit memory through agent-memory-maintain or agent-memory-reflect.\n\n"

    health = header + "# Memory Health\n\n" + notice
    health += f"- Semantic facts: {len(fact_rows)}\n"
    health += f"- Reflections: {len(reflection_rows)}\n"
    health += f"- Episodes: {len(episode_rows)}\n"
    health += f"- Stale memories: {len(stale)}\n"
    health += f"- Low-confidence memories: {len(low_confidence)}\n"
    health += f"- Duplicate candidates: {len(duplicates)}\n"
    health += f"- Unreviewed reflections: {len(unreviewed_reflections)}\n"
    health += f"- Open query misses: {sum(1 for row in query_miss_rows if row.get('status') == 'open')}\n"
    write_vault_file(project.vault_dir / "Governance" / "Health.md", health)

    review = header + "# Review Queue\n\n" + notice
    review += "## Unreviewed Reflections\n\n"
    for row in unreviewed_reflections[:30]:
        review += f"- reflection #{row['id']}: {row['task']}\n"
    review += "\n## Unreviewed Episodes\n\n"
    for row in episode_rows[:30]:
        if not row.get("reviewed_at") and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS:
            review += f"- episode #{row['id']}: {row['task']}\n"
    write_vault_file(project.vault_dir / "Governance" / "Review Queue.md", review)

    stale_doc = header + "# Stale Memories\n\n" + notice
    for row in stale[:50]:
        text = row.get("fact") or row.get("lesson") or row.get("task")
        stale_doc += f"- #{row['id']} ({row.get('status') or 'stale'}): {text}\n"
    write_vault_file(project.vault_dir / "Governance" / "Stale Memories.md", stale_doc)

    merge_doc = header + "# Merge Candidates\n\n" + notice
    for item in duplicates[:50]:
        merge_doc += f"- {item['type']} ids {item['ids']} similarity {item['similarity']}: {item['reason']}\n"
    write_vault_file(project.vault_dir / "Governance" / "Merge Candidates.md", merge_doc)

    low_doc = header + "# Low Confidence\n\n" + notice
    for row in low_confidence[:50]:
        text = row.get("fact") or row.get("lesson") or row.get("task")
        low_doc += f"- #{row['id']} confidence {row.get('confidence')}: {text}\n"
    write_vault_file(project.vault_dir / "Governance" / "Low Confidence.md", low_doc)

    reflection_quality = [
        {
            "id": row["id"],
            "task": row["task"],
            "issues": reflection_quality_issues(row),
        }
        for row in active_reflections
    ]
    reflection_quality = [item for item in reflection_quality if item["issues"]]
    quality_doc = header + "# Reflection Quality\n\n" + notice
    quality_doc += "## Reflection Quality Issues\n\n"
    for item in reflection_quality[:50]:
        quality_doc += f"- reflection #{item['id']} {item['task']}: {', '.join(item['issues'])}\n"
    write_vault_file(project.vault_dir / "Governance" / "Reflection Quality.md", quality_doc)

    misses_doc = header + "# Query Misses\n\n" + notice
    for row in query_miss_rows[:50]:
        miss_count = row.get("miss_count") or 1
        last_seen_at = row.get("last_seen_at") or row.get("created_at")
        misses_doc += f"- query miss #{row['id']} ({row['status']}, {row['source']}, misses {miss_count}, last seen {last_seen_at}): {row['query']}\n"
        if row.get("resolution"):
            misses_doc += f"  - resolution: {row['resolution']}\n"
    write_vault_file(project.vault_dir / "Governance" / "Query Misses.md", misses_doc)

    wiki_misses_doc = frontmatter("codebase-wiki", project, now_iso())
    wiki_misses_doc += "# Query Misses\n\n" + notice
    wiki_misses_doc += "These misses show where natural-language questions failed to retrieve learned code or memory context.\n\n"
    for row in query_miss_rows[:50]:
        miss_count = row.get("miss_count") or 1
        normalized = row.get("normalized_query") or normalize_query_miss(row["query"])
        last_seen_at = row.get("last_seen_at") or row.get("created_at")
        wiki_misses_doc += (
            f"- query miss #{row['id']} ({row['status']}, {row['source']}, "
            f"misses {miss_count}, last seen {last_seen_at}): {row['query']}\n"
        )
        wiki_misses_doc += f"  - normalized: `{normalized}`\n"
        if row.get("resolution"):
            wiki_misses_doc += f"  - resolution: {row['resolution']}\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "query-misses.md", wiki_misses_doc)


def vault_index(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_dirs(project)
    content = "# Agent Memory Vault\n\n"
    content += "## Recent Episodes\n\n"
    for path in sorted((project.vault_dir / "Episodes").glob("*.md"), reverse=True)[:10]:
        content += f"- [[Episodes/{path.stem}]]\n"
    content += "\n## Recent Reflections\n\n"
    for path in sorted((project.vault_dir / "Reflections").glob("*.md"), reverse=True)[:10]:
        content += f"- [[Reflections/{path.stem}]]\n"
    content += "\n## Semantic Facts\n\n- [[Semantic Facts/project-facts]]\n"
    content += "\n## Codebase Wiki\n\n"
    content += "- [[Codebase Wiki/files]]\n"
    content += "- [[Codebase Wiki/symbols]]\n"
    content += "- [[Codebase Wiki/log-statements]]\n"
    content += "- [[Codebase Wiki/memory-edges]]\n"
    content += "- [[Codebase Wiki/query-misses]]\n"
    content += "\n## Governance\n\n"
    content += "- [[Governance/Health]]\n"
    content += "- [[Governance/Review Queue]]\n"
    content += "- [[Governance/Stale Memories]]\n"
    content += "- [[Governance/Merge Candidates]]\n"
    content += "- [[Governance/Low Confidence]]\n"
    content += "- [[Governance/Reflection Quality]]\n"
    content += "- [[Governance/Query Misses]]\n"
    write_vault_file(project.vault_dir / "index.md", content)


def should_skip_dir(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def language_for(path: Path) -> str | None:
    return CODE_EXTENSIONS.get(path.suffix.lower())


def summarize_file(path: Path, language: str) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if language == "Markdown":
        heading = next((line.lstrip("#").strip() for line in lines if line.startswith("#")), "")
        return heading or f"Markdown file with {len(lines)} non-empty lines"
    if language == "ArkTS":
        symbols = extract_symbols(path, language)
        components = [name for name, kind in symbols if kind == "component"]
        routes = [name for name, kind in symbols if kind == "route"]
        resources = [name for name, kind in symbols if kind == "resource"]
        parts = [f"ArkTS file with {len(lines)} non-empty lines"]
        if components:
            parts.append("components: " + ", ".join(sorted(set(components))[:5]))
        if routes:
            parts.append("routes: " + ", ".join(sorted(set(routes))[:5]))
        if resources:
            parts.append("resources: " + ", ".join(sorted(set(resources))[:5]))
        return "; ".join(parts)
    if language == "HarmonyOS Config":
        symbols = extract_symbols(path, language)
        grouped: dict[str, list[str]] = {}
        for name, kind in symbols:
            grouped.setdefault(kind, []).append(name)
        parts = [f"HarmonyOS config with {len(lines)} non-empty lines"]
        for kind in ("ability", "permission", "dependency", "page_profile"):
            names = grouped.get(kind, [])
            if names:
                parts.append(f"{kind}s: " + ", ".join(sorted(set(names))[:5]))
        return "; ".join(parts)
    return f"{language} file with {len(lines)} non-empty lines"


def summarize_symbol(file_path: str, symbol: str, symbol_type: str | None, language: str) -> str:
    kind = symbol_type or "symbol"
    if language == "ArkTS":
        if kind == "component":
            return f"ArkTS component {symbol} declared in {file_path}"
        if kind == "route":
            return f"ArkTS route target {symbol} referenced by {file_path}"
        if kind == "resource":
            return f"ArkTS resource {symbol} referenced by {file_path}"
        if kind == "function":
            return f"ArkTS function or lifecycle method {symbol} in {file_path}"
        if kind == "class":
            return f"ArkTS class {symbol} declared in {file_path}"
    if language == "HarmonyOS Config":
        return f"HarmonyOS {kind} {symbol} configured in {file_path}"
    return f"{kind} {symbol} in {file_path}"


def extract_symbols(path: Path, language: str) -> list[tuple[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    symbols: list[tuple[str, str]] = []
    patterns: list[tuple[str, str]]
    if language == "Python":
        patterns = [(r"^\s*def\s+([A-Za-z_]\w*)\s*\(", "function"), (r"^\s*class\s+([A-Za-z_]\w*)", "class")]
    elif language in {"TypeScript", "JavaScript"}:
        patterns = [
            (r"^\s*function\s+([A-Za-z_$][\w$]*)\s*\(", "function"),
            (r"^\s*class\s+([A-Za-z_$][\w$]*)", "class"),
            (r"^\s*const\s+([A-Za-z_$][\w$]*)\s*=", "const"),
        ]
    elif language == "ArkTS":
        patterns = [
            (r"^\s*(?:export\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", "function"),
            (r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", "class"),
            (r"^\s*(?:export\s+)?struct\s+([A-Za-z_$][\w$]*)", "component"),
            (r"^\s*(?:private\s+|public\s+|protected\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::\s*[^ {]+)?\s*\{", "function"),
        ]
    elif language == "Dart":
        patterns = [
            (r"^\s*class\s+([A-Za-z_]\w*)", "class"),
            (r"^\s*(?:Future<[^>]+>|void|Widget)\s+([A-Za-z_]\w*)\s*\(", "function"),
        ]
    elif language == "Swift":
        patterns = [
            (r"^\s*class\s+([A-Za-z_]\w*)", "class"),
            (r"^\s*struct\s+([A-Za-z_]\w*)", "struct"),
            (r"^\s*func\s+([A-Za-z_]\w*)\s*\(", "function"),
        ]
    elif language == "Markdown":
        patterns = [(r"^(#{1,6})\s+(.+)$", "heading")]
    elif language == "HarmonyOS Config":
        return extract_harmonyos_config_symbols(text)
    else:
        patterns = []
    for line in text.splitlines():
        for pattern, kind in patterns:
            match = re.search(pattern, line)
            if match:
                if language == "Markdown":
                    name = match.group(2).strip()
                else:
                    name = match.group(1).strip()
                if name in {"if", "for", "while", "switch", "catch"}:
                    continue
                symbols.append((name, kind))
    if language == "ArkTS":
        symbols.extend(extract_arkts_reference_symbols(text))
    return symbols


def extract_arkts_reference_symbols(text: str) -> list[tuple[str, str]]:
    symbols: list[tuple[str, str]] = []
    for match in re.finditer(
        r"\brouter\.(?:pushUrl|replaceUrl)\s*\(\s*\{[^}]*\burl\s*:\s*['\"]([^'\"]+)['\"]",
        text,
        re.DOTALL,
    ):
        symbols.append((match.group(1), "route"))
    for match in re.finditer(r"\$r\s*\(\s*['\"]([^'\"]+)['\"]", text):
        symbols.append((match.group(1), "resource"))
    return symbols


def extract_harmonyos_config_symbols(text: str) -> list[tuple[str, str]]:
    symbols: list[tuple[str, str]] = []
    for match in re.finditer(r'"name"\s*:\s*"([^"]+)"', text):
        name = match.group(1)
        if "permission." in name:
            symbols.append((name, "permission"))
        elif name.endswith("Ability"):
            symbols.append((name, "ability"))
    for block_name in ("dependencies", "devDependencies", "overrides"):
        block_match = re.search(rf'"{block_name}"\s*:\s*\{{(.*?)\}}', text, re.DOTALL)
        if not block_match:
            continue
        for dep in re.finditer(r'"([^"]+)"\s*:', block_match.group(1)):
            symbols.append((dep.group(1), "dependency"))
    for match in re.finditer(r'"pages"\s*:\s*"([^"]+)"', text):
        symbols.append((match.group(1), "page_profile"))
    return symbols


def extract_log_statements(path: Path, language: str) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    logs: list[dict[str, Any]] = []
    current_function: str | None = None
    current_indent = -1
    for line_number, line in enumerate(text.splitlines(), start=1):
        symbol = function_symbol_on_line(line, language)
        if symbol:
            current_function, current_indent = symbol
        elif language == "Python" and current_function:
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())
            if stripped and indent <= current_indent and not stripped.startswith(("#", "@")):
                current_function = None
                current_indent = -1
        log = log_statement_on_line(line, language)
        if not log:
            continue
        log["line"] = line_number
        log["function"] = current_function
        log["raw_statement"] = line.strip()
        logs.append(log)
    return logs


def function_symbol_on_line(line: str, language: str) -> tuple[str, int] | None:
    indent = len(line) - len(line.lstrip())
    if language == "Python":
        match = re.match(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", line)
        return (match.group(1), indent) if match else None
    if language in {"TypeScript", "JavaScript"}:
        patterns = [
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
            r"^\s*(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(",
            r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)",
        ]
    elif language == "ArkTS":
        patterns = [
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
            r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)",
            r"^\s*(?:export\s+)?struct\s+([A-Za-z_$][\w$]*)",
            r"^\s*(?:private\s+|public\s+|protected\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::\s*[^ {]+)?\s*\{",
        ]
    elif language == "Dart":
        patterns = [
            r"^\s*(?:Future<[^>]+>|void|Widget|String|int|bool|double)\s+([A-Za-z_]\w*)\s*\(",
            r"^\s*class\s+([A-Za-z_]\w*)",
        ]
    elif language == "Swift":
        patterns = [
            r"^\s*func\s+([A-Za-z_]\w*)\s*\(",
            r"^\s*(?:class|struct)\s+([A-Za-z_]\w*)",
        ]
    else:
        patterns = []
    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            name = match.group(1)
            if name in {"if", "for", "while", "switch", "catch"}:
                continue
            return name, indent
    return None


def log_statement_on_line(line: str, language: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "//")):
        return None
    patterns: list[tuple[str, str, str]]
    if language == "Python":
        patterns = [
            (r"\bprint\s*\((.*)\)", "print", "print"),
            (r"\b(logging|logger)\.(debug|info|warning|warn|error|exception)\s*\((.*)\)", "", ""),
        ]
    elif language in {"TypeScript", "JavaScript"}:
        patterns = [
            (r"\bconsole\.(log|info|warn|error|debug)\s*\((.*)\)", "console", ""),
            (r"\blogger\.(log|info|warn|error|debug)\s*\((.*)\)", "logger", ""),
        ]
    elif language == "ArkTS":
        patterns = [
            (r"\bconsole\.(log|info|warn|error|debug)\s*\((.*)\)", "console", ""),
            (r"\blogger\.(log|info|warn|error|debug)\s*\((.*)\)", "logger", ""),
            (r"\bhilog\.(debug|info|warn|error|fatal)\s*\((.*)\)", "hilog", ""),
        ]
    elif language == "Dart":
        patterns = [
            (r"\bprint\s*\((.*)\)", "print", "print"),
            (r"\bdebugPrint\s*\((.*)\)", "debugPrint", "debug"),
            (r"\blog\s*\((.*)\)", "log", "log"),
        ]
    elif language == "Swift":
        patterns = [
            (r"\bprint\s*\((.*)\)", "print", "print"),
            (r"\bNSLog\s*\((.*)\)", "NSLog", "log"),
            (r"\bos_log\s*\((.*)\)", "os_log", "log"),
            (r"\blogger\.(debug|info|warning|error)\s*\((.*)\)", "logger", ""),
        ]
    else:
        return None
    for pattern, logger_name, fixed_level in patterns:
        match = re.search(pattern, stripped)
        if not match:
            continue
        if language == "Python" and logger_name == "":
            logger = match.group(1)
            level = match.group(2)
            args_text = match.group(3)
        elif language in {"TypeScript", "JavaScript", "ArkTS"}:
            logger = logger_name
            level = match.group(1)
            args_text = match.group(2)
        elif language == "Swift" and logger_name == "logger":
            logger = logger_name
            level = match.group(1)
            args_text = match.group(2)
        else:
            logger = logger_name
            level = fixed_level
            args_text = match.group(1)
        return {
            "level": "warning" if level == "warn" else level,
            "logger": logger,
            "message_template": message_template_for_args(logger, args_text),
        }
    return None


def message_template_for_args(logger: str, args_text: str) -> str:
    literals = string_literals(args_text)
    if logger == "hilog" and len(literals) >= 2:
        return literals[1]
    if literals:
        return literals[0]
    return args_text.strip()


def string_literals(text: str) -> list[str]:
    return [match.group(2) for match in re.finditer(r"""(['"])(.*?)(?<!\\)\1""", text)]


def wiki_index(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, args.source)
    files = collect_project_files(source_project)
    stats = write_wiki_index(source_project, files, replace=True)
    print(f"wiki index updated ({parse_stats_summary(stats)})")


def collect_project_files(project: Project) -> list[Path]:
    files_to_index: list[Path] = []
    for root, dirs, files in os.walk(project.root):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        if should_skip_dir(root_path.relative_to(project.root) if root_path != project.root else Path("")):
            continue
        for filename in files:
            path = root_path / filename
            rel = path.relative_to(project.root)
            if should_skip_dir(rel):
                continue
            if language_for(path):
                files_to_index.append(path)
    return files_to_index


def collect_path_files(project: Project, target: Path) -> list[Path]:
    if not target.exists():
        raise SystemExit(f"path does not exist: {target}")
    if target.is_file():
        return [target] if language_for(target) else []
    files_to_index: list[Path] = []
    for root, dirs, files in os.walk(target):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        rel_root = root_path.relative_to(project.root)
        if should_skip_dir(rel_root):
            continue
        for filename in files:
            path = root_path / filename
            rel = path.relative_to(project.root)
            if should_skip_dir(rel):
                continue
            if language_for(path):
                files_to_index.append(path)
    return files_to_index


def write_wiki_index(project: Project, files: list[Path], replace: bool = False) -> dict[str, Any]:
    ts = now_iso()
    unique_files = sorted({path.resolve() for path in files})
    relative_files: list[tuple[Path, Path, str, str]] = []
    for path in unique_files:
        try:
            rel = path.relative_to(project.root)
        except ValueError:
            continue
        if should_skip_dir(rel):
            continue
        language = language_for(path)
        if not language:
            continue
        relative_files.append((path, rel, str(rel), language))

    language_counts: Counter[str] = Counter()
    symbol_type_counts: Counter[str] = Counter()
    log_level_counts: Counter[str] = Counter()
    symbols_by_file: dict[str, list[tuple[str, str]]] = {}
    logs_by_file: dict[str, list[dict[str, Any]]] = {}
    for path, _rel, rel_text, language in relative_files:
        language_counts[language] += 1
        symbols = extract_symbols(path, language)
        logs = extract_log_statements(path, language)
        symbols_by_file[rel_text] = symbols
        logs_by_file[rel_text] = logs
        for _symbol, symbol_type in symbols:
            symbol_type_counts[symbol_type or "symbol"] += 1
        for log in logs:
            log_level_counts[str(log.get("level") or "log")] += 1

    with connect(project) as conn:
        if replace:
            conn.execute("DELETE FROM code_files WHERE project_id = ?", (project.project_id,))
            conn.execute("DELETE FROM code_symbols WHERE project_id = ?", (project.project_id,))
            conn.execute("DELETE FROM code_log_statements WHERE project_id = ?", (project.project_id,))
        else:
            for _, _, rel_text, _ in relative_files:
                conn.execute(
                    "DELETE FROM code_files WHERE project_id = ? AND file_path = ?",
                    (project.project_id, rel_text),
                )
                conn.execute(
                    "DELETE FROM code_symbols WHERE project_id = ? AND file_path = ?",
                    (project.project_id, rel_text),
                )
                conn.execute(
                    "DELETE FROM code_log_statements WHERE project_id = ? AND file_path = ?",
                    (project.project_id, rel_text),
                )
        conn.execute("DELETE FROM memory_edges WHERE project_id = ?", (project.project_id,))
        for path, _rel, rel_text, language in relative_files:
            summary = summarize_file(path, language)
            conn.execute(
                """
                INSERT INTO code_files(project_id, file_path, summary, language, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project.project_id, rel_text, summary, language, ts),
            )
            for symbol, symbol_type in symbols_by_file.get(rel_text, []):
                summary = summarize_symbol(rel_text, symbol, symbol_type, language)
                conn.execute(
                    """
                    INSERT INTO code_symbols(project_id, file_path, symbol, symbol_type, summary, calls, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (project.project_id, rel_text, symbol, symbol_type, summary, "", ts),
                )
            for log in logs_by_file.get(rel_text, []):
                conn.execute(
                    """
                    INSERT INTO code_log_statements(
                      project_id, file_path, line, function, level, logger,
                      message_template, raw_statement, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project.project_id,
                        rel_text,
                        log.get("line"),
                        log.get("function"),
                        log.get("level"),
                        log.get("logger"),
                        log.get("message_template") or "",
                        log.get("raw_statement"),
                        ts,
                    ),
                )
        rebuild_code_memory_edges(conn, project)
        memory_edges_total = conn.execute(
            "SELECT COUNT(*) AS count FROM memory_edges WHERE project_id = ?",
            (project.project_id,),
        ).fetchone()["count"]
        conn.commit()
    return {
        "files_indexed": len(relative_files),
        "languages": dict(sorted(language_counts.items())),
        "symbols_total": sum(symbol_type_counts.values()),
        "symbols_by_type": dict(sorted(symbol_type_counts.items())),
        "code_logs_total": sum(log_level_counts.values()),
        "code_logs_by_level": dict(sorted(log_level_counts.items())),
        "memory_edges_total": memory_edges_total,
    }


def rebuild_code_memory_edges(conn: sqlite3.Connection, project: Project) -> None:
    ts = now_iso()
    project_id = project.project_id
    files = conn.execute(
        "SELECT id, file_path, language FROM code_files WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    symbols = conn.execute(
        "SELECT id, file_path, symbol, symbol_type FROM code_symbols WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    logs = conn.execute(
        "SELECT id, file_path, function, line FROM code_log_statements WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    file_ids = {row["file_path"]: row["id"] for row in files}
    symbol_ids = {
        (row["file_path"], row["symbol"]): row["id"]
        for row in symbols
    }
    for row in symbols:
        file_id = file_ids.get(row["file_path"])
        if file_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_file",
                file_id,
                "contains",
                "code_symbol",
                row["id"],
                row["file_path"],
                0.9,
                ts,
            )
    for row in logs:
        file_id = file_ids.get(row["file_path"])
        evidence = f"{row['file_path']}:{row['line']}" if row["line"] else row["file_path"]
        if file_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_file",
                file_id,
                "contains",
                "code_log_statement",
                row["id"],
                evidence,
                0.9,
                ts,
            )
        function_name = row["function"]
        symbol_id = symbol_ids.get((row["file_path"], function_name)) if function_name else None
        if symbol_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_symbol",
                symbol_id,
                "emits_log",
                "code_log_statement",
                row["id"],
                evidence,
                0.8,
                ts,
            )

    insert_arkts_knowledge_edges(conn, project, files, symbols, ts)


def insert_arkts_knowledge_edges(
    conn: sqlite3.Connection,
    project: Project,
    files: list[sqlite3.Row],
    symbols: list[sqlite3.Row],
    ts: str,
) -> None:
    file_ids = {row["file_path"]: row["id"] for row in files}
    symbol_ids = {
        (row["file_path"], row["symbol"], row["symbol_type"]): row["id"]
        for row in symbols
    }
    for row in files:
        if row["language"] != "ArkTS":
            continue
        source_rel = row["file_path"]
        source_id = row["id"]
        source_abs = project.root / source_rel
        try:
            text = source_abs.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for target in resolve_js_imports(project, source_abs, text, [".ets", ".ts", ".js"]):
            target_rel = relative_project_path(project, target)
            target_id = file_ids.get(target_rel)
            if target_id:
                insert_memory_edge(
                    conn,
                    project.project_id,
                    "code_file",
                    source_id,
                    "imports",
                    "code_file",
                    target_id,
                    f"{source_rel} -> {target_rel}",
                    0.85,
                    ts,
                )

        for target in resolve_arkts_router_targets(project, source_abs, text):
            target_rel = relative_project_path(project, target)
            target_id = file_ids.get(target_rel)
            if target_id:
                insert_memory_edge(
                    conn,
                    project.project_id,
                    "code_file",
                    source_id,
                    "routes_to",
                    "code_file",
                    target_id,
                    f"{source_rel} -> {target_rel}",
                    0.85,
                    ts,
                )

        for resource, kind in extract_arkts_reference_symbols(text):
            if kind != "resource":
                continue
            symbol_id = symbol_ids.get((source_rel, resource, "resource"))
            if symbol_id:
                insert_memory_edge(
                    conn,
                    project.project_id,
                    "code_file",
                    source_id,
                    "uses_resource",
                    "code_symbol",
                    symbol_id,
                    f"{source_rel} uses {resource}",
                    0.8,
                    ts,
                )


def relative_project_path(project: Project, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.root))
    except ValueError:
        return str(path)
        function_name = row["function"]
        symbol_id = symbol_ids.get((row["file_path"], function_name)) if function_name else None
        if symbol_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_symbol",
                symbol_id,
                "emits_log",
                "code_log_statement",
                row["id"],
                evidence,
                0.8,
                ts,
            )


def insert_memory_edge(
    conn: sqlite3.Connection,
    project_id: str,
    source_type: str,
    source_id: int,
    relation: str,
    target_type: str,
    target_id: int,
    evidence: str,
    confidence: float,
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO memory_edges(
          project_id, source_type, source_id, relation, target_type,
          target_id, evidence, confidence, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            source_type,
            source_id,
            relation,
            target_type,
            target_id,
            evidence,
            confidence,
            created_at,
        ),
    )


def resolve_learning_source(project: Project, raw_source: str | None) -> Path:
    source = Path(raw_source).expanduser() if raw_source else project.root
    if not source.is_absolute():
        source = project.root / source
    source = source.resolve()
    if not source.exists() or not source.is_dir():
        raise SystemExit(f"source must be a directory: {source}")
    return source


def project_for_learning_source(project: Project, raw_source: str | None) -> Project:
    source = resolve_learning_source(project, raw_source)
    return replace(project, root=source, project_name=source.name)


def resolve_target(project: Project, raw_path: str) -> Path:
    target = Path(raw_path).expanduser()
    if not target.is_absolute():
        target = project.root / target
    target = target.resolve()
    try:
        target.relative_to(project.root)
    except ValueError:
        raise SystemExit(f"path must be inside project: {target}")
    return target


def learn_path(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, args.source)
    target = resolve_target(source_project, args.path)
    files = collect_path_files(source_project, target)
    stats = write_wiki_index(source_project, files, replace=args.replace)
    task = f"Learn path {target.relative_to(source_project.root)} from {source_project.root}"
    mode = "replaced" if args.replace else "merged"
    summary = f"{mode.capitalize()} {len(files)} files from {target.relative_to(source_project.root)}"
    add_episode_from_values(project, task, summary, "learned")
    payload = {
        "source": str(source_project.root),
        "path": str(target.relative_to(source_project.root)),
        "mode": "replace" if args.replace else "merge",
        "files": [str(path.relative_to(source_project.root)) for path in sorted(files)],
        "count": len(files),
        "summary": summary,
        "parse_stats": stats,
    }
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_learn_path.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.json:
        output(payload, True)
    else:
        print(f"{summary} ({parse_stats_summary(stats)})")


def parse_stats_summary(stats: dict[str, Any]) -> str:
    return (
        f"parsed files={stats.get('files_indexed', 0)}, "
        f"symbols={stats.get('symbols_total', 0)}, "
        f"logs={stats.get('code_logs_total', 0)}, "
        f"edges={stats.get('memory_edges_total', 0)}"
    )


def learn_business(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, args.source)
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid --payload JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        raise SystemExit("--payload must be an object with a files array")
    ts = now_iso()
    files_written = 0
    symbols_written = 0
    logs_written = 0
    with connect(source_project) as conn:
        for file_item in payload["files"]:
            if not isinstance(file_item, dict) or not file_item.get("file_path"):
                raise SystemExit("each file item must include file_path")
            file_path = str(file_item["file_path"])
            language = file_item.get("language") or CODE_EXTENSIONS.get(Path(file_path).suffix.lower()) or "unknown"
            summary = file_item.get("summary") or f"{language} file"
            conn.execute(
                """
                INSERT INTO code_files(
                  project_id, file_path, summary, language,
                  business_summary, business_terms, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, file_path) DO UPDATE SET
                  summary=excluded.summary,
                  language=excluded.language,
                  business_summary=excluded.business_summary,
                  business_terms=excluded.business_terms,
                  updated_at=excluded.updated_at
                """,
                (
                    source_project.project_id,
                    file_path,
                    summary,
                    language,
                    file_item.get("business_summary"),
                    json_list_text(file_item.get("business_terms")),
                    ts,
                ),
            )
            files_written += 1
            conn.execute(
                "DELETE FROM code_symbols WHERE project_id = ? AND file_path = ?",
                (source_project.project_id, file_path),
            )
            conn.execute(
                "DELETE FROM code_log_statements WHERE project_id = ? AND file_path = ?",
                (source_project.project_id, file_path),
            )
            for symbol_item in file_item.get("symbols") or []:
                if not isinstance(symbol_item, dict) or not symbol_item.get("symbol"):
                    continue
                symbol = str(symbol_item["symbol"])
                symbol_type = symbol_item.get("symbol_type") or "symbol"
                symbol_summary = symbol_item.get("summary") or summarize_symbol(file_path, symbol, symbol_type, language)
                conn.execute(
                    """
                    INSERT INTO code_symbols(
                      project_id, file_path, symbol, symbol_type, summary, calls,
                      business_summary, business_terms, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_project.project_id,
                        file_path,
                        symbol,
                        symbol_type,
                        symbol_summary,
                        symbol_item.get("calls") or "",
                        symbol_item.get("business_summary"),
                        json_list_text(symbol_item.get("business_terms")),
                        ts,
                    ),
                )
                symbols_written += 1
            for log_item in file_item.get("logs") or []:
                if not isinstance(log_item, dict) or not log_item.get("message_template"):
                    continue
                conn.execute(
                    """
                    INSERT INTO code_log_statements(
                      project_id, file_path, line, function, level, logger,
                      message_template, raw_statement,
                      business_summary, business_terms, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_project.project_id,
                        file_path,
                        log_item.get("line"),
                        log_item.get("function"),
                        log_item.get("level"),
                        log_item.get("logger"),
                        log_item.get("message_template"),
                        log_item.get("raw_statement"),
                        log_item.get("business_summary"),
                        json_list_text(log_item.get("business_terms")),
                        ts,
                    ),
                )
                logs_written += 1
        rebuild_code_memory_edges(conn, source_project)
        edge_count = conn.execute(
            "SELECT COUNT(*) AS count FROM memory_edges WHERE project_id = ?",
            (source_project.project_id,),
        ).fetchone()["count"]
        conn.commit()
    data = {
        "project_id": project.project_id,
        "source": str(source_project.root),
        "files_written": files_written,
        "symbols_written": symbols_written,
        "logs_written": logs_written,
        "memory_edges_total": edge_count,
    }
    output(data, args.json)


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
    payload = {
        "source": str(source_project.root),
        "entry": str(entry.relative_to(source_project.root)),
        "depth": args.depth,
        "mode": "replace" if args.replace else "merge",
        "files": rel_files,
        "count": len(rel_files),
        "parse_stats": stats,
    }
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


def collect_entry_related_files(project: Project, entry: Path, depth: int) -> list[Path]:
    seen: set[Path] = set()
    frontier: list[tuple[Path, int]] = [(entry.resolve(), 0)]
    while frontier:
        current, current_depth = frontier.pop(0)
        if current in seen:
            continue
        if not current.exists() or not current.is_file() or not language_for(current):
            continue
        seen.add(current)
        if current_depth >= depth:
            continue
        for imported in resolve_project_imports(project, current):
            if imported not in seen:
                frontier.append((imported, current_depth + 1))
    return sorted(seen)


def resolve_project_imports(project: Project, path: Path) -> list[Path]:
    language = language_for(path)
    if not language:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    candidates: list[Path] = []
    if language == "Python":
        candidates.extend(resolve_python_imports(project, path, text))
    elif language in {"TypeScript", "JavaScript"}:
        candidates.extend(resolve_js_imports(project, path, text))
    elif language == "ArkTS":
        candidates.extend(resolve_js_imports(project, path, text, [".ets", ".ts", ".js"]))
        candidates.extend(resolve_arkts_router_targets(project, path, text))
    elif language == "Dart":
        candidates.extend(resolve_quoted_relative_imports(project, path, text, [".dart"]))
    elif language == "Markdown":
        candidates.extend(resolve_markdown_links(project, path, text))
    return [candidate for candidate in candidates if candidate.exists() and language_for(candidate)]


def resolve_python_imports(project: Project, path: Path, text: str) -> list[Path]:
    candidates: list[Path] = []
    for line in text.splitlines():
        line = line.strip()
        rel_match = re.match(r"from\s+(\.+[\w\.]*)\s+import\s+([\w,\s*]+)", line)
        if rel_match:
            module = rel_match.group(1)
            names = [name.strip() for name in rel_match.group(2).split(",") if name.strip() and name.strip() != "*"]
            candidates.extend(resolve_python_module(project, path, module))
            for name in names:
                candidates.extend(resolve_python_module(project, path, f"{module}.{name}"))
            continue
        abs_match = re.match(r"(?:from|import)\s+([A-Za-z_][\w\.]*)", line)
        if abs_match:
            candidates.extend(resolve_python_module(project, path, abs_match.group(1)))
    return candidates


def resolve_python_module(project: Project, path: Path, module: str) -> list[Path]:
    base: Path
    parts: list[str]
    if module.startswith("."):
        dot_count = len(module) - len(module.lstrip("."))
        base = path.parent
        for _ in range(max(dot_count - 1, 0)):
            base = base.parent
        parts = [part for part in module.lstrip(".").split(".") if part]
    else:
        base = project.root
        parts = [part for part in module.split(".") if part]
    module_path = base.joinpath(*parts) if parts else base
    return existing_module_paths(module_path, [".py"])


def existing_module_paths(base: Path, extensions: list[str]) -> list[Path]:
    matches: list[Path] = []
    for ext in extensions:
        file_path = base.with_suffix(ext)
        if file_path.exists():
            matches.append(file_path.resolve())
    for ext in extensions:
        init_path = base / f"__init__{ext}"
        if init_path.exists():
            matches.append(init_path.resolve())
    return matches


def resolve_js_imports(
    project: Project,
    path: Path,
    text: str,
    extensions: list[str] | None = None,
) -> list[Path]:
    imports = re.findall(r"(?:from\s+|import\s*\(|require\s*\()\s*['\"]([^'\"]+)['\"]", text)
    candidates: list[Path] = []
    extensions = extensions or [".ts", ".tsx", ".js", ".jsx"]
    for spec in imports:
        if spec.startswith("."):
            candidates.extend(resolve_relative_spec(path.parent / spec, extensions))
    return candidates


def resolve_arkts_router_targets(project: Project, path: Path, text: str) -> list[Path]:
    candidates: list[Path] = []
    for route, kind in extract_arkts_reference_symbols(text):
        if kind != "route":
            continue
        if route.startswith("$") or route.startswith("@"):
            continue
        if route.startswith("/"):
            route = route.lstrip("/")
        bases = [project.root, arkts_ets_root(path), path.parent]
        for base in bases:
            candidates.extend(resolve_relative_spec(base / route, [".ets"]))
    return candidates


def arkts_ets_root(path: Path) -> Path:
    for parent in [path.parent, *path.parents]:
        if parent.name == "ets":
            return parent
    return path.parent


def resolve_quoted_relative_imports(project: Project, path: Path, text: str, extensions: list[str]) -> list[Path]:
    imports = re.findall(r"import\s+['\"]([^'\"]+)['\"]", text)
    candidates: list[Path] = []
    for spec in imports:
        if spec.startswith("."):
            candidates.extend(resolve_relative_spec(path.parent / spec, extensions))
    return candidates


def resolve_relative_spec(base: Path, extensions: list[str]) -> list[Path]:
    matches: list[Path] = []
    if base.suffix and base.exists():
        matches.append(base.resolve())
    matches.extend(existing_module_paths(base, extensions))
    for ext in extensions:
        index_path = base / f"index{ext}"
        if index_path.exists():
            matches.append(index_path.resolve())
    return matches


def resolve_markdown_links(project: Project, path: Path, text: str) -> list[Path]:
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    candidates: list[Path] = []
    for link in links:
        if "://" in link or link.startswith("#"):
            continue
        target = (path.parent / link.split("#", 1)[0]).resolve()
        try:
            target.relative_to(project.root)
        except ValueError:
            continue
        if target.exists() and target.is_file():
            candidates.append(target)
    return candidates


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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser(
        {
            "init_project": init_project,
            "doctor": doctor,
            "update": update,
            "search": search,
            "context": context,
            "reflect": reflect,
            "reflect_review": reflect_review,
            "list_records": list_records,
            "miss_list": miss_list,
            "miss_status": miss_status,
            "mark_stale": mark_stale,
            "maintain_health": maintain_health,
            "maintain_review": maintain_review,
            "maintain_plan": maintain_plan,
            "maintain_status": maintain_status,
            "maintain_merge": maintain_merge,
            "maintain_promote": maintain_promote,
            "vault_init": vault_init,
            "vault_export": vault_export,
            "vault_index": vault_index,
            "wiki_index": wiki_index,
            "wiki_search": wiki_search,
            "learn_path": learn_path,
            "learn_entry": learn_entry,
            "learn_business": learn_business,
        }
    )
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
