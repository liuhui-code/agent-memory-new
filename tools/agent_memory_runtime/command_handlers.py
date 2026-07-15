# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .models import Project, REQUIRED_TABLES
from .performance_scoring import append_performance_sample, build_performance_sample, estimate_payload_tokens, monotonic_ms
from .query import limited_context, limited_search, record_query_miss_if_empty
from .records import output, row_dict, table_for_type
from .runtime_logs import analyze_runtime_log
from .storage import connect, create_schema, ensure_dirs, ensure_initialized, now_iso, resolve_project, upsert_project, write_config, write_global_config
from .usage_samples import record_query_usage, record_runtime_log_usage
from .vault import vault_index

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
    started_ms = monotonic_ms()
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = limited_search(
        project,
        args.query,
        cursor=args.cursor,
        per_type_limit=args.per_type_limit,
        aggregate_limit=args.aggregate_limit,
    )
    record_query_usage(project, "search", args.query, data)
    record_query_miss_if_empty(project, "search", args.query, data)
    append_query_performance_sample(project, "search", started_ms, data)
    output(data, args.json)



def context(args: argparse.Namespace) -> None:
    started_ms = monotonic_ms()
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = limited_context(project, args.query)
    record_query_usage(project, "context", args.query, data)
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_context.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    append_query_performance_sample(project, "context", started_ms, data)
    output(data, args.json)



def append_query_performance_sample(project: Project, operation: str, started_ms: float, data: dict[str, Any]) -> None:
    append_performance_sample(
        project,
        build_performance_sample(
            project,
            operation,
            monotonic_ms() - started_ms,
            result_counts(data),
            estimate_payload_tokens(data),
        ),
    )



def result_counts(data: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, value in data.items():
        if isinstance(value, list):
            counts[key] = len(value)
        elif isinstance(value, dict) and key == "result_counts":
            counts.update({str(name): int(count or 0) for name, count in value.items()})
    return counts



def analyze_runtime_log_command(args: argparse.Namespace) -> None:
    from .diagnosis_hypotheses import persist_hypothesis_ledger

    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    log_file = Path(args.log_file).expanduser().resolve()
    if not log_file.exists():
        raise SystemExit(f"log file not found: {log_file}")
    data = analyze_runtime_log(
        project,
        args.query,
        log_file,
        before=args.before_lines,
        after=args.after_lines,
        slice_limit=args.slice_limit,
    )
    record_runtime_log_usage(project, args.query, str(log_file), data)
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_runtime_log_analysis.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    persist_hypothesis_ledger(project, data["hypothesis_ledger"])
    output(data, args.json)



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



def conflict_status(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    ts = now_iso()
    with connect(project) as conn:
        conn.execute(
            """
            UPDATE semantic_conflicts
            SET status = ?, resolution = ?, decision_note = ?, replacement_source = ?, reviewed_at = ?
            WHERE project_id = ? AND id = ?
            """,
            (args.status, args.resolution, args.decision_note, args.replacement_source, ts, project.project_id, args.id),
        )
        conn.commit()
    print(f"semantic conflict #{args.id} status set to {args.status}")



def conflict_apply(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    ts = now_iso()
    with connect(project) as conn:
        conflict = conn.execute(
            """
            SELECT *
            FROM semantic_conflicts
            WHERE project_id = ? AND id = ?
            LIMIT 1
            """,
            (project.project_id, args.id),
        ).fetchone()
        if not conflict:
            raise SystemExit(f"semantic conflict #{args.id} not found")
        if not str(conflict["incoming"] or "").strip():
            raise SystemExit("semantic conflict has no incoming summary to apply")
        entity_type = conflict["entity_type"] or "code_file"
        target = str(conflict["target"])
        if entity_type == "code_file":
            row = conn.execute(
                """
                SELECT id
                FROM code_files
                WHERE project_id = ? AND file_path = ?
                """,
                (project.project_id, target),
            ).fetchall()
            if len(row) != 1:
                raise SystemExit(f"semantic conflict target matched {len(row)} rows, expected 1")
            conn.execute(
                """
                UPDATE code_files
                SET business_summary = ?, updated_at = ?
                WHERE project_id = ? AND file_path = ?
                """,
                (conflict["incoming"], ts, project.project_id, target),
            )
        elif entity_type == "code_symbol":
            file_path, _, symbol = target.partition("::")
            rows = conn.execute(
                """
                SELECT id
                FROM code_symbols
                WHERE project_id = ? AND file_path = ? AND symbol = ?
                """,
                (project.project_id, file_path, symbol),
            ).fetchall()
            if len(rows) != 1:
                raise SystemExit(f"semantic conflict target matched {len(rows)} rows, expected 1")
            conn.execute(
                """
                UPDATE code_symbols
                SET business_summary = ?, updated_at = ?
                WHERE project_id = ? AND file_path = ? AND symbol = ?
                """,
                (conflict["incoming"], ts, project.project_id, file_path, symbol),
            )
        elif entity_type == "code_log_statement":
            file_path, _, message_template = target.partition("::")
            rows = conn.execute(
                """
                SELECT id
                FROM code_log_statements
                WHERE project_id = ? AND file_path = ? AND message_template = ?
                """,
                (project.project_id, file_path, message_template),
            ).fetchall()
            if len(rows) != 1:
                raise SystemExit(f"semantic conflict target matched {len(rows)} rows, expected 1")
            conn.execute(
                """
                UPDATE code_log_statements
                SET business_summary = ?, updated_at = ?
                WHERE project_id = ? AND file_path = ? AND message_template = ?
                """,
                (conflict["incoming"], ts, project.project_id, file_path, message_template),
            )
        else:
            raise SystemExit(f"unsupported semantic conflict entity type: {entity_type}")
        resolution = args.resolution or "applied incoming summary after review"
        conn.execute(
            """
            UPDATE semantic_conflicts
            SET status = 'applied', resolution = ?, decision_note = ?, replacement_source = ?, reviewed_at = ?
            WHERE project_id = ? AND id = ?
            """,
            (resolution, args.decision_note, args.replacement_source, ts, project.project_id, args.id),
        )
        conn.commit()
    print(f"semantic conflict #{args.id} applied")
