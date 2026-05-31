# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import sqlite3
from typing import Any

from .models import ACTIVE_STATUS, GOVERNANCE_COLUMNS, Project, VALID_MEMORY_STATUSES
from .records import output, parse_ids, row_dict, table_for_type
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .text import tokenize


def mark_stale(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    table = table_for_type(args.type)
    if table not in {"semantic_facts", "reflections"}:
        raise SystemExit("mark-stale supports semantic and reflection records")
    with connect(project) as conn:
        conn.execute(
            f"UPDATE {table} SET is_stale = 1, status = 'stale' WHERE project_id = ? AND id = ?",
            (project.project_id, args.id),
        )
        conn.commit()
    print(f"{args.type} #{args.id} marked stale")


def memory_text(row: dict[str, Any], kind: str) -> str:
    if kind == "semantic":
        return str(row.get("fact") or "")
    if kind == "reflection":
        return " ".join(
            str(row.get(key) or "")
            for key in ("task", "summary", "mistake", "lesson", "future_rule")
        )
    if kind == "episode":
        return " ".join(str(row.get(key) or "") for key in ("task", "summary", "outcome"))
    return ""


def token_set(text: str) -> set[str]:
    return {token for token in tokenize(text) if len(token) > 1}


def duplicate_candidates(rows: list[dict[str, Any]], kind: str, limit: int = 10) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    prepared = [(row, token_set(memory_text(row, kind))) for row in rows]
    for index, (left, left_tokens) in enumerate(prepared):
        if not left_tokens:
            continue
        for right, right_tokens in prepared[index + 1 :]:
            if not right_tokens:
                continue
            overlap = len(left_tokens & right_tokens)
            union = len(left_tokens | right_tokens)
            similarity = overlap / union if union else 0.0
            if similarity >= 0.55:
                candidates.append(
                    {
                        "type": kind,
                        "ids": [left["id"], right["id"]],
                        "similarity": round(similarity, 3),
                        "reason": "high token overlap",
                        "suggested_action": "review or merge",
                    }
                )
    candidates.sort(key=lambda item: item["similarity"], reverse=True)
    return candidates[:limit]


def fetch_memory_rows(conn: sqlite3.Connection, project: Project, kind: str, active_only: bool = True) -> list[dict[str, Any]]:
    table = table_for_type(kind)
    status_filter = "AND COALESCE(status, 'active') = 'active'" if active_only else ""
    stale_filter = "AND COALESCE(is_stale, 0) = 0" if table in {"semantic_facts", "reflections"} and active_only else ""
    rows = conn.execute(
        f"""
        SELECT * FROM {table}
        WHERE project_id = ? {status_filter} {stale_filter}
        ORDER BY id DESC
        """,
        (project.project_id,),
    ).fetchall()
    return [row_dict(row) for row in rows]


def maintain_health(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    with connect(project) as conn:
        semantic_rows = fetch_memory_rows(conn, project, "semantic", active_only=False)
        reflection_rows = fetch_memory_rows(conn, project, "reflection", active_only=False)
        episode_rows = fetch_memory_rows(conn, project, "episode", active_only=False)
        code_files_missing_business_terms = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM code_files
            WHERE project_id = ?
              AND (business_terms IS NULL OR business_terms = '' OR business_terms = '[]')
            """,
            (project.project_id,),
        ).fetchone()["count"]
        code_symbols_missing_business_terms = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM code_symbols
            WHERE project_id = ?
              AND (business_terms IS NULL OR business_terms = '' OR business_terms = '[]')
            """,
            (project.project_id,),
        ).fetchone()["count"]
        code_logs_missing_business_terms = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM code_log_statements
            WHERE project_id = ?
              AND (business_terms IS NULL OR business_terms = '' OR business_terms = '[]')
            """,
            (project.project_id,),
        ).fetchone()["count"]

    semantic_active = [row for row in semantic_rows if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")]
    reflection_active = [row for row in reflection_rows if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")]
    duplicate_count = len(duplicate_candidates(semantic_active, "semantic")) + len(duplicate_candidates(reflection_active, "reflection"))
    low_confidence_count = sum(1 for row in semantic_rows + reflection_rows if float(row.get("confidence") or 0.8) < 0.6)
    stale_count = sum(1 for row in semantic_rows + reflection_rows if row.get("is_stale") or row.get("status") == "stale")
    unreviewed_reflections = sum(
        1
        for row in reflection_rows
        if not row.get("reviewed_at")
        and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS
        and not row.get("is_stale")
    )

    recommended_actions: list[str] = []
    if stale_count:
        recommended_actions.append("Review stale memories and archive, merge, or refresh them.")
    if duplicate_count:
        recommended_actions.append("Run maintain-review and merge duplicate candidates.")
    if low_confidence_count:
        recommended_actions.append("Verify low-confidence memories against source files or user instructions.")
    if unreviewed_reflections:
        recommended_actions.append("Review reflections and promote durable lessons into semantic facts.")
    if code_files_missing_business_terms or code_symbols_missing_business_terms or code_logs_missing_business_terms:
        recommended_actions.append("Enrich learned code with business summaries and terms through agent-memory-learn.")

    data = {
        "project_id": project.project_id,
        "counts": {
            "semantic_facts": len(semantic_rows),
            "reflections": len(reflection_rows),
            "episodes": len(episode_rows),
            "stale": stale_count,
            "low_confidence": low_confidence_count,
            "duplicate_candidates": duplicate_count,
            "unreviewed_reflections": unreviewed_reflections,
            "code_files_missing_business_terms": code_files_missing_business_terms,
            "code_symbols_missing_business_terms": code_symbols_missing_business_terms,
            "code_logs_missing_business_terms": code_logs_missing_business_terms,
        },
        "recommended_actions": recommended_actions,
    }
    output(data, args.json)


def maintain_review(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = build_review_data(project, args.limit)
    output(data, args.json)


def reflect_review(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = build_reflect_review_data(project, args.limit)
    output(data, args.json)


def build_reflect_review_data(project: Project, limit: int) -> dict[str, Any]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT * FROM reflections
            WHERE project_id = ?
              AND COALESCE(status, 'active') = 'active'
              AND COALESCE(is_stale, 0) = 0
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
    items = []
    for row in rows:
        item = row_dict(row)
        issues = reflection_quality_issues(item)
        if issues:
            action = reflection_quality_action(issues)
            items.append(
                {
                    "id": item["id"],
                    "task": item["task"],
                    "issues": issues,
                    "suggested_action": action,
                    "reason": reflection_quality_reason(issues),
                }
            )
    return {"project_id": project.project_id, "reflections": items}


def reflection_quality_issues(row: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not row.get("scope"):
        issues.append("missing_scope")
    if not row.get("evidence"):
        issues.append("missing_evidence")
    if not row.get("future_rule"):
        issues.append("missing_future_rule")
    if not row.get("trigger_condition"):
        issues.append("missing_trigger_condition")
    if not row.get("repair_action"):
        issues.append("missing_repair_action")
    if not row.get("hidden_assumptions"):
        issues.append("missing_hidden_assumptions")
    if not row.get("negative_preconditions"):
        issues.append("missing_negative_preconditions")
    if not row.get("verification_method"):
        issues.append("missing_verification_method")
    if not row.get("reuse_feedback"):
        issues.append("missing_reuse_feedback")
    if is_generic_reflection_text(row.get("future_rule") or ""):
        issues.append("future_rule_too_generic")
    if is_generic_reflection_text(row.get("lesson") or ""):
        issues.append("lesson_too_generic")
    if int(row.get("applied_count") or 0) == 0:
        issues.append("never_applied")
    if row.get("last_outcome") == "misleading":
        issues.append("misleading_outcome")
    return issues


def is_generic_reflection_text(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return False
    generic_phrases = {
        "be careful",
        "be careful.",
        "do better",
        "do better.",
        "注意",
        "小心",
        "以后注意",
    }
    return normalized in generic_phrases or len(tokenize(normalized)) <= 2


def reflection_quality_reason(issues: list[str]) -> str:
    if "misleading_outcome" in issues:
        return "reflection was previously misleading"
    if reflection_quality_action(issues) == "observe":
        return "reflection has not been reused yet"
    return "reflection is not actionable enough for future tasks"


def reflection_quality_action(issues: list[str]) -> str:
    if "misleading_outcome" in issues:
        return "mark_stale"
    structural_issues = set(issues) - {"never_applied"}
    if structural_issues:
        return "rewrite"
    return "observe"


EXPERIENCE_CANDIDATE_FIELDS = [
    "hidden_assumptions",
    "negative_preconditions",
    "verification_method",
    "reuse_feedback",
    "source_cases",
]


def is_complete_experience_candidate(row: dict[str, Any]) -> bool:
    issues = set(reflection_quality_issues(row)) - {"never_applied"}
    if issues:
        return False
    return all(row.get(field) for field in EXPERIENCE_CANDIDATE_FIELDS)


def build_review_data(project: Project, limit: int) -> dict[str, Any]:
    with connect(project) as conn:
        semantic_rows = fetch_memory_rows(conn, project, "semantic", active_only=False)
        reflection_rows = fetch_memory_rows(conn, project, "reflection", active_only=False)
        episode_rows = fetch_memory_rows(conn, project, "episode", active_only=False)

    semantic_active = [
        row for row in semantic_rows
        if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")
    ]
    reflection_active = [
        row for row in reflection_rows
        if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")
    ]
    return {
        "stale_memories": [
            row for row in semantic_rows + reflection_rows
            if row.get("is_stale") or row.get("status") == "stale"
        ][:limit],
        "low_confidence": [
            row for row in semantic_rows + reflection_rows
            if float(row.get("confidence") or 0.8) < 0.6
        ][:limit],
        "unreviewed_reflections": [
            row for row in reflection_rows
            if not row.get("reviewed_at")
            and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS
            and not row.get("is_stale")
        ][:limit],
        "unreviewed_episodes": [
            row for row in episode_rows
            if not row.get("reviewed_at") and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS
        ][:limit],
        "duplicate_candidates": (
            duplicate_candidates(semantic_active, "semantic", limit)
            + duplicate_candidates(reflection_active, "reflection", limit)
        )[:limit],
    }


def maintain_plan(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    review = build_review_data(project, args.limit)
    reflection_quality = build_reflect_review_data(project, args.limit)
    query_misses = build_query_miss_data(project, args.limit)
    semantic_gap_targets = build_semantic_gap_targets(project)
    learn_business_payload_template = build_learn_business_payload_template(project)
    actions: list[dict[str, Any]] = []

    for row in review["stale_memories"]:
        kind = "semantic" if "fact" in row else "reflection"
        reason = row.get("stale_reason") or "stale memory should be archived, refreshed, or merged"
        actions.append(
            {
                "action": "archive",
                "type": kind,
                "id": row["id"],
                "reason": reason,
                "risk": "low",
                "requires_confirmation": True,
                "command": (
                    "python tools/agent_memory.py maintain-status "
                    f"--project . --type {kind} --id {row['id']} --status archived "
                    f"--reason {json.dumps(reason, ensure_ascii=False)}"
                ),
            }
        )

    for candidate in review["duplicate_candidates"]:
        actions.append(
            {
                "action": "review",
                "type": candidate["type"],
                "ids": candidate["ids"],
                "reason": candidate["reason"],
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
            }
        )

    for row in review["low_confidence"]:
        kind = "semantic" if "fact" in row else "reflection"
        actions.append(
            {
                "action": "verify",
                "type": kind,
                "id": row["id"],
                "reason": "low-confidence memory needs source verification",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
            }
        )

    for item in reflection_quality["reflections"]:
        if item["suggested_action"] == "mark_stale":
            reason = item["reason"]
            actions.append(
                {
                    "action": "mark_stale",
                    "type": "reflection",
                    "id": item["id"],
                    "reason": reason,
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": (
                        "python tools/agent_memory.py maintain-status "
                        f"--project . --type reflection --id {item['id']} --status stale "
                        f"--reason {json.dumps(reason, ensure_ascii=False)}"
                    ),
                }
            )
        elif item["suggested_action"] == "rewrite":
            actions.append(
                {
                    "action": "rewrite_reflection",
                    "type": "reflection",
                    "id": item["id"],
                    "reason": ", ".join(item["issues"]),
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": None,
                }
            )

    for row in review["unreviewed_reflections"]:
        if is_complete_experience_candidate(row):
            actions.append(
                {
                    "action": "promote_experience_candidate",
                    "type": "reflection",
                    "id": row["id"],
                    "reason": "reflection has enough structure to review as an experience candidate",
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": None,
                    "candidate_fields": EXPERIENCE_CANDIDATE_FIELDS,
                    "skill_candidate": row.get("skill_candidate"),
                    "verification_method": row.get("verification_method"),
                    "source_cases": row.get("source_cases"),
                }
            )
        else:
            actions.append(
                {
                    "action": "promote_or_mark_reviewed",
                    "type": "reflection",
                    "id": row["id"],
                    "reason": "unreviewed reflection may contain a durable lesson",
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": None,
                }
            )

    for row in review["unreviewed_episodes"]:
        actions.append(
            {
                "action": "promote_or_archive",
                "type": "episode",
                "id": row["id"],
                "reason": "unreviewed episode may contain durable project knowledge",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
            }
        )

    for row in query_misses:
        actions.append(
            {
                "action": "review_query_miss",
                "type": "query_miss",
                "id": row["id"],
                "query": row["query"],
                "source": row["source"],
                "miss_count": row.get("miss_count") or 1,
                "last_seen_at": row.get("last_seen_at") or row.get("created_at"),
                "reason": "query had no memory or wiki matches",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                "suggested_fixes": [
                    "learn_missing_scope",
                    "add_business_terms",
                    "rewrite_reflection",
                    "ignore_noise",
                ],
                "semantic_gap_targets": semantic_gap_targets,
                "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
                "learn_business_payload_template": learn_business_payload_template,
                "workflow_steps": semantic_enrichment_workflow_steps(),
            }
        )

    if any(semantic_gap_targets.values()):
        actions.append(
            {
                "action": "add_business_terms",
                "type": "code_memory",
                "id": None,
                "reason": "learned code records are missing business summaries or business terms",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                "semantic_gap_targets": semantic_gap_targets,
                "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
                "learn_business_payload_template": learn_business_payload_template,
                "workflow_steps": semantic_enrichment_workflow_steps(),
            }
        )

    data = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "summary": {
            "stale": len(review["stale_memories"]),
            "duplicate_candidates": len(review["duplicate_candidates"]),
            "low_confidence": len(review["low_confidence"]),
            "unreviewed_reflections": len(review["unreviewed_reflections"]),
            "unreviewed_episodes": len(review["unreviewed_episodes"]),
            "reflection_quality_issues": len(reflection_quality["reflections"]),
            "open_query_misses": len(query_misses),
        },
        "actions": actions,
        "advisory_notice": "maintain-plan only proposes actions. Execute changes only after user confirmation.",
    }
    output(data, args.json)


def build_query_miss_data(project: Project, limit: int) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT * FROM query_misses
            WHERE project_id = ? AND status = 'open'
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
    return [row_dict(row) for row in rows]


def build_semantic_gap_targets(project: Project, limit_per_group: int = 5) -> dict[str, list[str]]:
    with connect(project) as conn:
        files_missing_business_summary = [
            row["file_path"]
            for row in conn.execute(
                """
                SELECT file_path
                FROM code_files
                WHERE project_id = ?
                  AND (business_summary IS NULL OR TRIM(business_summary) = '')
                ORDER BY file_path
                LIMIT ?
                """,
                (project.project_id, limit_per_group),
            ).fetchall()
        ]
        files_missing_business_terms = [
            row["file_path"]
            for row in conn.execute(
                """
                SELECT file_path
                FROM code_files
                WHERE project_id = ?
                  AND (business_terms IS NULL OR business_terms = '' OR business_terms = '[]')
                ORDER BY file_path
                LIMIT ?
                """,
                (project.project_id, limit_per_group),
            ).fetchall()
        ]
        symbols_missing_business_summary = [
            f"{row['file_path']}::{row['symbol']}"
            for row in conn.execute(
                """
                SELECT file_path, symbol
                FROM code_symbols
                WHERE project_id = ?
                  AND (business_summary IS NULL OR TRIM(business_summary) = '')
                ORDER BY file_path, symbol
                LIMIT ?
                """,
                (project.project_id, limit_per_group),
            ).fetchall()
        ]
        symbols_missing_business_terms = [
            f"{row['file_path']}::{row['symbol']}"
            for row in conn.execute(
                """
                SELECT file_path, symbol
                FROM code_symbols
                WHERE project_id = ?
                  AND (business_terms IS NULL OR business_terms = '' OR business_terms = '[]')
                ORDER BY file_path, symbol
                LIMIT ?
                """,
                (project.project_id, limit_per_group),
            ).fetchall()
        ]
        logs_missing_business_summary = [
            f"{row['file_path']}::{row['message_template']}"
            for row in conn.execute(
                """
                SELECT file_path, message_template
                FROM code_log_statements
                WHERE project_id = ?
                  AND (business_summary IS NULL OR TRIM(business_summary) = '')
                ORDER BY file_path, message_template
                LIMIT ?
                """,
                (project.project_id, limit_per_group),
            ).fetchall()
        ]
        logs_missing_business_terms = [
            f"{row['file_path']}::{row['message_template']}"
            for row in conn.execute(
                """
                SELECT file_path, message_template
                FROM code_log_statements
                WHERE project_id = ?
                  AND (business_terms IS NULL OR business_terms = '' OR business_terms = '[]')
                ORDER BY file_path, message_template
                LIMIT ?
                """,
                (project.project_id, limit_per_group),
            ).fetchall()
        ]
    return {
        "files_missing_business_summary": files_missing_business_summary,
        "files_missing_business_terms": files_missing_business_terms,
        "symbols_missing_business_summary": symbols_missing_business_summary,
        "symbols_missing_business_terms": symbols_missing_business_terms,
        "logs_missing_business_summary": logs_missing_business_summary,
        "logs_missing_business_terms": logs_missing_business_terms,
    }


def build_learn_business_payload_template(project: Project, limit_files: int = 5) -> dict[str, Any]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT file_path
            FROM (
              SELECT file_path
              FROM code_files
              WHERE project_id = ?
                AND (
                  business_summary IS NULL OR TRIM(business_summary) = ''
                  OR business_terms IS NULL OR business_terms = '' OR business_terms = '[]'
                )
              UNION
              SELECT file_path
              FROM code_symbols
              WHERE project_id = ?
                AND (
                  business_summary IS NULL OR TRIM(business_summary) = ''
                  OR business_terms IS NULL OR business_terms = '' OR business_terms = '[]'
                )
              UNION
              SELECT file_path
              FROM code_log_statements
              WHERE project_id = ?
                AND (
                  business_summary IS NULL OR TRIM(business_summary) = ''
                  OR business_terms IS NULL OR business_terms = '' OR business_terms = '[]'
                )
            )
            ORDER BY file_path
            LIMIT ?
            """,
            (project.project_id, project.project_id, project.project_id, limit_files),
        ).fetchall()
        file_paths = [row["file_path"] for row in rows]
        files: list[dict[str, Any]] = []
        for file_path in file_paths:
            file_row = conn.execute(
                """
                SELECT file_path, summary, language, business_summary, business_terms
                FROM code_files
                WHERE project_id = ? AND file_path = ?
                """,
                (project.project_id, file_path),
            ).fetchone()
            file_item = {
                "file_path": file_path,
                "summary": file_row["summary"] if file_row else "",
                "business_summary": "" if not file_row or not str(file_row["business_summary"] or "").strip() else "",
                "business_terms": [],
                "symbols": [],
                "logs": [],
            }
            symbol_rows = conn.execute(
                """
                SELECT symbol, symbol_type, summary, business_summary, business_terms
                FROM code_symbols
                WHERE project_id = ? AND file_path = ?
                  AND (
                    business_summary IS NULL OR TRIM(business_summary) = ''
                    OR business_terms IS NULL OR business_terms = '' OR business_terms = '[]'
                  )
                ORDER BY symbol
                """,
                (project.project_id, file_path),
            ).fetchall()
            for row in symbol_rows:
                file_item["symbols"].append(
                    {
                        "symbol": row["symbol"],
                        "symbol_type": row["symbol_type"],
                        "summary": row["summary"],
                        "business_summary": "",
                        "business_terms": [],
                    }
                )
            log_rows = conn.execute(
                """
                SELECT message_template, function, level, logger, raw_statement, business_summary, business_terms
                FROM code_log_statements
                WHERE project_id = ? AND file_path = ?
                  AND (
                    business_summary IS NULL OR TRIM(business_summary) = ''
                    OR business_terms IS NULL OR business_terms = '' OR business_terms = '[]'
                  )
                ORDER BY message_template
                """,
                (project.project_id, file_path),
            ).fetchall()
            for row in log_rows:
                file_item["logs"].append(
                    {
                        "message_template": row["message_template"],
                        "function": row["function"],
                        "level": row["level"],
                        "logger": row["logger"],
                        "raw_statement": row["raw_statement"],
                        "business_summary": "",
                        "business_terms": [],
                    }
                )
            files.append(file_item)
    return {"files": files}


def semantic_enrichment_workflow_steps() -> list[str]:
    return [
        "Read the listed files, symbols, and logs in current source.",
        "Fill missing business_summary and business_terms in learn_business_payload_template.",
        "Write the completed payload with learn-business.",
        "Re-run query or maintain-plan to confirm the semantic gap is reduced.",
    ]


def maintain_status(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    if args.status not in VALID_MEMORY_STATUSES:
        raise SystemExit(f"unsupported status: {args.status}")
    table = table_for_type(args.type)
    if table not in {"semantic_facts", "reflections", "episodes"}:
        raise SystemExit("maintain-status supports semantic, reflection, and episode records")
    ts = now_iso()
    assignments = ["status = ?", "reviewed_at = ?"]
    values: list[Any] = [args.status, ts]
    if "stale_reason" in {name for name, _ in GOVERNANCE_COLUMNS.get(table, [])}:
        assignments.append("stale_reason = ?")
        values.append(args.reason)
    if table in {"semantic_facts", "reflections"}:
        assignments.append("is_stale = ?")
        values.append(1 if args.status == "stale" else 0)
    values.extend([project.project_id, args.id])
    with connect(project) as conn:
        conn.execute(
            f"""
            UPDATE {table}
            SET {", ".join(assignments)}
            WHERE project_id = ? AND id = ?
            """,
            values,
        )
        conn.commit()
    print(f"{args.type} #{args.id} status set to {args.status}")


def maintain_merge(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    ids = parse_ids(args.ids)
    table = table_for_type(args.type)
    if table not in {"semantic_facts", "reflections"}:
        raise SystemExit("maintain-merge supports semantic and reflection records")
    ts = now_iso()
    with connect(project) as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE project_id = ? AND id IN ({','.join('?' for _ in ids)})",
            [project.project_id, *ids],
        ).fetchall()
        if len(rows) != len(set(ids)):
            raise SystemExit("some ids were not found")
        if args.type == "semantic":
            if not args.fact:
                raise SystemExit("--fact is required when merging semantic records")
            cur = conn.execute(
                """
                INSERT INTO semantic_facts(
                  project_id, fact, source, confidence, category, scope, evidence,
                  created_at, updated_at, reviewed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.project_id,
                    args.fact,
                    args.source or "maintain-merge",
                    args.confidence,
                    args.category,
                    args.scope,
                    f"merged from semantic ids: {','.join(map(str, ids))}",
                    ts,
                    ts,
                    ts,
                ),
            )
        else:
            if not args.lesson:
                raise SystemExit("--lesson is required when merging reflections")
            cur = conn.execute(
                """
                INSERT INTO reflections(
                  project_id, task, summary, mistake, lesson, future_rule,
                  scope, evidence, confidence, created_at, reviewed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.project_id,
                    args.task or "Merged reflections",
                    args.summary,
                    None,
                    args.lesson,
                    args.future_rule,
                    args.scope,
                    f"merged from reflection ids: {','.join(map(str, ids))}",
                    args.confidence,
                    ts,
                    ts,
                ),
            )
        new_id = cur.lastrowid
        conn.execute(
            f"""
            UPDATE {table}
            SET status = 'merged', merged_into_id = ?, reviewed_at = ?
            WHERE project_id = ? AND id IN ({','.join('?' for _ in ids)})
            """,
            [new_id, ts, project.project_id, *ids],
        )
        conn.commit()
    output({"merged_into_id": new_id, "source_ids": ids, "type": args.type}, args.json)


def maintain_promote(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    if not args.fact:
        raise SystemExit("--fact is required")
    if bool(args.episode_id) == bool(args.reflection_id):
        raise SystemExit("provide exactly one of --episode-id or --reflection-id")
    ts = now_iso()
    with connect(project) as conn:
        source = f"episode:{args.episode_id}" if args.episode_id else f"reflection:{args.reflection_id}"
        evidence = args.evidence or f"promoted from {source}"
        if args.episode_id:
            source_row = conn.execute(
                "SELECT * FROM episodes WHERE project_id = ? AND id = ?",
                (project.project_id, args.episode_id),
            ).fetchone()
            if not source_row:
                raise SystemExit(f"episode not found: {args.episode_id}")
        else:
            source_row = conn.execute(
                "SELECT * FROM reflections WHERE project_id = ? AND id = ?",
                (project.project_id, args.reflection_id),
            ).fetchone()
            if not source_row:
                raise SystemExit(f"reflection not found: {args.reflection_id}")
        cur = conn.execute(
            """
            INSERT INTO semantic_facts(
              project_id, fact, source, confidence, category, scope, evidence,
              created_at, updated_at, reviewed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                args.fact,
                source,
                args.confidence,
                args.category,
                args.scope,
                evidence,
                ts,
                ts,
                ts,
            ),
        )
        fact_id = cur.lastrowid
        if args.episode_id:
            conn.execute(
                """
                UPDATE episodes
                SET reviewed_at = ?, derived_facts = ?
                WHERE project_id = ? AND id = ?
                """,
                (ts, json.dumps([fact_id]), project.project_id, args.episode_id),
            )
        else:
            conn.execute(
                """
                UPDATE reflections
                SET reviewed_at = ?
                WHERE project_id = ? AND id = ?
                """,
                (ts, project.project_id, args.reflection_id),
            )
        conn.commit()
    payload = {"semantic_fact_id": fact_id}
    if args.episode_id:
        payload["episode_id"] = args.episode_id
    else:
        payload["reflection_id"] = args.reflection_id
    output(payload, args.json)
