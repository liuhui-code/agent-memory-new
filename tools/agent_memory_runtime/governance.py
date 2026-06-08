# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import sqlite3
import re
from pathlib import Path
from typing import Any

from .code_wiki import semantic_followup_from_db
from .models import ACTIVE_STATUS, GOVERNANCE_COLUMNS, Project, REVIEW_DUPLICATE_POOL_LIMIT, VALID_MEMORY_STATUSES
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
    ordered_rows = sorted(rows, key=lambda item: int(item.get("id") or 0), reverse=True)[:REVIEW_DUPLICATE_POOL_LIMIT]
    prepared = [(row, token_set(memory_text(row, kind))) for row in ordered_rows]
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
                        "review_pool_limited": len(rows) > REVIEW_DUPLICATE_POOL_LIMIT,
                    }
                )
    candidates.sort(key=lambda item: item["similarity"], reverse=True)
    return candidates[:limit]


def fetch_memory_rows(
    conn: sqlite3.Connection,
    project: Project,
    kind: str,
    active_only: bool = True,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    table = table_for_type(kind)
    status_filter = "AND COALESCE(status, 'active') = 'active'" if active_only else ""
    stale_filter = "AND COALESCE(is_stale, 0) = 0" if table in {"semantic_facts", "reflections"} and active_only else ""
    limit_clause = "LIMIT ?" if limit is not None else ""
    params: list[Any] = [project.project_id]
    if limit is not None:
        params.append(limit)
    rows = conn.execute(
        f"""
        SELECT * FROM {table}
        WHERE project_id = ? {status_filter} {stale_filter}
        ORDER BY id DESC
        {limit_clause}
        """,
        params,
    ).fetchall()
    return [row_dict(row) for row in rows]


def maintain_health(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    with connect(project) as conn:
        semantic_count = conn.execute(
            "SELECT COUNT(*) AS count FROM semantic_facts WHERE project_id = ?",
            (project.project_id,),
        ).fetchone()["count"]
        reflection_count = conn.execute(
            "SELECT COUNT(*) AS count FROM reflections WHERE project_id = ?",
            (project.project_id,),
        ).fetchone()["count"]
        episode_count = conn.execute(
            "SELECT COUNT(*) AS count FROM episodes WHERE project_id = ?",
            (project.project_id,),
        ).fetchone()["count"]
        stale_semantic_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM semantic_facts
            WHERE project_id = ? AND (COALESCE(is_stale, 0) = 1 OR COALESCE(status, 'active') = 'stale')
            """,
            (project.project_id,),
        ).fetchone()["count"]
        stale_reflection_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM reflections
            WHERE project_id = ? AND (COALESCE(is_stale, 0) = 1 OR COALESCE(status, 'active') = 'stale')
            """,
            (project.project_id,),
        ).fetchone()["count"]
        low_conf_semantic_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM semantic_facts
            WHERE project_id = ? AND COALESCE(confidence, 0.8) < 0.6
            """,
            (project.project_id,),
        ).fetchone()["count"]
        low_conf_reflection_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM reflections
            WHERE project_id = ? AND COALESCE(confidence, 0.8) < 0.6
            """,
            (project.project_id,),
        ).fetchone()["count"]
        unreviewed_reflections = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM reflections
            WHERE project_id = ?
              AND reviewed_at IS NULL
              AND COALESCE(status, 'active') = 'active'
              AND COALESCE(is_stale, 0) = 0
            """,
            (project.project_id,),
        ).fetchone()["count"]
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
        semantic_active_rows = fetch_memory_rows(conn, project, "semantic", active_only=True, limit=REVIEW_DUPLICATE_POOL_LIMIT)
        reflection_active_rows = fetch_memory_rows(conn, project, "reflection", active_only=True, limit=REVIEW_DUPLICATE_POOL_LIMIT)

    scope_health_rows = build_scope_health_rows(project)
    scope_missing_source = sum(1 for row in scope_health_rows if row["health_status"] == "missing_source")
    scope_with_drift = sum(1 for row in scope_health_rows if row["health_status"] in {"drift", "high_drift"})
    scope_high_drift = sum(1 for row in scope_health_rows if row["health_status"] == "high_drift")

    duplicate_count = len(duplicate_candidates(semantic_active_rows, "semantic")) + len(duplicate_candidates(reflection_active_rows, "reflection"))
    low_confidence_count = low_conf_semantic_count + low_conf_reflection_count
    stale_count = stale_semantic_count + stale_reflection_count

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
    if scope_missing_source:
        recommended_actions.append("Repair or retire learned scopes whose source roots no longer exist.")
    if scope_with_drift:
        recommended_actions.append("Review refreshed scope drift and rerun focused learn-business on changed files.")

    data = {
        "project_id": project.project_id,
        "counts": {
            "semantic_facts": semantic_count,
            "reflections": reflection_count,
            "episodes": episode_count,
            "stale": stale_count,
            "low_confidence": low_confidence_count,
            "duplicate_candidates": duplicate_count,
            "unreviewed_reflections": unreviewed_reflections,
            "code_files_missing_business_terms": code_files_missing_business_terms,
            "code_symbols_missing_business_terms": code_symbols_missing_business_terms,
            "code_logs_missing_business_terms": code_logs_missing_business_terms,
            "learn_scopes": len(scope_health_rows),
            "scope_missing_source": scope_missing_source,
            "scope_with_drift": scope_with_drift,
            "scope_high_drift": scope_high_drift,
        },
        "scope_health": scope_health_rows[:10],
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

PATH_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".ets", ".json5", ".json", ".md")


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


def extract_path_like_values(*groups: Any) -> list[str]:
    paths: list[str] = []
    for group in groups:
        if isinstance(group, str):
            parsed = json_list(group)
            candidates = [str(item) for item in parsed] if parsed else [group]
        else:
            candidates = [str(item) for item in json_list(group)]
        for candidate in candidates:
            text = candidate.strip()
            if not text:
                continue
            if text.startswith(("file: ", "file:")):
                text = text.split(":", 1)[1].strip()
            if any(text.endswith(suffix) for suffix in PATH_SUFFIXES) and "/" in text:
                paths.append(text)
    return stable_unique_strings(paths)


def build_correction_targets(row: dict[str, Any]) -> dict[str, Any]:
    file_paths = extract_path_like_values(
        row.get("source_cases"),
        row.get("inspection_targets"),
        row.get("context_used"),
        row.get("evidence"),
    )
    return {
        "file_paths": file_paths,
        "inspection_targets": json_list(row.get("inspection_targets")),
        "useful_terms": json_list(row.get("useful_followup_terms")),
        "misleading_terms": json_list(row.get("misleading_followup_terms")),
        "source_cases": json_list(row.get("source_cases")),
    }


def build_correction_learning_rule(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_memory_type": "code_wiki_business_semantics",
        "correction_trigger": row.get("trigger_condition") or row.get("problem") or "",
        "incorrect_understanding": stable_unique_strings(
            [*(json_list(row.get("misleading_followup_terms"))), *(json_list(row.get("what_failed")))]
        ),
        "corrected_understanding": stable_unique_strings(
            [
                str(row.get("future_rule") or ""),
                str(row.get("lesson") or ""),
                *(json_list(row.get("what_worked"))),
            ]
        ),
        "correction_reason": row.get("reasoning_summary") or row.get("summary") or "",
        "source_evidence": stable_unique_strings(
            [
                str(row.get("evidence") or ""),
                str(row.get("verification_method") or ""),
                str(row.get("final_verification_path") or ""),
            ]
        ),
        "repair_action": row.get("repair_action") or "",
        "prevention_rule": row.get("future_rule") or "",
    }


def build_correction_learn_payload_template(project: Project, row: dict[str, Any]) -> dict[str, Any]:
    targets = build_correction_targets(row)
    file_paths = targets["file_paths"]
    followup = semantic_followup_from_db(project, file_paths) if file_paths else None
    if followup:
        return followup["followup_payload_template"]

    hint_terms = stable_unique_strings(
        [
            *targets["useful_terms"],
            *targets["misleading_terms"],
            str(row.get("problem") or ""),
            str(row.get("trigger_condition") or ""),
        ]
    )
    hint_context = stable_unique_strings(
        [
            str(row.get("reasoning_summary") or ""),
            str(row.get("evidence") or ""),
            str(row.get("verification_method") or ""),
            *targets["inspection_targets"],
        ]
    )
    return {
        "files": [
            {
                "file_path": file_path,
                "business_summary": "",
                "business_terms": [],
                "hint_terms": hint_terms[:12],
                "hint_context": hint_context[:8],
                "symbols": [],
                "logs": [],
            }
            for file_path in file_paths
        ]
    }


def correction_repair_workflow_steps() -> list[str]:
    return [
        "Read the affected file, symbol, or log targets in current source.",
        "Compare the stored business meaning against the correction experience evidence and verification method.",
        "Rewrite the learn-business payload for the affected records instead of re-learning a broad directory.",
        "Re-run maintain-plan or query to confirm the semantic misunderstanding is reduced.",
    ]


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


def evaluate_skill_pattern_quality(candidate: dict[str, Any], grouped_rows: list[dict[str, Any]]) -> tuple[int, str, list[str]]:
    score = 0
    reasons: list[str] = []
    supporting_count = int(candidate.get("supporting_count") or 0)
    if supporting_count >= 3:
        score += 3
        reasons.append("has_three_or_more_supporting_reflections")
    elif supporting_count >= 2:
        score += 1
        reasons.append("has_minimum_supporting_reflections")
    else:
        reasons.append("insufficient_supporting_reflections")

    if candidate.get("common_steps"):
        score += 2
        reasons.append("has_common_steps")
    else:
        reasons.append("missing_common_steps")
    if candidate.get("common_stop_conditions"):
        score += 1
        reasons.append("has_stop_conditions")
    else:
        reasons.append("missing_stop_conditions")
    if candidate.get("expected_outputs"):
        score += 1
        reasons.append("has_expected_outputs")
    else:
        reasons.append("missing_expected_outputs")
    if candidate.get("failure_modes"):
        score += 1
        reasons.append("has_failure_modes")
    else:
        reasons.append("missing_failure_modes")

    helped = sum(1 for row in grouped_rows if row.get("last_outcome") == "helped")
    partial = sum(1 for row in grouped_rows if row.get("last_outcome") == "partial")
    misleading = sum(1 for row in grouped_rows if row.get("last_outcome") == "misleading")
    if helped >= 1:
        score += 2
        reasons.append("has_helped_reuse_signal")
    elif partial >= 1:
        score += 1
        reasons.append("has_partial_reuse_signal")
    else:
        reasons.append("missing_positive_reuse_signal")
    if misleading >= 1:
        score -= 2
        reasons.append("has_misleading_reuse_signal")

    anchor_health = candidate.get("anchor_health")
    if anchor_health == "fresh":
        score += 1
        reasons.append("supporting_anchors_are_fresh")
    elif anchor_health == "mixed":
        reasons.append("some_supporting_anchors_are_missing")
    elif anchor_health == "missing":
        reasons.append("supporting_anchors_are_missing")
    if score >= 8:
        readiness = "promotion_candidate"
    elif score >= 5:
        readiness = "review_candidate"
    else:
        readiness = "needs_more_evidence"
    return score, readiness, reasons


def supporting_anchor_health(project_root: Path, grouped_rows: list[dict[str, Any]]) -> dict[str, Any]:
    anchors = stable_unique_strings(
        [
            path
            for row in grouped_rows
            for path in extract_path_like_values(
                row.get("source_cases"),
                row.get("inspection_targets"),
                row.get("context_used"),
                row.get("evidence"),
                row.get("final_verification_path"),
            )
        ]
    )
    existing: list[str] = []
    missing: list[str] = []
    for anchor in anchors:
        candidate = project_root / anchor
        if candidate.exists():
            existing.append(anchor)
        else:
            missing.append(anchor)
    if not anchors:
        status = "unknown"
    elif not missing:
        status = "fresh"
    elif existing:
        status = "mixed"
    else:
        status = "missing"
    return {
        "anchor_paths": anchors,
        "existing_anchor_paths": existing,
        "missing_anchor_paths": missing,
        "anchor_health": status,
    }


def build_scope_health_rows(project: Project, limit: int = 50) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM learn_scopes
            WHERE project_id = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
    scope_rows: list[dict[str, Any]] = []
    for row in rows:
        item = row_dict(row)
        source_root = Path(item["source_root"]).expanduser()
        source_exists = source_root.exists() and source_root.is_dir()
        try:
            refresh_summary = json.loads(item.get("last_refresh_summary") or "{}")
        except json.JSONDecodeError:
            refresh_summary = {}
        added = refresh_summary.get("added_files") or []
        changed = refresh_summary.get("changed_files") or []
        removed = refresh_summary.get("removed_files") or []
        drift_count = len(added) + len(changed) + len(removed)
        if not source_exists:
            health = "missing_source"
        elif drift_count >= 5:
            health = "high_drift"
        elif drift_count >= 1:
            health = "drift"
        else:
            health = "stable"
        item.update(
            {
                "source_exists": source_exists,
                "added_files": added,
                "changed_files": changed,
                "removed_files": removed,
                "drift_count": drift_count,
                "health_status": health,
            }
        )
        scope_rows.append(item)
    scope_rows.sort(
        key=lambda row: (
            {"missing_source": 3, "high_drift": 2, "drift": 1, "stable": 0}.get(row["health_status"], 0),
            row["drift_count"],
            row["id"],
        ),
        reverse=True,
    )
    return scope_rows


def skill_candidate_draft_path(pattern_name: str) -> str:
    return f"docs/skill-candidates/{pattern_name}.md"


def skill_candidate_package_path(pattern_name: str) -> str:
    return f"skills/_candidates/{pattern_name}/SKILL.md"


def skill_candidate_promotion_checklist_path(pattern_name: str) -> str:
    return f"skills/_candidates/{pattern_name}/PROMOTION.md"


def read_frontmatter_metadata(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    lines = text.splitlines()
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata


def artifact_has_human_review(metadata: dict[str, str]) -> bool:
    if not metadata:
        return False
    review_status = (metadata.get("review_status") or "").strip()
    reviewer = (metadata.get("reviewer") or "").strip()
    review_notes = (metadata.get("review_notes") or "").strip()
    if reviewer:
        return True
    if review_notes not in {"", "[]"}:
        return True
    return bool(review_status and review_status != "pending_review")


def guarded_write_artifact(path: Path, content: str) -> dict[str, Any]:
    existing_meta = read_frontmatter_metadata(path)
    if path.exists() and artifact_has_human_review(existing_meta):
        return {
            "write_action": "preserved_existing_reviewed_artifact",
            "warning": "existing artifact has human review metadata; runtime did not overwrite it",
            "existing_review_status": existing_meta.get("review_status", ""),
            "existing_reviewer": existing_meta.get("reviewer", ""),
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return {
        "write_action": "wrote_artifact",
        "warning": "",
        "existing_review_status": existing_meta.get("review_status", ""),
        "existing_reviewer": existing_meta.get("reviewer", ""),
    }


def build_review_guidance(candidate: dict[str, Any]) -> list[str]:
    guidance = [
        "Confirm reviewer, review status, and notes are updated in the artifact before formal promotion.",
        "Verify common steps, stop conditions, and expected outputs against the supporting reflections.",
    ]
    if candidate.get("promotion_stage") == "clustered":
        guidance.insert(0, "Write the draft artifact first, then begin human review.")
    elif candidate.get("promotion_stage") == "draft":
        guidance.insert(0, "Review the draft and record reviewer metadata before packaging it.")
    elif candidate.get("promotion_stage") == "candidate_package":
        guidance.insert(0, "Review the candidate package metadata and notes before considering manual promotion into skills/.")
    return guidance


def annotate_skill_pattern_artifacts(project_root: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    draft_path = candidate["draft_path"]
    package_path = skill_candidate_package_path(candidate["pattern_name"])
    promotion_checklist_path = skill_candidate_promotion_checklist_path(candidate["pattern_name"])
    draft_file = project_root / draft_path
    package_file = project_root / package_path
    promotion_checklist_file = project_root / promotion_checklist_path
    draft_exists = draft_file.exists()
    package_exists = package_file.exists()
    promotion_checklist_exists = promotion_checklist_file.exists()
    draft_meta = read_frontmatter_metadata(draft_file)
    package_meta = read_frontmatter_metadata(package_file)
    if package_exists:
        promotion_stage = "candidate_package"
    elif draft_exists:
        promotion_stage = "draft"
    else:
        promotion_stage = "clustered"
    return {
        **candidate,
        "draft_status": "written" if draft_exists else "not_written",
        "draft_review_status": draft_meta.get("review_status") or ("pending_review" if draft_exists else ""),
        "draft_reviewer": draft_meta.get("reviewer", ""),
        "package_path": package_path,
        "package_status": "written" if package_exists else "not_written",
        "package_review_status": package_meta.get("review_status") or ("pending_review" if package_exists else ""),
        "package_reviewer": package_meta.get("reviewer", ""),
        "promotion_checklist_path": promotion_checklist_path,
        "promotion_checklist_status": "written" if promotion_checklist_exists else "not_written",
        "promotion_stage": promotion_stage,
        "review_guidance": build_review_guidance(
            {
                **candidate,
                "promotion_stage": promotion_stage,
            }
        ),
    }


def format_frontmatter_sequence(values: list[Any]) -> str:
    if not values:
        return "[]"
    items = ", ".join(json.dumps(value, ensure_ascii=False) for value in values)
    return f"[{items}]"


def build_skill_candidate_frontmatter(
    candidate: dict[str, Any],
    artifact_type: str,
    promotion_status: str,
    source_draft: str | None = None,
) -> list[str]:
    lines = [
        "---",
        f"pattern_name: {json.dumps(candidate['pattern_name'], ensure_ascii=False)}",
        f"artifact_type: {json.dumps(artifact_type, ensure_ascii=False)}",
        f"promotion_status: {json.dumps(promotion_status, ensure_ascii=False)}",
        'review_status: "pending_review"',
        'reviewer: ""',
        "review_notes: []",
        f"experience_type: {json.dumps(candidate.get('experience_type') or 'procedure_experience', ensure_ascii=False)}",
        f"supporting_count: {int(candidate.get('supporting_count') or 0)}",
        f"supporting_reflection_ids: {format_frontmatter_sequence(candidate.get('supporting_reflection_ids', []))}",
        f"common_followup_focus: {format_frontmatter_sequence(candidate.get('common_followup_focus', []))}",
        f"supporting_cases: {format_frontmatter_sequence(candidate.get('supporting_cases', []))}",
        f"verification_methods: {format_frontmatter_sequence(candidate.get('verification_methods', []))}",
        f"source_runtime_command: {json.dumps('tools/agent_memory.py', ensure_ascii=False)}",
    ]
    if source_draft:
        lines.append(f"source_draft: {json.dumps(source_draft, ensure_ascii=False)}")
    lines.extend(["---", ""])
    return lines


def build_skill_candidate_markdown(candidate: dict[str, Any]) -> str:
    lines = build_skill_candidate_frontmatter(
        candidate,
        artifact_type="skill_candidate_draft",
        promotion_status="draft",
    ) + [
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
    lines.extend(["", "## Quality Signals", ""])
    lines.append(f"- Readiness: `{candidate.get('promotion_readiness', 'needs_more_evidence')}`")
    lines.append(f"- Quality score: `{candidate.get('quality_score', 0)}`")
    lines.append(f"- Helped reuse count: `{candidate.get('helped_reuse_count', 0)}`")
    lines.append(f"- Partial reuse count: `{candidate.get('partial_reuse_count', 0)}`")
    lines.append(f"- Misleading reuse count: `{candidate.get('misleading_reuse_count', 0)}`")
    lines.append(f"- Anchor health: `{candidate.get('anchor_health', 'unknown')}`")
    missing_anchors = candidate.get("missing_anchor_paths") or []
    if missing_anchors:
        lines.append("- Missing anchors:")
        for item in missing_anchors:
            lines.append(f"  - {item}")
    for item in candidate.get("quality_reasons", []):
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
            "- Reviewer: ",
            "- Review status: pending_review",
            "- Review notes:",
            "  - ",
            "- Confirm the trigger is stable across cases.",
            "- Remove noisy terms before turning this into a skill.",
            "- Add stop conditions and expected outputs before promotion.",
            "",
        ]
    )
    return "\n".join(lines)


def build_skill_candidate_package_markdown(candidate: dict[str, Any]) -> str:
    lines = build_skill_candidate_frontmatter(
        candidate,
        artifact_type="skill_candidate_package",
        promotion_status="candidate",
        source_draft=candidate["draft_path"],
    ) + [
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


def build_skill_promotion_checklist_markdown(candidate: dict[str, Any]) -> str:
    lines = [
        f"# Promotion Checklist: {candidate['pattern_name']}",
        "",
        "Use this checklist before manually promoting the candidate package into `skills/<name>/SKILL.md`.",
        "",
        "## Artifact Paths",
        "",
        f"- Draft: `{candidate['draft_path']}`",
        f"- Candidate package: `{skill_candidate_package_path(candidate['pattern_name'])}`",
        f"- Formal target: `skills/{candidate['pattern_name']}/SKILL.md`",
        "",
        "## Required Metadata",
        "",
        "- [ ] Candidate package `review_status` is no longer `pending_review`.",
        "- [ ] Candidate package `reviewer` is filled.",
        "- [ ] Candidate package `review_notes` explain remaining edits or approval basis.",
        "",
        "## Pattern Quality Checks",
        "",
        f"- [ ] Promotion readiness is acceptable (`{candidate.get('promotion_readiness', 'needs_more_evidence')}`).",
        f"- [ ] Quality score is acceptable for manual promotion review (`{candidate.get('quality_score', 0)}`).",
        f"- [ ] Anchor health is acceptable (`{candidate.get('anchor_health', 'unknown')}`).",
        f"- [ ] Supporting reflections are still sufficient (`{candidate['supporting_count']}` currently).",
        "- [ ] Trigger conditions are stable and explicit.",
        "- [ ] Common steps are executable in order.",
        "- [ ] Stop conditions are concrete.",
        "- [ ] Expected outputs are stable enough for reuse.",
        "- [ ] Failure modes are explicit enough to avoid misuse.",
        "",
        "## Promotion Steps",
        "",
        "- [ ] Review `docs/skill-promotion-rules.md`.",
        "- [ ] Copy or adapt the candidate package into `skills/<name>/SKILL.md` manually.",
        "- [ ] Keep user-facing behavior inside the existing four-skill interface.",
        "- [ ] Run the relevant runtime and workflow tests after promotion.",
        "- [ ] Update docs or examples if the new formal skill changes the recommended workflow.",
        "",
        "## Source Context",
        "",
        f"- Supporting reflections: {', '.join(f'#{reflection_id}' for reflection_id in candidate.get('supporting_reflection_ids', []))}",
    ]
    if candidate.get("common_followup_focus"):
        lines.append(f"- Common followup focus: {', '.join(candidate['common_followup_focus'])}")
    if candidate.get("supporting_cases"):
        lines.append(f"- Supporting cases: {', '.join(candidate['supporting_cases'])}")
    lines.append("")
    return "\n".join(lines)


def incident_strategy_draft_path(strategy_name: str) -> str:
    return f"docs/incident-strategies/{strategy_name}.md"


def incident_strategy_frontmatter(candidate: dict[str, Any]) -> list[str]:
    return [
        "---",
        f"strategy_name: {json.dumps(candidate['strategy_name'], ensure_ascii=False)}",
        f"artifact_type: {json.dumps('incident_strategy_draft', ensure_ascii=False)}",
        f"promotion_status: {json.dumps('draft', ensure_ascii=False)}",
        'review_status: "pending_review"',
        'reviewer: ""',
        "review_notes: []",
        f"experience_type: {json.dumps('procedure_experience', ensure_ascii=False)}",
        f"supporting_count: {int(candidate.get('supporting_count') or 0)}",
        f"supporting_reflection_ids: {format_frontmatter_sequence(candidate.get('supporting_reflection_ids', []))}",
        f"common_followup_focus: {format_frontmatter_sequence(candidate.get('common_followup_focus', []))}",
        f"supporting_cases: {format_frontmatter_sequence(candidate.get('supporting_cases', []))}",
        f"source_runtime_command: {json.dumps('tools/agent_memory.py', ensure_ascii=False)}",
        "---",
        "",
    ]


def build_incident_strategy_markdown(candidate: dict[str, Any]) -> str:
    lines = incident_strategy_frontmatter(candidate) + [
        f"# Incident Strategy: {candidate['strategy_name']}",
        "",
        "## Summary",
        "",
        "Generated from repeated runtime-log-backed procedure experiences. Review before turning this into a broader diagnostic policy or formal skill.",
        "",
        "## Goal Symptoms",
        "",
    ]
    for item in candidate.get("goal_symptoms", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Log Events", ""])
    for item in candidate.get("common_log_events", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Common Followup Focus", ""])
    for item in candidate.get("common_followup_focus", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Recommended Steps", ""])
    for item in candidate.get("recommended_steps", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Verification Paths", ""])
    for item in candidate.get("verification_paths", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Misleading Signals", ""])
    for item in candidate.get("misleading_signals", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Log Design Feedback", ""])
    for item in candidate.get("log_design_feedback", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Supporting Cases", ""])
    for item in candidate.get("supporting_cases", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Quality Signals", ""])
    lines.append(f"- Readiness: `{candidate.get('promotion_readiness', 'needs_more_evidence')}`")
    lines.append(f"- Quality score: `{candidate.get('quality_score', 0)}`")
    for item in candidate.get("quality_reasons", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Review Notes", "", "- Reviewer: ", "- Review status: pending_review", "- Review notes:", "  - ", ""])
    return "\n".join(lines)


def is_runtime_log_backed_procedure(row: dict[str, Any]) -> bool:
    if reflection_experience_type(row) != "procedure_experience":
        return False
    if str(row.get("useful_followup_focus") or "") == "log":
        return True
    source_cases = [str(item).lower() for item in json_list(row.get("source_cases"))]
    return any(item.startswith("runtime_log:") or item.startswith("session:") for item in source_cases)


def slug_words(text: str) -> list[str]:
    normalized = text.lower()
    normalized = normalized.replace("资料", "profile").replace("个人中心", "profile").replace("登录", "login")
    return [token for token in re.findall(r"[a-z0-9]+", normalized) if token]


def classify_incident_domain(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("session invalid", "401", "auth", "login", "token", "session")):
        return "auth-session"
    if any(token in lowered for token in ("route", "router", "pushurl", "navigation")):
        return "route"
    if any(token in lowered for token in ("resource", "$r", "media", "image")):
        return "resource"
    if any(token in lowered for token in ("permission", "config", "module", "ability")):
        return "config"
    return "runtime"


def classify_incident_goal(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("profile", "资料", "个人中心")) and any(token in lowered for token in ("blank", "空白", "没数据", "no data")):
        return "profile-blank"
    if any(token in lowered for token in ("blank", "空白", "white screen")):
        return "blank-screen"
    if any(token in lowered for token in ("permission", "权限")):
        return "permission"
    if any(token in lowered for token in ("retry", "重试", "network", "网络")):
        return "network-retry"
    return "incident"


def incident_strategy_name(row: dict[str, Any]) -> str:
    text = " ".join(
        [
            str(row.get("problem") or ""),
            " ".join(json_list(row.get("useful_followup_terms"))),
            " ".join(json_list(row.get("source_cases"))),
        ]
    )
    return f"log-{classify_incident_domain(text)}-{classify_incident_goal(text)}-diagnosis"


def evaluate_incident_strategy_quality(candidate: dict[str, Any]) -> tuple[int, str, list[str]]:
    score = 0
    reasons: list[str] = []
    if int(candidate.get("supporting_count") or 0) >= 2:
        score += 2
        reasons.append("has_repeated_runtime_incidents")
    if candidate.get("common_log_events"):
        score += 2
        reasons.append("has_common_log_events")
    if candidate.get("recommended_steps"):
        score += 2
        reasons.append("has_recommended_steps")
    if candidate.get("verification_paths"):
        score += 1
        reasons.append("has_verification_paths")
    if candidate.get("misleading_signals"):
        score += 1
        reasons.append("captures_misleading_signals")
    helped = int(candidate.get("helped_reuse_count") or 0)
    if helped >= 1:
        score += 2
        reasons.append("has_helped_reuse_signal")
    if int(candidate.get("misleading_reuse_count") or 0) >= 1:
        score -= 1
        reasons.append("has_misleading_reuse_signal")
    readiness = "promotion_candidate" if score >= 7 else "review_candidate" if score >= 4 else "needs_more_evidence"
    return score, readiness, reasons


def incident_goal_area(strategy_name: str) -> str:
    area = str(strategy_name or "").strip().lower()
    if area.startswith("log-"):
        area = area[4:]
    if area.endswith("-diagnosis"):
        area = area[: -len("-diagnosis")]
    return area.replace("-", "_")


def infer_log_design_kinds(feedback: list[str]) -> list[str]:
    kinds: list[str] = []
    lowered = " ".join(str(item).lower() for item in feedback)
    if "decision checkpoint" in lowered or "decision checkpoints" in lowered:
        kinds.append("decision_checkpoint")
    if "request_id" in lowered or "session_id" in lowered or "correlation" in lowered:
        kinds.append("request_correlation")
    if "start marker" in lowered or "start log" in lowered:
        kinds.append("start_marker")
    if not kinds:
        kinds.append("anchor_alignment")
    return stable_unique_strings(kinds)


def build_incident_strategy_candidates(project: Project, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not is_runtime_log_backed_procedure(row):
            continue
        if not is_complete_experience_candidate(row):
            continue
        name = incident_strategy_name(row)
        groups.setdefault(name, []).append(row)

    candidates: list[dict[str, Any]] = []
    for strategy_name, grouped_rows in groups.items():
        if len(grouped_rows) < 2:
            continue
        grouped_rows.sort(key=lambda item: int(item.get("id") or 0))
        common_followup_focus = unique_list(
            [str(row.get("useful_followup_focus") or "") for row in grouped_rows if row.get("useful_followup_focus")]
        )
        goal_symptoms = stable_unique_strings(
            [str(row.get("problem") or "") for row in grouped_rows if row.get("problem")]
        )[:6]
        common_log_events = stable_unique_strings(
            [
                term
                for row in grouped_rows
                for term in json_list(row.get("useful_followup_terms"))
                if len(term.strip()) > 1
            ]
        )[:10]
        recommended_steps = stable_unique_strings(
            [
                step
                for row in grouped_rows
                for step in json_list(row.get("what_worked"))
            ]
        )[:8]
        verification_paths = stable_unique_strings(
            [
                str(row.get("final_verification_path") or "")
                for row in grouped_rows
                if str(row.get("final_verification_path") or "").strip()
            ]
        )[:6]
        misleading_signals = stable_unique_strings(
            [
                signal
                for row in grouped_rows
                for signal in json_list(row.get("what_failed")) + json_list(row.get("misleading_followup_terms"))
            ]
        )[:8]
        supporting_cases = stable_unique_strings(
            [
                case
                for row in grouped_rows
                for case in json_list(row.get("related_cases")) + json_list(row.get("source_cases"))
            ]
        )[:10]
        log_design_feedback = stable_unique_strings(
            [
                "Add decision checkpoints around auth/session or fallback branches.",
                "Prefer request_id/session_id correlation in runtime logs.",
            ]
        )
        helped_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "helped" or row.get("reuse_feedback") == "helped"
        )
        partial_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "partial" or row.get("reuse_feedback") == "partial"
        )
        misleading_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "misleading" or row.get("reuse_feedback") == "misleading"
        )
        candidate = {
            "strategy_name": strategy_name,
            "experience_type": "procedure_experience",
            "supporting_reflection_ids": [int(row["id"]) for row in grouped_rows],
            "supporting_count": len(grouped_rows),
            "common_followup_focus": common_followup_focus,
            "goal_symptoms": goal_symptoms,
            "common_log_events": common_log_events,
            "recommended_steps": recommended_steps,
            "verification_paths": verification_paths,
            "misleading_signals": misleading_signals,
            "supporting_cases": supporting_cases,
            "log_design_feedback": log_design_feedback,
            "helped_reuse_count": helped_count,
            "partial_reuse_count": partial_count,
            "misleading_reuse_count": misleading_count,
            "draft_path": incident_strategy_draft_path(strategy_name),
            "related_skill_candidates": stable_unique_strings(
                [str(row.get("skill_candidate") or "") for row in grouped_rows if str(row.get("skill_candidate") or "").strip()]
            )[:4],
        }
        quality_score, promotion_readiness, quality_reasons = evaluate_incident_strategy_quality(candidate)
        candidate["quality_score"] = quality_score
        candidate["promotion_readiness"] = promotion_readiness
        candidate["quality_reasons"] = quality_reasons
        candidate["draft_markdown"] = build_incident_strategy_markdown(candidate)
        candidates.append(candidate)
    candidates.sort(key=lambda item: (-int(item["supporting_count"]), item["strategy_name"]))
    return candidates


def build_log_design_gap_candidates(project: Project, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not is_runtime_log_backed_procedure(row):
            continue
        goal_area = incident_goal_area(incident_strategy_name(row))
        groups.setdefault(goal_area, []).append(row)

    candidates: list[dict[str, Any]] = []
    for goal_area, grouped_rows in groups.items():
        if len(grouped_rows) < 2:
            continue
        grouped_rows.sort(key=lambda item: int(item.get("id") or 0))
        feedback = stable_unique_strings(
            [
                "Add decision checkpoints around auth/session or fallback branches.",
                "Prefer request_id/session_id correlation in runtime logs.",
                *[
                    str(row.get("repair_action") or "")
                    for row in grouped_rows
                    if "runtime slice" in str(row.get("repair_action") or "").lower()
                ],
            ]
        )[:6]
        candidates.append(
            {
                "strategy_name": incident_strategy_name(grouped_rows[-1]),
                "goal_area": goal_area,
                "goal_symptoms": stable_unique_strings([str(row.get("problem") or "") for row in grouped_rows if str(row.get("problem") or "").strip()])[:6],
                "supporting_reflection_ids": [int(row["id"]) for row in grouped_rows],
                "supporting_count": len(grouped_rows),
                "high_value_log_anchor_targets": stable_unique_strings(
                    [
                        *[
                            term
                            for row in grouped_rows
                            for term in json_list(row.get("useful_followup_terms"))
                        ],
                        *[
                            target
                            for row in grouped_rows
                            for target in json_list(row.get("inspection_targets"))
                        ],
                    ]
                )[:8],
                "suggested_log_kinds": infer_log_design_kinds(feedback),
                "log_design_feedback": feedback,
            }
        )
    candidates.sort(key=lambda item: (-int(item["supporting_count"]), item["goal_area"]))
    return candidates


def build_skill_pattern_candidates(project: Project, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
        helped_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "helped" or row.get("reuse_feedback") == "helped"
        )
        partial_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "partial" or row.get("reuse_feedback") == "partial"
        )
        misleading_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "misleading" or row.get("reuse_feedback") == "misleading"
        )
        anchor_health = supporting_anchor_health(project.root, grouped_rows)
        common_steps = infer_common_steps(
            common_followup_focus,
            query_terms,
            verification_methods,
            inspection_targets,
        )
        candidate = {
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
            "helped_reuse_count": helped_count,
            "partial_reuse_count": partial_count,
            "misleading_reuse_count": misleading_count,
            **anchor_health,
            "draft_path": skill_candidate_draft_path(pattern_name),
        }
        quality_score, promotion_readiness, quality_reasons = evaluate_skill_pattern_quality(candidate, grouped_rows)
        candidate["quality_score"] = quality_score
        candidate["promotion_readiness"] = promotion_readiness
        candidate["quality_reasons"] = quality_reasons
        candidates.append(candidate)
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
        stale_semantic_rows = conn.execute(
            """
            SELECT * FROM semantic_facts
            WHERE project_id = ?
              AND (COALESCE(is_stale, 0) = 1 OR COALESCE(status, 'active') = 'stale')
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
        stale_reflection_rows = conn.execute(
            """
            SELECT * FROM reflections
            WHERE project_id = ?
              AND (COALESCE(is_stale, 0) = 1 OR COALESCE(status, 'active') = 'stale')
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
        low_conf_semantic_rows = conn.execute(
            """
            SELECT * FROM semantic_facts
            WHERE project_id = ?
              AND COALESCE(confidence, 0.8) < 0.6
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
        low_conf_reflection_rows = conn.execute(
            """
            SELECT * FROM reflections
            WHERE project_id = ?
              AND COALESCE(confidence, 0.8) < 0.6
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
        unreviewed_reflection_rows = conn.execute(
            """
            SELECT * FROM reflections
            WHERE project_id = ?
              AND reviewed_at IS NULL
              AND COALESCE(status, 'active') = 'active'
              AND COALESCE(is_stale, 0) = 0
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
        unreviewed_episode_rows = conn.execute(
            """
            SELECT * FROM episodes
            WHERE project_id = ?
              AND reviewed_at IS NULL
              AND COALESCE(status, 'active') = 'active'
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
        semantic_active = fetch_memory_rows(conn, project, "semantic", active_only=True, limit=REVIEW_DUPLICATE_POOL_LIMIT)
        reflection_active = fetch_memory_rows(conn, project, "reflection", active_only=True, limit=REVIEW_DUPLICATE_POOL_LIMIT)
    return {
        "stale_memories": [row_dict(row) for row in list(stale_semantic_rows) + list(stale_reflection_rows)][:limit],
        "low_confidence": [row_dict(row) for row in list(low_conf_semantic_rows) + list(low_conf_reflection_rows)][:limit],
        "unreviewed_reflections": [row_dict(row) for row in unreviewed_reflection_rows],
        "unreviewed_episodes": [row_dict(row) for row in unreviewed_episode_rows],
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
    refresh_drifts = build_recent_refresh_drifts(project, args.limit)
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
                correction_targets = build_correction_targets(row)
                correction_payload_template = build_correction_learn_payload_template(project, row)
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
                        "correction_targets": correction_targets,
                        "learning_rule_draft": build_correction_learning_rule(row),
                        "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
                        "learn_business_payload_template": correction_payload_template,
                        "workflow_steps": correction_repair_workflow_steps(),
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

    for candidate in build_skill_pattern_candidates(project, review["unreviewed_reflections"]):
        candidate = annotate_skill_pattern_artifacts(project.root, candidate)
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

    for candidate in build_incident_strategy_candidates(project, review["unreviewed_reflections"]):
        actions.append(
            {
                "action": "review_incident_strategy_candidate",
                "type": "incident_strategy",
                "id": None,
                "reason": "multiple runtime-log-backed procedure experiences point to the same incident diagnosis strategy",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
                "write_command_template": (
                    "python tools/agent_memory.py maintain-incident-strategy-draft "
                    f"--project . --strategy-name {json.dumps(candidate['strategy_name'], ensure_ascii=False)} --json"
                ),
                **candidate,
            }
        )

    for candidate in build_log_design_gap_candidates(project, review["unreviewed_reflections"]):
        actions.append(
            {
                "action": "review_log_design_gap",
                "type": "log_design",
                "id": None,
                "reason": "repeated runtime-log-backed diagnosis points to a narrow log design gap worth fixing",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
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

    for drift in refresh_drifts:
        drift_files = stable_unique_strings(
            [
                *(drift.get("added_files") or []),
                *(drift.get("changed_files") or []),
            ]
        )
        payload_template = build_learn_business_payload_template_for_paths(project, drift_files)
        actions.append(
            {
                "action": "review_semantic_drift",
                "type": "learn_scope",
                "id": drift["scope_id"],
                "reason": "refreshed learned scope changed and may need business-semantics review",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                **drift,
                "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
                "learn_business_payload_template": payload_template,
                "workflow_steps": semantic_enrichment_workflow_steps(),
            }
        )
        removed_reflection_ids = find_reflections_linked_to_paths(project, drift.get("removed_files") or [])
        if removed_reflection_ids:
            actions.append(
                {
                    "action": "mark_experience_stale_if_anchor_removed",
                    "type": "reflection",
                    "id": None,
                    "reason": "one or more active reflections reference files removed from a refreshed learned scope",
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": None,
                    "scope_id": drift["scope_id"],
                    "removed_files": drift.get("removed_files") or [],
                    "linked_reflection_ids": removed_reflection_ids,
                }
            )
            affected_patterns = stable_unique_strings(
                [
                    str(row.get("skill_candidate") or "")
                    for row in review["unreviewed_reflections"]
                    if int(row.get("id") or 0) in removed_reflection_ids and row.get("skill_candidate")
                ]
            )
            for pattern_name in affected_patterns:
                actions.append(
                    {
                        "action": "review_skill_pattern_staleness",
                        "type": "skill_pattern",
                        "id": None,
                        "reason": "a clustered skill pattern depends on reflections anchored to removed files",
                        "risk": "medium",
                        "requires_confirmation": True,
                        "command": None,
                        "pattern_name": pattern_name,
                        "scope_id": drift["scope_id"],
                        "removed_files": drift.get("removed_files") or [],
                        "linked_reflection_ids": removed_reflection_ids,
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
            "refresh_drifts": len(refresh_drifts),
            "skill_pattern_candidates": len(build_skill_pattern_candidates(project, review["unreviewed_reflections"])),
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


def build_recent_refresh_drifts(project: Project, limit: int) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT id, scope_type, source_root, target_path, entry_path, depth, mode,
                   last_refreshed_at, last_refresh_summary
            FROM learn_scopes
            WHERE project_id = ?
              AND status = 'active'
              AND last_refresh_summary IS NOT NULL
              AND TRIM(last_refresh_summary) != ''
            ORDER BY COALESCE(last_refreshed_at, updated_at) DESC, id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
    drifts: list[dict[str, Any]] = []
    for row in rows:
        summary_raw = row["last_refresh_summary"] or ""
        try:
            summary = json.loads(summary_raw)
        except json.JSONDecodeError:
            continue
        added_files = summary.get("added_files") or []
        changed_files = summary.get("changed_files") or []
        removed_files = summary.get("removed_files") or []
        semantic_review_targets = summary.get("semantic_review_targets") or {}
        if not (added_files or changed_files or removed_files or semantic_review_targets.get("drift_detected")):
            continue
        drifts.append(
            {
                "scope_id": row["id"],
                "scope_type": row["scope_type"],
                "source_root": row["source_root"],
                "target_path": row["target_path"],
                "entry_path": row["entry_path"],
                "depth": row["depth"],
                "mode": row["mode"],
                "last_refreshed_at": row["last_refreshed_at"],
                "added_files": added_files,
                "changed_files": changed_files,
                "removed_files": removed_files,
                "unchanged_count": summary.get("unchanged_count", 0),
                "semantic_review_targets": semantic_review_targets,
            }
        )
    return drifts


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


def build_learn_business_payload_template_for_paths(
    project: Project,
    file_paths: list[str],
) -> dict[str, Any]:
    unique_paths = stable_unique_strings(file_paths)
    followup = semantic_followup_from_db(project, unique_paths)
    if not followup:
        return {"files": []}
    return followup["followup_payload_template"]


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
    return build_learn_business_payload_template_for_paths(project, file_paths)


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


def find_reflections_linked_to_paths(project: Project, file_paths: list[str], limit: int = 8) -> list[int]:
    if not file_paths:
        return []
    normalized_targets = {path.strip().lower() for path in file_paths if str(path).strip()}
    linked: list[int] = []
    for row in active_reflection_rows(project):
        linked_paths = {
            path.lower()
            for path in extract_path_like_values(
                row.get("source_cases"),
                row.get("inspection_targets"),
                row.get("context_used"),
                row.get("evidence"),
                row.get("final_verification_path"),
            )
        }
        if linked_paths & normalized_targets:
            linked.append(int(row["id"]))
    return linked[:limit]


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
    candidates = build_skill_pattern_candidates(project, active_reflection_rows(project))
    if args.pattern_name == "all":
        written: list[dict[str, Any]] = []
        for candidate in candidates:
            draft_path = project.root / candidate["draft_path"]
            write_result = guarded_write_artifact(draft_path, candidate["draft_markdown"])
            candidate = annotate_skill_pattern_artifacts(project.root, candidate)
            written.append(
                {
                    "pattern_name": candidate["pattern_name"],
                    "path": str(draft_path),
                    "draft_status": candidate["draft_status"],
                    "draft_review_status": candidate["draft_review_status"],
                    "draft_reviewer": candidate["draft_reviewer"],
                    "package_path": candidate["package_path"],
                    "package_status": candidate["package_status"],
                    "package_review_status": candidate["package_review_status"],
                    "package_reviewer": candidate["package_reviewer"],
                    "promotion_checklist_path": candidate["promotion_checklist_path"],
                    "promotion_checklist_status": candidate["promotion_checklist_status"],
                    "promotion_stage": candidate["promotion_stage"],
                    "promotion_readiness": candidate["promotion_readiness"],
                    "quality_score": candidate["quality_score"],
                    "quality_reasons": candidate["quality_reasons"],
                    "review_guidance": candidate["review_guidance"],
                    "write_action": write_result["write_action"],
                    "warning": write_result["warning"],
                    "existing_review_status": write_result["existing_review_status"],
                    "existing_reviewer": write_result["existing_reviewer"],
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
    write_result = guarded_write_artifact(draft_path, candidate["draft_markdown"])
    candidate = annotate_skill_pattern_artifacts(project.root, candidate)
    payload = {
        "pattern_name": candidate["pattern_name"],
        "path": str(draft_path),
        "supporting_reflection_ids": candidate["supporting_reflection_ids"],
        "supporting_count": candidate["supporting_count"],
        "draft_status": candidate["draft_status"],
        "draft_review_status": candidate["draft_review_status"],
        "draft_reviewer": candidate["draft_reviewer"],
        "package_path": candidate["package_path"],
        "package_status": candidate["package_status"],
        "package_review_status": candidate["package_review_status"],
        "package_reviewer": candidate["package_reviewer"],
        "promotion_checklist_path": candidate["promotion_checklist_path"],
        "promotion_checklist_status": candidate["promotion_checklist_status"],
        "promotion_stage": candidate["promotion_stage"],
        "promotion_readiness": candidate["promotion_readiness"],
        "quality_score": candidate["quality_score"],
        "quality_reasons": candidate["quality_reasons"],
        "review_guidance": candidate["review_guidance"],
        "write_action": write_result["write_action"],
        "warning": write_result["warning"],
        "existing_review_status": write_result["existing_review_status"],
        "existing_reviewer": write_result["existing_reviewer"],
    }
    output(payload, args.json)


def maintain_skill_package(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    candidates = build_skill_pattern_candidates(project, active_reflection_rows(project))
    candidate = next((item for item in candidates if item["pattern_name"] == args.pattern_name), None)
    if not candidate:
        raise SystemExit(f"skill pattern candidate not found: {args.pattern_name}")
    package_path = project.root / skill_candidate_package_path(candidate["pattern_name"])
    write_result = guarded_write_artifact(package_path, build_skill_candidate_package_markdown(candidate))
    checklist_path = project.root / skill_candidate_promotion_checklist_path(candidate["pattern_name"])
    checklist_write_result = guarded_write_artifact(checklist_path, build_skill_promotion_checklist_markdown(candidate))
    candidate = annotate_skill_pattern_artifacts(project.root, candidate)
    payload = {
        "pattern_name": candidate["pattern_name"],
        "path": str(package_path),
        "supporting_reflection_ids": candidate["supporting_reflection_ids"],
        "supporting_count": candidate["supporting_count"],
        "draft_status": candidate["draft_status"],
        "draft_review_status": candidate["draft_review_status"],
        "draft_reviewer": candidate["draft_reviewer"],
        "package_path": candidate["package_path"],
        "package_status": candidate["package_status"],
        "package_review_status": candidate["package_review_status"],
        "package_reviewer": candidate["package_reviewer"],
        "promotion_checklist_path": candidate["promotion_checklist_path"],
        "promotion_checklist_status": candidate["promotion_checklist_status"],
        "promotion_stage": candidate["promotion_stage"],
        "promotion_readiness": candidate["promotion_readiness"],
        "quality_score": candidate["quality_score"],
        "quality_reasons": candidate["quality_reasons"],
        "review_guidance": candidate["review_guidance"],
        "write_action": write_result["write_action"],
        "warning": write_result["warning"],
        "existing_review_status": write_result["existing_review_status"],
        "existing_reviewer": write_result["existing_reviewer"],
        "promotion_checklist_write_action": checklist_write_result["write_action"],
        "promotion_checklist_warning": checklist_write_result["warning"],
    }
    output(payload, args.json)


def maintain_skill_promotion_status(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    candidates = build_skill_pattern_candidates(project, active_reflection_rows(project))
    candidate = next((item for item in candidates if item["pattern_name"] == args.pattern_name), None)
    if not candidate:
        raise SystemExit(f"skill pattern candidate not found: {args.pattern_name}")
    candidate = annotate_skill_pattern_artifacts(project.root, candidate)
    draft_meta = read_frontmatter_metadata(project.root / candidate["draft_path"])
    package_meta = read_frontmatter_metadata(project.root / candidate["package_path"])
    formal_target = f"skills/{candidate['pattern_name']}/SKILL.md"
    blockers: list[str] = []
    if candidate["promotion_stage"] != "candidate_package":
        blockers.append("candidate_package_not_written")
    if candidate["promotion_checklist_status"] != "written":
        blockers.append("promotion_checklist_missing")
    if candidate.get("package_review_status") in {"", "pending_review"}:
        blockers.append("package_review_not_completed")
    if not candidate.get("package_reviewer"):
        blockers.append("package_reviewer_missing")
    if candidate.get("promotion_readiness") != "promotion_candidate":
        blockers.append("promotion_readiness_not_high_enough")
    if candidate.get("anchor_health") == "missing":
        blockers.append("supporting_anchors_missing")
    payload = {
        "pattern_name": candidate["pattern_name"],
        "formal_target": formal_target,
        "promotion_stage": candidate["promotion_stage"],
        "draft_path": candidate["draft_path"],
        "draft_status": candidate["draft_status"],
        "draft_review_status": candidate["draft_review_status"],
        "draft_reviewer": candidate["draft_reviewer"],
        "package_path": candidate["package_path"],
        "package_status": candidate["package_status"],
        "package_review_status": candidate["package_review_status"],
        "package_reviewer": candidate["package_reviewer"],
        "promotion_checklist_path": candidate["promotion_checklist_path"],
        "promotion_checklist_status": candidate["promotion_checklist_status"],
        "promotion_readiness": candidate["promotion_readiness"],
        "quality_score": candidate["quality_score"],
        "quality_reasons": candidate["quality_reasons"],
        "helped_reuse_count": candidate["helped_reuse_count"],
        "partial_reuse_count": candidate["partial_reuse_count"],
        "misleading_reuse_count": candidate["misleading_reuse_count"],
        "anchor_health": candidate["anchor_health"],
        "missing_anchor_paths": candidate["missing_anchor_paths"],
        "draft_frontmatter": draft_meta,
        "package_frontmatter": package_meta,
        "promotion_blockers": blockers,
        "ready_for_manual_promotion": not blockers,
        "review_guidance": candidate["review_guidance"],
    }
    output(payload, args.json)


def maintain_incident_strategy_draft(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    candidates = build_incident_strategy_candidates(project, active_reflection_rows(project))
    candidate = next((item for item in candidates if item["strategy_name"] == args.strategy_name), None)
    if not candidate:
        raise SystemExit(f"incident strategy candidate not found: {args.strategy_name}")
    draft_path = project.root / candidate["draft_path"]
    write_result = guarded_write_artifact(draft_path, candidate["draft_markdown"])
    payload = {
        "strategy_name": candidate["strategy_name"],
        "path": str(draft_path),
        "supporting_reflection_ids": candidate["supporting_reflection_ids"],
        "supporting_count": candidate["supporting_count"],
        "draft_status": "written" if draft_path.exists() else "not_written",
        "promotion_readiness": candidate["promotion_readiness"],
        "quality_score": candidate["quality_score"],
        "quality_reasons": candidate["quality_reasons"],
        "write_action": write_result["write_action"],
        "warning": write_result["warning"],
        "existing_review_status": write_result["existing_review_status"],
        "existing_reviewer": write_result["existing_reviewer"],
    }
    output(payload, args.json)
