#!/usr/bin/env python3
# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Local Agent Memory runtime.

This is the stable script API used by Agent Memory skills.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_memory_runtime.cli import build_parser
from agent_memory_runtime.code_wiki import (
    learn_business,
    learn_entry,
    learn_path,
    wiki_index,
    wiki_search,
)
from agent_memory_runtime.governance import (
    maintain_health,
    maintain_merge,
    maintain_plan,
    maintain_promote,
    maintain_review,
    maintain_status,
    mark_stale,
    reflect_review,
)
from agent_memory_runtime.models import (
    Project,
    REQUIRED_TABLES,
)
from agent_memory_runtime.query import (
    limited_search,
    limited_context,
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
    reflection_list_text,
)
from agent_memory_runtime.vault import (
    vault_export,
    vault_index,
    vault_init,
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
    data = limited_search(
        project,
        args.query,
        cursor=args.cursor,
        per_type_limit=args.per_type_limit,
        aggregate_limit=args.aggregate_limit,
    )
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
        "hidden_assumptions": reflection_list_text(payload.get("hidden_assumptions")),
        "negative_preconditions": reflection_list_text(payload.get("negative_preconditions")),
        "verification_method": reflection_value(args, payload, "verification_method"),
        "reuse_feedback": reflection_value(args, payload, "reuse_feedback"),
        "source_cases": reflection_list_text(payload.get("source_cases")),
        "skill_candidate": reflection_value(args, payload, "skill_candidate"),
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
              what_worked, what_failed, hidden_assumptions, negative_preconditions,
              verification_method, reuse_feedback, source_cases, skill_candidate,
              scope, evidence, confidence, trigger_condition, anti_pattern,
              repair_action, applies_to, does_not_apply_to, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                data["hidden_assumptions"],
                data["negative_preconditions"],
                data["verification_method"],
                data["reuse_feedback"],
                data["source_cases"],
                data["skill_candidate"],
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
        data["id"] = cur.lastrowid
        if args.used_reflection_ids:
            ids = parse_ids(args.used_reflection_ids)
            outcome = args.reflection_outcome or "used"
            conn.execute(
                f"""
                UPDATE reflections
                SET applied_count = COALESCE(applied_count, 0) + 1,
                    last_applied_at = ?,
                    last_outcome = ?
                WHERE project_id = ? AND id IN ({','.join('?' for _ in ids)})
                """,
                [data["created_at"], outcome, project.project_id, *ids],
            )
            for reused_reflection_id in ids:
                conn.execute(
                    """
                    INSERT INTO reflection_reuse_events(
                      project_id, reused_reflection_id, applying_reflection_id,
                      outcome, task, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project.project_id,
                        reused_reflection_id,
                        data["id"],
                        outcome,
                        data["task"],
                        data["created_at"],
                    ),
                )
        conn.commit()
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


def main(argv: list[str] | None = None) -> int:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
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
