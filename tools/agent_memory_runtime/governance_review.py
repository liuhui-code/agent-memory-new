# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import sqlite3
import re
from pathlib import Path
from typing import Any

from .active_learning_queue import build_active_learning_actions, build_active_learning_queue
from .code_wiki import semantic_followup_from_db
from .evidence_chain_quality import build_evidence_chain_summary, enrich_reflections_with_evidence_chains
from .graph_quality import (
    build_graph_quality,
    build_graph_quality_actions,
    build_graph_signal_quality,
    build_graph_signal_quality_actions,
    build_log_observability_gap_actions,
)
from .governance_action_budget import (
    annotate_governance_action_priorities,
    build_governance_action_budget,
    compact_maintain_plan_payload,
)
from .incident_trace_governance import build_incident_trace_actions
from .experience_maturity import score_experience_maturity
from .experience_usage import build_experience_usage_actions, fetch_experience_usage_summary
from .memory_tiers import build_memory_tier_actions, build_memory_tiers
from .models import ACTIVE_STATUS, GOVERNANCE_COLUMNS, Project, REVIEW_DUPLICATE_POOL_LIMIT, VALID_MEMORY_STATUSES
from .performance_scoring import (
    append_performance_sample,
    build_performance_sample,
    build_runtime_performance_actions,
    build_runtime_performance_summary,
    estimate_payload_tokens,
    monotonic_ms,
)
from .quality_scoring import build_quality_report
from .quality_gate_eval import (
    build_quality_gate_failure_actions,
    build_recurring_quality_gate_failure_actions,
    load_quality_gate_history_report,
    load_quality_gate_snapshot,
)
from .query import collect_matches, infer_followup_focus, rank_followup_seed_terms, suggested_followup_terms
from .records import output, parse_ids, row_dict, table_for_type
from .retrieval_feedback import fetch_open_retrieval_feedback
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .task_trace_governance import build_task_trace_actions
from .text import json_list, tokenize, unique_list
from .usage_samples import record_governance_usage



from .governance_utils import fetch_memory_rows, stable_unique_strings

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
                    "runtime_feedback_summary": runtime_feedback_summary(item),
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
    issues.extend(runtime_feedback_issues(row))
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



def runtime_feedback_summary(row: dict[str, Any]) -> dict[str, list[str]]:
    effective_signals = stable_unique_strings(
        [
            *json_list(row.get("useful_followup_terms")),
            *[
                str(row.get("problem") or "").strip(),
                str(row.get("trajectory_summary") or "").strip(),
            ],
        ]
    )[:6]
    misleading_signals = stable_unique_strings(
        [
            *json_list(row.get("misleading_followup_terms")),
            *json_list(row.get("what_failed")),
        ]
    )[:5]
    verification_checkpoints = stable_unique_strings(
        [
            str(row.get("final_verification_path") or "").strip(),
            str(row.get("verification_method") or "").strip(),
            str(row.get("repair_action") or "").strip(),
        ]
    )[:4]
    return {
        "effective_signals": effective_signals,
        "misleading_signals": misleading_signals,
        "verification_checkpoints": verification_checkpoints,
    }



def runtime_feedback_issues(row: dict[str, Any]) -> list[str]:
    source_cases = [str(item).lower() for item in json_list(row.get("source_cases"))]
    runtime_backed = (
        reflection_experience_type(row) == "procedure_experience"
        and (
            str(row.get("useful_followup_focus") or "") == "log"
            or any(item.startswith("runtime_log:") or item.startswith("session:") for item in source_cases)
        )
    )
    if not runtime_backed and reflection_experience_type(row) != "correction_experience":
        return []
    issues: list[str] = []
    if not json_list(row.get("useful_followup_terms")):
        issues.append("missing_runtime_effective_signals")
    if not json_list(row.get("inspection_targets")):
        issues.append("missing_runtime_inspection_targets")
    if not str(row.get("final_verification_path") or "").strip():
        issues.append("missing_runtime_verification_path")
    if reflection_experience_type(row) == "correction_experience" and not json_list(row.get("misleading_followup_terms")):
        issues.append("missing_runtime_misleading_signals")
    return issues
