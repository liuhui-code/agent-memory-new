# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from .governance import duplicate_candidates, is_complete_experience_candidate, reflection_quality_issues
from .models import ACTIVE_STATUS, Project
from .query import normalize_query_miss
from .records import row_dict
from .storage import connect, ensure_dirs, ensure_initialized, now_iso, resolve_project
from .text import json_list


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
        reflection_reuse_events = conn.execute(
            "SELECT * FROM reflection_reuse_events WHERE project_id = ? ORDER BY id DESC",
            (project.project_id,),
        ).fetchall()
        semantic_conflicts = conn.execute(
            "SELECT * FROM semantic_conflicts WHERE project_id = ? ORDER BY observed_at DESC, id DESC",
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

    write_governance_dashboard(project, facts, reflections, episodes, query_misses, reflection_reuse_events, semantic_conflicts)
    vault_index(args)
    print(f"vault exported to {project.vault_dir}")


def write_governance_dashboard(
    project: Project,
    facts: list[sqlite3.Row],
    reflections: list[sqlite3.Row],
    episodes: list[sqlite3.Row],
    query_misses: list[sqlite3.Row],
    reflection_reuse_events: list[sqlite3.Row],
    semantic_conflicts: list[sqlite3.Row],
) -> None:
    fact_rows = [row_dict(row) for row in facts]
    reflection_rows = [row_dict(row) for row in reflections]
    episode_rows = [row_dict(row) for row in episodes]
    query_miss_rows = [row_dict(row) for row in query_misses]
    reflection_reuse_rows = [row_dict(row) for row in reflection_reuse_events]
    semantic_conflict_rows = [row_dict(row) for row in semantic_conflicts]
    open_semantic_conflicts = [row for row in semantic_conflict_rows if row.get("status") == "open"]
    open_file_conflicts = [row for row in open_semantic_conflicts if row.get("entity_type") == "code_file"]
    open_symbol_conflicts = [row for row in open_semantic_conflicts if row.get("entity_type") == "code_symbol"]
    open_log_conflicts = [row for row in open_semantic_conflicts if row.get("entity_type") == "code_log_statement"]
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
    health += f"- Open semantic conflicts: {len(open_semantic_conflicts)}\n"
    health += f"- Open file semantic conflicts: {len(open_file_conflicts)}\n"
    health += f"- Open symbol semantic conflicts: {len(open_symbol_conflicts)}\n"
    health += f"- Open log semantic conflicts: {len(open_log_conflicts)}\n"
    write_vault_file(project.vault_dir / "Governance" / "Health.md", health)

    review = header + "# Review Queue\n\n" + notice
    review += "## Unreviewed Reflections\n\n"
    for row in unreviewed_reflections[:30]:
        review += f"- reflection #{row['id']}: {row['task']}\n"
    review += "\n## Unreviewed Episodes\n\n"
    for row in episode_rows[:30]:
        if not row.get("reviewed_at") and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS:
            review += f"- episode #{row['id']}: {row['task']}\n"
    review += "\n## Open Semantic Conflicts\n\n"
    for row in semantic_conflict_rows[:30]:
        if row.get("status") == "open":
            review += f"- conflict #{row['id']}: {row['target']}\n"
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

    experience_candidates = [
        row for row in active_reflections
        if is_complete_experience_candidate(row)
    ]
    candidates_doc = header + "# Experience Candidates\n\n" + notice
    candidates_doc += "These reflections have enough structure to review as reusable experience. They are not accepted experience until reviewed.\n\n"
    for row in experience_candidates[:50]:
        candidates_doc += f"## Reflection #{row['id']}: {row['task']}\n\n"
        if row.get("skill_candidate"):
            candidates_doc += f"- Skill candidate: `{row['skill_candidate']}`\n"
        if row.get("problem"):
            candidates_doc += f"- Problem: {row['problem']}\n"
        if row.get("trigger_condition"):
            candidates_doc += f"- Trigger: {row['trigger_condition']}\n"
        if row.get("verification_method"):
            candidates_doc += f"- Verification: {row['verification_method']}\n"
        if row.get("reuse_feedback"):
            candidates_doc += f"- Reuse feedback: {row['reuse_feedback']}\n"
        source_cases = json_list(row.get("source_cases"))
        if source_cases:
            candidates_doc += "- Source cases:\n"
            for item in source_cases:
                candidates_doc += f"  - {item}\n"
        hidden_assumptions = json_list(row.get("hidden_assumptions"))
        if hidden_assumptions:
            candidates_doc += "- Hidden assumptions:\n"
            for item in hidden_assumptions:
                candidates_doc += f"  - {item}\n"
        negative_preconditions = json_list(row.get("negative_preconditions"))
        if negative_preconditions:
            candidates_doc += "- Negative preconditions:\n"
            for item in negative_preconditions:
                candidates_doc += f"  - {item}\n"
        candidates_doc += "\n"
    write_vault_file(project.vault_dir / "Governance" / "Experience Candidates.md", candidates_doc)

    reuse_doc = header + "# Reflection Reuse\n\n" + notice
    reuse_doc += "These events show when a later reflection reused an earlier reflection and whether it helped.\n\n"
    for row in reflection_reuse_rows[:50]:
        reuse_doc += (
            f"- reuse event #{row['id']}: reused reflection #{row['reused_reflection_id']} "
            f"-> applying reflection #{row['applying_reflection_id']} "
            f"({row['outcome']})"
        )
        if row.get("task"):
            reuse_doc += f": {row['task']}"
        reuse_doc += "\n"
    write_vault_file(project.vault_dir / "Governance" / "Reflection Reuse.md", reuse_doc)

    conflicts_doc = header + "# Semantic Conflicts\n\n" + notice
    conflicts_doc += "These conflicts capture incompatible incoming business summaries that require source-grounded review before replacement.\n\n"
    for row in semantic_conflict_rows[:50]:
        conflicts_doc += f"## Conflict #{row['id']}: {row['target']}\n\n"
        conflicts_doc += f"- Field: {row['field']}\n"
        conflicts_doc += f"- Entity type: {row.get('entity_type') or 'code_file'}\n"
        conflicts_doc += f"- Status: {row.get('status') or 'open'}\n"
        conflicts_doc += f"- Source command: {row['source_command']}\n"
        conflicts_doc += f"- Observed at: {row['observed_at']}\n"
        if row.get("resolution"):
            conflicts_doc += f"- Resolution: {row['resolution']}\n"
        if row.get("decision_note"):
            conflicts_doc += f"- Decision note: {row['decision_note']}\n"
        if row.get("replacement_source"):
            conflicts_doc += f"- Replacement source: {row['replacement_source']}\n"
        conflicts_doc += f"\n### Existing\n\n{row.get('existing') or ''}\n\n"
        conflicts_doc += f"### Incoming\n\n{row.get('incoming') or ''}\n\n"
    write_vault_file(project.vault_dir / "Governance" / "Semantic Conflicts.md", conflicts_doc)

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
    content += "- [[Governance/Experience Candidates]]\n"
    content += "- [[Governance/Reflection Reuse]]\n"
    content += "- [[Governance/Semantic Conflicts]]\n"
    content += "- [[Governance/Query Misses]]\n"
    write_vault_file(project.vault_dir / "index.md", content)
