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



from .governance_review import reflection_experience_type, reflection_quality_issues
from .governance_skill_artifacts import (
    build_review_guidance,
    build_skill_candidate_markdown,
    evaluate_skill_pattern_quality,
    infer_common_steps,
    skill_candidate_draft_path,
    supporting_anchor_health,
)
from .governance_utils import EXPERIENCE_CANDIDATE_FIELDS, stable_unique_strings

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
