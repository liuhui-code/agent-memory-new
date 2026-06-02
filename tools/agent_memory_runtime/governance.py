# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from .code_wiki import semantic_followup_from_db
from .models import ACTIVE_STATUS, GOVERNANCE_COLUMNS, Project, VALID_MEMORY_STATUSES
from .query import collect_matches, infer_followup_focus, rank_followup_seed_terms, suggested_followup_terms
from .records import output, parse_ids, row_dict, table_for_type
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .text import json_list, tokenize, unique_list


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


def reflection_experience_type(row: dict[str, Any]) -> str | None:
    experience_type = row.get("experience_type")
    return str(experience_type) if experience_type else None


EXPERIENCE_CANDIDATE_FIELDS = [
    "hidden_assumptions",
    "negative_preconditions",
    "verification_method",
    "reuse_feedback",
    "source_cases",
]

TRACE_CASE_FIELDS = [
    "query_rounds",
    "trajectory_summary",
    "useful_followup_focus",
    "useful_followup_terms",
    "misleading_followup_terms",
    "inspection_targets",
    "final_verification_path",
    "related_cases",
]


def stable_unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        stripped = value.strip()
        normalized = stripped.lower()
        if not stripped or normalized in seen:
            continue
        seen.add(normalized)
        result.append(stripped)
    return result


def infer_common_steps(
    followup_focuses: list[str],
    query_terms: list[str],
    verification_methods: list[str],
    inspection_targets: list[str],
) -> list[str]:
    steps: list[str] = []
    focus_set = {focus.lower() for focus in followup_focuses}
    joined_terms = " ".join(query_terms).lower()
    joined_targets = " ".join(inspection_targets).lower()
    joined_verification = " ".join(verification_methods).lower()

    if "route" in focus_set:
        steps.append("query route anchors")
        steps.append("inspect route target and page registration")
        if "router" in joined_terms or "pushurl" in joined_terms or "log" in joined_verification:
            steps.append("check related logs")
        steps.append("verify route mismatch")
    if "resource" in focus_set:
        steps.append("query resource anchors")
        steps.append("inspect resource usage and lookup sites")
        steps.append("verify resource resolution")
    if "log" in focus_set and "check related logs" not in steps:
        steps.append("query log anchors")
        steps.append("inspect matching log statements and nearby code")
    if "config" in focus_set:
        steps.append("query config anchors")
        steps.append("inspect config, permission, and module declarations")
        steps.append("verify config mismatch")

    if not steps:
        steps.append("query strongest anchors first")
    if inspection_targets and not any("inspect" in step for step in steps):
        steps.append("inspect shortlisted targets")
    if joined_verification and not any(step.startswith("verify ") for step in steps):
        steps.append("verify conclusion against source or reproduction path")
    return stable_unique_strings(steps)


def skill_candidate_draft_path(pattern_name: str) -> str:
    return f"docs/skill-candidates/{pattern_name}.md"


def skill_candidate_package_path(pattern_name: str) -> str:
    return f"skills/_candidates/{pattern_name}/SKILL.md"


def build_skill_candidate_markdown(candidate: dict[str, Any]) -> str:
    lines = [
        f"# Skill Candidate: {candidate['pattern_name']}",
        "",
        "## Summary",
        "",
        "Generated from repeated `procedure_experience` reflections. Review before turning this into a real skill.",
        "",
        "## Trigger Cluster",
        "",
    ]
    for item in candidate.get("trigger_cluster", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Followup Focus", ""])
    for item in candidate.get("common_followup_focus", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Query Terms", ""])
    for item in candidate.get("common_query_terms", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Steps", ""])
    for item in candidate.get("common_steps", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Stop Conditions", ""])
    for item in candidate.get("common_stop_conditions", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Expected Outputs", ""])
    for item in candidate.get("expected_outputs", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Failure Modes", ""])
    for item in candidate.get("failure_modes", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Supporting Cases", ""])
    for item in candidate.get("supporting_cases", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Verification Methods", ""])
    for item in candidate.get("verification_methods", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Supporting Reflections",
            "",
            ", ".join(f"#{reflection_id}" for reflection_id in candidate.get("supporting_reflection_ids", [])),
            "",
            "## Review Notes",
            "",
            "- Confirm the trigger is stable across cases.",
            "- Remove noisy terms before turning this into a skill.",
            "- Add stop conditions and expected outputs before promotion.",
            "",
        ]
    )
    return "\n".join(lines)


def build_skill_candidate_package_markdown(candidate: dict[str, Any]) -> str:
    lines = [
        f"# Skill Candidate Package: {candidate['pattern_name']}",
        "",
        "Candidate package generated from repeated procedure_experience reflections.",
        "This is still a reviewed candidate artifact, not a formal installed skill.",
        "",
        f"Source draft: `{candidate['draft_path']}`",
        "",
        candidate["draft_markdown"].rstrip(),
        "",
    ]
    return "\n".join(lines)


def build_skill_pattern_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if reflection_experience_type(row) == "correction_experience":
            continue
        if not is_complete_experience_candidate(row):
            continue
        pattern_name = str(row.get("skill_candidate") or "").strip()
        if not pattern_name:
            continue
        groups.setdefault(pattern_name, []).append(row)

    candidates: list[dict[str, Any]] = []
    for pattern_name, grouped_rows in groups.items():
        if len(grouped_rows) < 2:
            continue
        grouped_rows.sort(key=lambda item: int(item.get("id") or 0))
        common_followup_focus = unique_list(
            [str(row.get("useful_followup_focus") or "") for row in grouped_rows if row.get("useful_followup_focus")]
        )
        query_terms = stable_unique_strings(
            [
                term
                for row in grouped_rows
                for term in json_list(row.get("useful_followup_terms"))
            ]
        )
        supporting_cases = stable_unique_strings(
            [
                case
                for row in grouped_rows
                for case in json_list(row.get("related_cases")) + json_list(row.get("source_cases"))
            ]
        )
        trigger_cluster = stable_unique_strings(
            [str(row.get("trigger_condition") or "") for row in grouped_rows if row.get("trigger_condition")]
        )
        verification_methods = stable_unique_strings(
            [str(row.get("verification_method") or "") for row in grouped_rows if row.get("verification_method")]
        )
        stop_conditions = stable_unique_strings(
            [str(row.get("final_verification_path") or "") for row in grouped_rows if row.get("final_verification_path")]
        )
        failure_modes = stable_unique_strings(
            [
                item
                for row in grouped_rows
                for item in (
                    ([str(row.get("anti_pattern"))] if row.get("anti_pattern") else [])
                    + json_list(row.get("what_failed"))
                    + json_list(row.get("misleading_followup_terms"))
                )
            ]
        )
        expected_outputs: list[str] = []
        if any(json_list(row.get("inspection_targets")) for row in grouped_rows):
            expected_outputs.append("inspection target shortlist")
        if verification_methods:
            expected_outputs.append("verification checklist")
        if common_followup_focus:
            expected_outputs.extend(f"{focus} anchor shortlist" for focus in common_followup_focus)
        expected_outputs = stable_unique_strings(expected_outputs)
        inspection_targets = stable_unique_strings(
            [
                target
                for row in grouped_rows
                for target in json_list(row.get("inspection_targets"))
            ]
        )
        common_steps = infer_common_steps(
            common_followup_focus,
            query_terms,
            verification_methods,
            inspection_targets,
        )
        candidates.append(
            {
                "pattern_name": pattern_name,
                "experience_type": "procedure_experience",
                "supporting_reflection_ids": [int(row["id"]) for row in grouped_rows],
                "supporting_count": len(grouped_rows),
                "common_followup_focus": common_followup_focus,
                "common_query_terms": query_terms[:8],
                "common_steps": common_steps[:8],
                "common_stop_conditions": stop_conditions[:6],
                "expected_outputs": expected_outputs[:6],
                "failure_modes": failure_modes[:8],
                "supporting_cases": supporting_cases[:10],
                "trigger_cluster": trigger_cluster[:6],
                "verification_methods": verification_methods[:4],
                "draft_path": skill_candidate_draft_path(pattern_name),
            }
        )
    for candidate in candidates:
        candidate["draft_markdown"] = build_skill_candidate_markdown(candidate)
    candidates.sort(
        key=lambda item: (-int(item["supporting_count"]), item["pattern_name"])
    )
    return candidates


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


def active_reflection_rows(project: Project) -> list[dict[str, Any]]:
    with connect(project) as conn:
        reflection_rows = fetch_memory_rows(conn, project, "reflection", active_only=False)
    return [
        row for row in reflection_rows
        if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")
    ]


def maintain_plan(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    review = build_review_data(project, args.limit)
    reflection_quality = build_reflect_review_data(project, args.limit)
    query_misses = build_query_miss_data(project, args.limit)
    semantic_conflicts = build_recent_semantic_conflicts(project, args.limit)
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
        experience_type = reflection_experience_type(row)
        if is_complete_experience_candidate(row):
            if experience_type == "correction_experience":
                actions.append(
                    {
                        "action": "review_correction_experience",
                        "type": "reflection",
                        "id": row["id"],
                        "experience_type": experience_type,
                        "governance_path": "learn_semantic_repair",
                        "reason": "reflection is a semantic correction candidate for learn governance",
                        "risk": "medium",
                        "requires_confirmation": True,
                        "command": None,
                        "candidate_fields": EXPERIENCE_CANDIDATE_FIELDS,
                        "verification_method": row.get("verification_method"),
                        "source_cases": row.get("source_cases"),
                        **{field: row.get(field) for field in TRACE_CASE_FIELDS},
                    }
                )
            else:
                actions.append(
                    {
                        "action": "promote_experience_candidate",
                        "type": "reflection",
                        "id": row["id"],
                        "experience_type": experience_type or "procedure_experience",
                        "reason": "reflection has enough structure to review as an experience candidate",
                        "risk": "medium",
                        "requires_confirmation": True,
                        "command": None,
                        "candidate_fields": EXPERIENCE_CANDIDATE_FIELDS,
                        "skill_candidate": row.get("skill_candidate"),
                        "verification_method": row.get("verification_method"),
                        "source_cases": row.get("source_cases"),
                        **{field: row.get(field) for field in TRACE_CASE_FIELDS},
                    }
                )
        else:
            actions.append(
                {
                    "action": "promote_or_mark_reviewed",
                    "type": "reflection",
                    "id": row["id"],
                    "experience_type": experience_type,
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

    for candidate in build_skill_pattern_candidates(review["unreviewed_reflections"]):
        actions.append(
            {
                "action": "review_skill_pattern_candidate",
                "type": "skill_pattern",
                "id": None,
                "reason": "multiple procedure experiences point to the same reusable skill pattern",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
                "write_command_template": (
                    "python tools/agent_memory.py maintain-skill-draft "
                    f"--project . --pattern-name {json.dumps(candidate['pattern_name'], ensure_ascii=False)} --json"
                ),
                "package_command_template": (
                    "python tools/agent_memory.py maintain-skill-package "
                    f"--project . --pattern-name {json.dumps(candidate['pattern_name'], ensure_ascii=False)} --json"
                ),
                **candidate,
            }
        )

    for row in query_misses:
        followup_focus = build_followup_focus(project, row["query"])
        suggested_query_terms = build_suggested_query_terms(project, row["query"], learn_business_payload_template)
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
                "followup_focus": followup_focus,
                "suggested_query_terms": suggested_query_terms,
                "query_command_template": "python tools/agent_memory.py search --project . --query '<query>' --json",
                "query_workflow_steps": query_followup_workflow_steps(),
                "semantic_gap_targets": semantic_gap_targets,
                "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
                "learn_business_payload_template": learn_business_payload_template,
                "workflow_steps": semantic_enrichment_workflow_steps(),
            }
        )

    for conflict in semantic_conflicts:
        actions.append(
            {
                "action": "review_semantic_conflict",
                "type": "semantic_conflict",
                "id": None,
                "target": conflict["target"],
                "field": conflict["field"],
                "existing": conflict["existing"],
                "incoming": conflict["incoming"],
                "source_command": conflict["source_command"],
                "observed_at": conflict["observed_at"],
                "decision_note": conflict.get("decision_note"),
                "replacement_source": conflict.get("replacement_source"),
                "reason": "incoming semantic summary conflicts with existing stored summary",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                "apply_command_template": f"python tools/agent_memory.py conflict-apply --project . --id {conflict['id']} --resolution \"<decision>\"",
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
            "semantic_conflicts": len(semantic_conflicts),
            "skill_pattern_candidates": len(build_skill_pattern_candidates(review["unreviewed_reflections"])),
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


def build_recent_semantic_conflicts(project: Project, limit: int) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT id, target, field, existing, incoming, source_command, observed_at
                 , entity_type, decision_note, replacement_source
            FROM semantic_conflicts
            WHERE project_id = ? AND status = 'open'
            ORDER BY observed_at DESC, id DESC
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
    followup = semantic_followup_from_db(project, file_paths)
    if not followup:
        return {"files": []}
    return followup["followup_payload_template"]


def semantic_followup_hint_terms(payload_template: dict[str, Any], limit: int = 12) -> list[str]:
    terms: list[str] = []
    for file_item in payload_template.get("files", []):
        if file_item.get("file_path"):
            terms.append(str(file_item["file_path"]))
        terms.extend(file_item.get("hint_terms") or [])
        for symbol_item in file_item.get("symbols", []):
            if symbol_item.get("symbol"):
                terms.append(str(symbol_item["symbol"]))
            terms.extend(symbol_item.get("hint_terms") or [])
        for log_item in file_item.get("logs", []):
            if log_item.get("message_template"):
                terms.append(str(log_item["message_template"]))
            if log_item.get("function"):
                terms.append(str(log_item["function"]))
            terms.extend(log_item.get("hint_terms") or [])
    return unique_list(terms)[:limit]


def build_followup_focus(project: Project, query: str) -> str | None:
    matches = collect_matches(project, query)
    return infer_followup_focus(query, matches)


def build_suggested_query_terms(project: Project, query: str, payload_template: dict[str, Any], limit: int = 12) -> list[str]:
    matches = collect_matches(project, query)
    if any(matches.get(key) for key in ("wiki_matches", "code_log_matches", "semantic_facts", "reflections", "episodes")):
        return suggested_followup_terms(query, matches, limit=limit)
    query_terms = [token for token in tokenize(query) if len(token) > 1]
    followup_terms = semantic_followup_hint_terms(payload_template, limit=limit)
    return rank_followup_seed_terms(query, [*query_terms, *followup_terms], limit=limit)


def query_followup_workflow_steps() -> list[str]:
    return [
        "Start from suggested_query_terms and keep the original user problem wording.",
        "Prefer exact route, resource, log, file, and symbol anchors before generic keywords.",
        "Run query or search again with the strongest 2-6 followup terms.",
        "If retrieval is still weak, enrich the listed code records with learn-business before querying again.",
    ]


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


def maintain_skill_draft(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    candidates = build_skill_pattern_candidates(active_reflection_rows(project))
    if args.pattern_name == "all":
        written: list[dict[str, Any]] = []
        for candidate in candidates:
            draft_path = project.root / candidate["draft_path"]
            draft_path.parent.mkdir(parents=True, exist_ok=True)
            draft_path.write_text(candidate["draft_markdown"].rstrip() + "\n", encoding="utf-8")
            written.append(
                {
                    "pattern_name": candidate["pattern_name"],
                    "path": str(draft_path),
                }
            )
        payload = {
            "written_count": len(written),
            "pattern_names": [item["pattern_name"] for item in written],
            "written": written,
        }
        output(payload, args.json)
        return

    candidate = next((item for item in candidates if item["pattern_name"] == args.pattern_name), None)
    if not candidate:
        raise SystemExit(f"skill pattern candidate not found: {args.pattern_name}")
    draft_path = project.root / candidate["draft_path"]
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(candidate["draft_markdown"].rstrip() + "\n", encoding="utf-8")
    payload = {
        "pattern_name": candidate["pattern_name"],
        "path": str(draft_path),
        "supporting_reflection_ids": candidate["supporting_reflection_ids"],
        "supporting_count": candidate["supporting_count"],
    }
    output(payload, args.json)


def maintain_skill_package(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    candidates = build_skill_pattern_candidates(active_reflection_rows(project))
    candidate = next((item for item in candidates if item["pattern_name"] == args.pattern_name), None)
    if not candidate:
        raise SystemExit(f"skill pattern candidate not found: {args.pattern_name}")
    package_path = project.root / skill_candidate_package_path(candidate["pattern_name"])
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(build_skill_candidate_package_markdown(candidate).rstrip() + "\n", encoding="utf-8")
    payload = {
        "pattern_name": candidate["pattern_name"],
        "path": str(package_path),
        "supporting_reflection_ids": candidate["supporting_reflection_ids"],
        "supporting_count": candidate["supporting_count"],
    }
    output(payload, args.json)
