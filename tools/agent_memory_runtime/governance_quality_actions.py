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

from .governance_utils import fetch_memory_rows


def fetch_quality_memory_rows(project: Project, limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    with connect(project) as conn:
        semantic_rows = fetch_memory_rows(conn, project, "semantic", active_only=False, limit=limit)
        reflection_rows = fetch_memory_rows(conn, project, "reflection", active_only=False, limit=limit)
    return semantic_rows, reflection_rows



def fetch_incident_trace_quality_rows(project: Project, limit: int) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM incident_traces
            WHERE project_id = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
    return [row_dict(row) for row in rows]



def build_quality_governance_actions(quality_report: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for item in quality_report.get("low_quality_records", []):
        record_type = normalize_quality_record_type(item.get("record_type"))
        record_id = int(item.get("record_id") or 0)
        if not record_id:
            continue
        key = ("review_low_quality_memory", record_type, record_id)
        if key in seen:
            continue
        seen.add(key)
        actions.append(
            {
                "action": "review_low_quality_memory",
                "governance_lane": "memory_quality",
                "type": record_type,
                "id": record_id,
                "reason": "quality score is below the review threshold",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
                "quality_score": item.get("quality_score"),
                "quality_band": item.get("quality_band"),
                "quality_reasons": item.get("reasons") or [],
                "recommended_action": item.get("recommended_action"),
                "suggested_actions": low_quality_suggested_actions(record_type),
            }
        )
    for item in quality_report.get("high_value_records", []):
        if item.get("record_type") != "reflection":
            continue
        record_id = int(item.get("record_id") or 0)
        if not record_id:
            continue
        key = ("review_high_value_experience", "reflection", record_id)
        if key in seen:
            continue
        seen.add(key)
        experience_type = item.get("experience_type") or "procedure_experience"
        actions.append(
            {
                "action": "review_high_value_experience",
                "governance_lane": high_value_governance_lane(str(experience_type)),
                "type": "reflection",
                "id": record_id,
                "experience_type": experience_type,
                "reason": "experience has high quality score and is worth prioritized review",
                "risk": "low",
                "requires_confirmation": True,
                "command": None,
                "quality_score": item.get("quality_score"),
                "quality_band": item.get("quality_band"),
                "quality_reasons": item.get("reasons") or [],
                "suggested_actions": high_value_suggested_actions(str(experience_type)),
            }
        )
    return actions



def normalize_quality_record_type(record_type: Any) -> str:
    if record_type == "incident_trace":
        return "incident-trace"
    return str(record_type or "memory")



def low_quality_suggested_actions(record_type: str) -> list[str]:
    actions = ["verify_against_source", "lower_confidence", "mark_stale", "merge_duplicate"]
    if record_type == "reflection":
        actions.insert(1, "tighten_trigger_condition")
    if record_type == "incident-trace":
        actions.insert(1, "review_trace_evidence")
    return actions



def high_value_governance_lane(experience_type: str) -> str:
    if experience_type in {"correction_experience", "semantic_patch_experience"}:
        return "learn_semantic_repair"
    return "skill_evolution"



def high_value_suggested_actions(experience_type: str) -> list[str]:
    if experience_type in {"correction_experience", "semantic_patch_experience"}:
        return ["reuse_as_guardrail", "review_for_semantic_repair", "keep_active"]
    return ["reuse_as_primary_context", "review_for_skill_pattern", "review_for_promotion", "keep_active"]



def build_weak_evidence_chain_actions(quality_report: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for item in quality_report.get("high_value_records", []):
        if item.get("record_type") != "reflection":
            continue
        score = item.get("evidence_chain_score")
        if score is None or float(score or 0.0) >= 0.6:
            continue
        actions.append(
            {
                "action": "review_weak_evidence_chain",
                "governance_lane": "memory_quality",
                "type": "reflection",
                "id": item.get("record_id"),
                "experience_type": item.get("experience_type") or "procedure_experience",
                "reason": "high-value experience lacks a grounded source-case evidence chain",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                "quality_score": item.get("quality_score"),
                "evidence_chain_score": score,
                "evidence_chain_reasons": item.get("evidence_chain_reasons") or [],
                "suggested_actions": [
                    "link_source_case",
                    "verify_against_incident_trace",
                    "add_code_or_log_anchor",
                    "keep_as_unanchored_experience",
                ],
            }
        )
    return actions



def build_experience_maturity_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item.update(score_experience_maturity(item))
        level = item.get("experience_maturity")
        counter = item.get("counter_evidence") if isinstance(item.get("counter_evidence"), dict) else {}
        if level == "raw_observation" and float(item.get("confidence") or 0.0) >= 0.8:
            actions.append(
                {
                    "action": "review_immature_experience",
                    "governance_lane": "memory_quality",
                    "type": "reflection",
                    "id": item.get("id"),
                    "experience_maturity": level,
                    "experience_maturity_score": item.get("experience_maturity_score"),
                    "reason": "high-confidence reflection is still a raw observation",
                    "risk": "medium",
                    "requires_confirmation": False,
                    "command": None,
                    "suggested_actions": [
                        "add_trigger_condition",
                        "add_repair_action",
                        "add_verification_method",
                        "lower_confidence_until_structured",
                    ],
                }
            )
        if level in {"structured_candidate", "verified_case", "reused_pattern", "skill_candidate"} and not counter.get("has_counter_evidence"):
            actions.append(
                {
                    "action": "review_missing_counter_evidence",
                    "governance_lane": "memory_quality",
                    "type": "reflection",
                    "id": item.get("id"),
                    "experience_maturity": level,
                    "experience_maturity_score": item.get("experience_maturity_score"),
                    "reason": "mature experience is missing counter-evidence or does-not-apply conditions",
                    "risk": "low",
                    "requires_confirmation": False,
                    "command": None,
                    "missing_counter_evidence_fields": counter.get("missing_fields") or [],
                    "suggested_actions": [
                        "add_negative_preconditions",
                        "add_does_not_apply_to",
                        "add_counter_example",
                        "lower_confidence_until_verified",
                        "keep_if_context_specific",
                    ],
                }
            )
        if level == "deprecated_pattern" and (item.get("skill_candidate") or int(item.get("applied_count") or 0) > 0):
            actions.append(
                {
                    "action": "review_maturity_regression",
                    "governance_lane": "memory_quality",
                    "type": "reflection",
                    "id": item.get("id"),
                    "experience_maturity": level,
                    "experience_maturity_score": item.get("experience_maturity_score"),
                    "reason": "previously reusable experience now has deprecated or misleading signals",
                    "risk": "medium",
                    "requires_confirmation": False,
                    "command": None,
                    "suggested_actions": [
                        "mark_stale_if_confirmed",
                        "split_valid_and_invalid_conditions",
                        "write_correction_experience",
                        "remove_skill_candidate_until_reverified",
                    ],
                }
            )
    return actions



def build_retrieval_feedback_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("signal_stable"):
            continue
        if row.get("reason") in {"useful", "verified_useful", "undertrusted", "overtrusted"}:
            continue
        actions.append(
            {
                "action": "review_retrieval_feedback",
                "governance_lane": "memory_quality",
                "type": row.get("record_type"),
                "id": row.get("record_id"),
                "feedback_id": row.get("id"),
                "query": row.get("query"),
                "reason": "retrieval feedback says this record was unhelpful for the query",
                "reason_code": row.get("reason"),
                "replacement_type": row.get("replacement_type"),
                "replacement_id": row.get("replacement_id"),
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                "suggested_actions": [
                    "tighten_trigger_condition",
                    "lower_confidence",
                    "mark_stale_if_confirmed",
                    "merge_or_supersede_if_replacement_is_better",
                    "ignore_feedback_if_not_reproducible",
                ],
                "supporting_feedback_ids": row.get("supporting_feedback_ids") or [row.get("id")],
                "resolution_commands": [
                    "python tools/agent_memory.py retrieval-feedback --project . "
                    f"--feedback-id {feedback_id} --status resolved --note '<resolution>' --json"
                    for feedback_id in (row.get("supporting_feedback_ids") or [row.get("id")])
                ],
            }
        )
    return actions



def build_calibration_feedback_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("signal_stable"):
            continue
        reason = str(row.get("reason") or "")
        if reason == "overtrusted":
            actions.append(
                {
                    "action": "review_overtrusted_memory",
                    "governance_lane": "memory_quality",
                    "type": row.get("record_type"),
                    "id": row.get("record_id"),
                    "feedback_id": row.get("id"),
                    "query": row.get("query"),
                    "reason": "calibration feedback says this record was trusted too strongly for the query",
                    "reason_code": reason,
                    "risk": "medium",
                    "requires_confirmation": False,
                    "command": None,
                    "suggested_actions": [
                        "tighten_trigger_condition",
                        "lower_confidence_if_confirmed",
                        "add_negative_precondition",
                        "mark_stale_if_current_code_disagrees",
                        "ignore_feedback_if_not_reproducible",
                    ],
                }
            )
        elif reason == "undertrusted":
            actions.append(
                {
                    "action": "review_undertrusted_memory",
                    "governance_lane": "memory_quality",
                    "type": row.get("record_type"),
                    "id": row.get("record_id"),
                    "feedback_id": row.get("id"),
                    "query": row.get("query"),
                    "reason": "calibration feedback says this record was more useful than its trust label implied",
                    "reason_code": reason,
                    "risk": "low",
                    "requires_confirmation": False,
                    "command": None,
                    "suggested_actions": [
                        "add_verification_evidence",
                        "raise_confidence_if_confirmed",
                        "link_source_case",
                        "keep_feedback_only_if_single_observation",
                    ],
                }
            )
    return actions
