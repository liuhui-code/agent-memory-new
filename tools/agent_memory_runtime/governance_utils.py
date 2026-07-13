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



def normalized_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())



def token_overlap_ratio(left: str, right: str) -> float:
    left_tokens = token_set(left)
    right_tokens = token_set(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return overlap / union if union else 0.0



def shared_reflection_context(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    shared_scope = normalized_text(left.get("scope")) and normalized_text(left.get("scope")) == normalized_text(right.get("scope"))
    shared_trigger = normalized_text(left.get("trigger_condition")) and normalized_text(left.get("trigger_condition")) == normalized_text(right.get("trigger_condition"))
    shared_inspection_targets = stable_unique_strings(
        [
            target
            for target in json_list(left.get("inspection_targets"))
            if normalized_text(target) in {normalized_text(value) for value in json_list(right.get("inspection_targets"))}
        ]
    )
    return {
        "shared_scope": bool(shared_scope),
        "shared_trigger": bool(shared_trigger),
        "shared_inspection_targets": shared_inspection_targets,
        "scope_overlap": token_overlap_ratio(str(left.get("scope") or ""), str(right.get("scope") or "")),
        "trigger_overlap": token_overlap_ratio(str(left.get("trigger_condition") or ""), str(right.get("trigger_condition") or "")),
    }



def count_actions_by_lane(actions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in actions:
        lane = str(action.get("governance_lane") or "general")
        counts[lane] = counts.get(lane, 0) + 1
    return counts



def infer_governance_lane(action: dict[str, Any]) -> str:
    action_name = str(action.get("action") or "")
    if action_name in {"review_correction_experience", "review_semantic_drift", "add_business_terms"}:
        return "learn_semantic_repair"
    if action_name in {"review_skill_pattern_candidate", "review_incident_strategy_candidate"}:
        return "skill_evolution"
    if action_name in {"review_log_design_gap", "review_log_observability_gap", "review_query_miss"}:
        return "log_diagnosis"
    if action_name in {"review_quality_gate_failure"}:
        return "quality_gate"
    if action_name in {"review_recurring_incident_fingerprint"}:
        return "incident_recurrence"
    if action_name in {"review_experience_conflict"}:
        return "experience_conflict"
    if action_name in {"mark_experience_stale_if_anchor_removed", "review_skill_pattern_staleness"}:
        return "experience_staleness"
    if action_name in {"archive", "review", "verify", "rewrite_reflection", "promote_or_mark_reviewed", "promote_or_archive"}:
        return "memory_hygiene"
    if action_name in {"review_semantic_conflict"}:
        return "semantic_conflict"
    return "general"
