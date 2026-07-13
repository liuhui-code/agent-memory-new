# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from datetime import datetime

from .models import ACTIVE_STATUS
from .storage import connect, ensure_dirs, ensure_initialized, now_iso, resolve_project
from .text import json_list
from .vault_common import (
    VAULT_EDGE_SUMMARY_LIMIT,
    VAULT_EPISODE_EXPORT_LIMIT,
    VAULT_FACT_SUMMARY_LIMIT,
    VAULT_FILE_SUMMARY_LIMIT,
    VAULT_LOG_SUMMARY_LIMIT,
    VAULT_REFLECTION_EXPORT_LIMIT,
    VAULT_SYMBOL_SUMMARY_LIMIT,
    clear_markdown_files,
    frontmatter,
    slugify,
    truncation_notice,
    write_vault_file,
)
from .vault_governance import write_governance_dashboard
from .vault_incident import write_incident_trace_vault_pages

def vault_init(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    ensure_dirs(project)
    vault_index(args)
    print(f"vault initialized at {project.vault_dir}")



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
        incident_traces = conn.execute(
            "SELECT * FROM incident_traces WHERE project_id = ? ORDER BY updated_at DESC, id DESC",
            (project.project_id,),
        ).fetchall()

    exported_episodes = episodes[:VAULT_EPISODE_EXPORT_LIMIT]
    exported_reflections = reflections[:VAULT_REFLECTION_EXPORT_LIMIT]
    clear_markdown_files(project.vault_dir / "Episodes")
    clear_markdown_files(project.vault_dir / "Reflections")

    for row in exported_episodes:
        slug = slugify(row["task"], f"episode-{row['id']}")
        content = frontmatter("episode", project, row["created_at"])
        content += f"# Episode: {row['task']}\n\n"
        content += f"## Summary\n\n{row['summary']}\n\n"
        if row["outcome"]:
            content += f"## Outcome\n\n{row['outcome']}\n"
        write_vault_file(project.vault_dir / "Episodes" / f"{row['id']:04d}-{slug}.md", content)

    for row in exported_reflections:
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
    facts_content += truncation_notice(len(facts), min(len(facts), VAULT_FACT_SUMMARY_LIMIT))
    for row in facts[:VAULT_FACT_SUMMARY_LIMIT]:
        status = row["status"] or ("stale" if row["is_stale"] else ACTIVE_STATUS)
        details = f"{row['source']}, status {status}, confidence {row['confidence']}"
        if row["scope"]:
            details += f", scope {row['scope']}"
        facts_content += f"- #{row['id']} ({details}): {row['fact']}\n"
    write_vault_file(project.vault_dir / "Semantic Facts" / "project-facts.md", facts_content)

    files_content = frontmatter("codebase-wiki", project, now_iso())
    files_content += "# Code Files\n\n"
    files_content += truncation_notice(len(files), min(len(files), VAULT_FILE_SUMMARY_LIMIT))
    for row in files[:VAULT_FILE_SUMMARY_LIMIT]:
        files_content += f"- `{row['file_path']}` ({row['language'] or 'unknown'}): {row['summary'] or ''}\n"
        if row["business_summary"]:
            files_content += f"  - Business: {row['business_summary']}\n"
        terms = json_list(row["business_terms"])
        if terms:
            files_content += f"  - Terms: {', '.join(terms)}\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "files.md", files_content)

    symbols_content = frontmatter("codebase-wiki", project, now_iso())
    symbols_content += "# Code Symbols\n\n"
    symbols_content += truncation_notice(len(symbols), min(len(symbols), VAULT_SYMBOL_SUMMARY_LIMIT))
    for row in symbols[:VAULT_SYMBOL_SUMMARY_LIMIT]:
        symbols_content += f"- `{row['file_path']}` :: `{row['symbol']}` ({row['symbol_type'] or 'symbol'})\n"
        if row["business_summary"]:
            symbols_content += f"  - Business: {row['business_summary']}\n"
        terms = json_list(row["business_terms"])
        if terms:
            symbols_content += f"  - Terms: {', '.join(terms)}\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "symbols.md", symbols_content)

    logs_content = frontmatter("codebase-wiki", project, now_iso())
    logs_content += "# Code Log Statements\n\n"
    logs_content += truncation_notice(len(logs), min(len(logs), VAULT_LOG_SUMMARY_LIMIT))
    for row in logs[:VAULT_LOG_SUMMARY_LIMIT]:
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
    edges_content += truncation_notice(len(edges), min(len(edges), VAULT_EDGE_SUMMARY_LIMIT))
    for row in edges[:VAULT_EDGE_SUMMARY_LIMIT]:
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
    write_incident_trace_vault_pages(project, incident_traces)
    vault_index(args)
    print(f"vault exported to {project.vault_dir}")



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
    content += "- [[Codebase Wiki/incident-traces]]\n"
    content += "- [[Codebase Wiki/query-misses]]\n"
    content += "\n## Governance\n\n"
    content += "- [[Governance/Health]]\n"
    content += "- [[Governance/Review Queue]]\n"
    content += "- [[Governance/Stale Memories]]\n"
    content += "- [[Governance/Merge Candidates]]\n"
    content += "- [[Governance/Low Confidence]]\n"
    content += "- [[Governance/Reflection Quality]]\n"
    content += "- [[Governance/Experience Candidates]]\n"
    content += "- [[Governance/Skill Pattern Candidates]]\n"
    content += "- [[Governance/Incident Strategy Candidates]]\n"
    content += "- [[Governance/Incident Trace Review]]\n"
    content += "- [[Governance/Recurring Incident Fingerprints]]\n"
    content += "- [[Governance/Learned Scopes]]\n"
    content += "- [[Governance/Refresh Drift]]\n"
    content += "- [[Governance/Reflection Reuse]]\n"
    content += "- [[Governance/Semantic Conflicts]]\n"
    content += "- [[Governance/Query Misses]]\n"
    write_vault_file(project.vault_dir / "index.md", content)
