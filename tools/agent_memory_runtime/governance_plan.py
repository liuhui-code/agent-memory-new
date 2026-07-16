# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from collections import Counter
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
from .impact_feedback import impact_feedback_summary
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
from .semantic_provider_metrics import build_semantic_provider_actions, semantic_provider_health
from .quality_gate_eval import (
    build_quality_gate_failure_actions,
    build_recurring_quality_gate_failure_actions,
    load_quality_gate_history_report,
    load_quality_gate_snapshot,
)
from .query import collect_matches, infer_followup_focus, rank_followup_seed_terms, suggested_followup_terms
from .records import output, parse_ids, row_dict, table_for_type
from .retrieval_feedback import fetch_open_retrieval_feedback, retrieval_feedback_summary
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .task_trace_governance import build_task_trace_actions
from .text import json_list, tokenize, unique_list
from .usage_samples import record_governance_usage



from .governance_corrections import build_correction_learn_payload_template, build_correction_learning_rule, build_correction_targets, build_experience_conflict_candidates, build_retrieval_interference_candidates, build_semantic_patch_review_action
from .governance_incidents import build_incident_strategy_candidates, build_log_design_gap_candidates, build_recurring_incident_fingerprint_candidates
from .governance_learn_actions import build_followup_focus, build_learn_business_payload_template, build_learn_business_payload_template_for_paths, build_learn_governance_summary, build_query_miss_data, build_recent_refresh_drifts, build_recent_semantic_conflicts, build_semantic_gap_targets, build_suggested_query_terms, find_reflections_linked_to_paths, query_followup_workflow_steps, semantic_enrichment_workflow_steps
from .governance_plan_actions import build_maintain_plan_actions
from .governance_quality_actions import build_calibration_feedback_actions, build_experience_maturity_actions, build_quality_governance_actions, build_retrieval_feedback_actions, build_weak_evidence_chain_actions, fetch_incident_trace_quality_rows, fetch_quality_memory_rows
from .governance_review import build_reflect_review_data, reflection_experience_type
from .governance_review_data import active_reflection_rows, build_review_data
from .governance_skill_candidates import build_skill_pattern_candidates, is_complete_experience_candidate
from .governance_utils import count_actions_by_lane
from .governance_lane_plan import build_focused_maintain_plan, selected_known_lane

def maintain_plan(args: argparse.Namespace) -> None:
    started_ms = monotonic_ms()
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    focused_lane = selected_known_lane(args)
    if focused_lane:
        data = build_focused_maintain_plan(project, args, focused_lane)
        finish_maintain_plan(project, args, data, started_ms)
        return
    review = build_review_data(project, args.limit)
    reflection_quality = build_reflect_review_data(project, args.limit)
    query_misses = build_query_miss_data(project, args.limit)
    semantic_conflicts = build_recent_semantic_conflicts(project, args.limit)
    refresh_drifts = build_recent_refresh_drifts(project, args.limit)
    semantic_gap_targets = build_semantic_gap_targets(project)
    learn_business_payload_template = build_learn_business_payload_template(project)
    correction_rows = [
        row
        for row in review["unreviewed_reflections"]
        if reflection_experience_type(row) == "correction_experience" and is_complete_experience_candidate(row)
    ]
    semantic_patch_rows = [
        row
        for row in review["unreviewed_reflections"]
        if reflection_experience_type(row) == "semantic_patch_experience"
    ]
    incident_strategy_candidates = build_incident_strategy_candidates(project, review["unreviewed_reflections"])
    recurring_incident_fingerprint_candidates = build_recurring_incident_fingerprint_candidates(project, review["unreviewed_reflections"])
    active_reflections = active_reflection_rows(project, limit=REVIEW_DUPLICATE_POOL_LIMIT)
    retrieval_interference_candidates = build_retrieval_interference_candidates(active_reflections, args.limit)
    experience_conflict_candidates = build_experience_conflict_candidates(active_reflections, args.limit)
    incident_trace_actions = build_incident_trace_actions(project, args.limit)
    impact_feedback = impact_feedback_summary(project)
    graph_quality = build_graph_quality(
        project,
        force_verify=bool(getattr(args, "verify_graph_quality", False)),
    )
    graph_quality_actions = build_graph_quality_actions(graph_quality)
    graph_signal_quality = build_graph_signal_quality(project, graph_quality=graph_quality)
    graph_signal_quality_actions = build_graph_signal_quality_actions(graph_signal_quality)
    log_observability_gap_actions = build_log_observability_gap_actions(graph_signal_quality)
    last_quality_gate = load_quality_gate_snapshot(project)
    quality_gate_actions = build_quality_gate_failure_actions(last_quality_gate)
    quality_gate_history = load_quality_gate_history_report(project, limit=20)
    recurring_quality_gate_actions = build_recurring_quality_gate_failure_actions(quality_gate_history)
    runtime_performance = build_runtime_performance_summary(project)
    runtime_performance_actions = build_runtime_performance_actions(runtime_performance)
    provider_health = semantic_provider_health(project)
    semantic_provider_actions = build_semantic_provider_actions(provider_health)
    experience_usage = fetch_experience_usage_summary(project, args.limit)
    experience_usage_actions = build_experience_usage_actions(experience_usage)
    memory_tiers = build_memory_tiers(project, args.limit)
    memory_tier_actions = build_memory_tier_actions(memory_tiers)
    task_trace_actions = build_task_trace_actions(project)
    retrieval_feedback_rows = fetch_open_retrieval_feedback(project, args.limit)
    retrieval_observations = retrieval_feedback_summary(project)
    retrieval_feedback_actions = build_retrieval_feedback_actions(retrieval_feedback_rows)
    calibration_feedback_actions = build_calibration_feedback_actions(retrieval_feedback_rows)
    quality_semantic_rows, quality_reflection_rows = fetch_quality_memory_rows(project, args.limit)
    quality_reflection_rows = enrich_reflections_with_evidence_chains(project, quality_reflection_rows)
    quality_report = build_quality_report(
        quality_semantic_rows,
        quality_reflection_rows,
        fetch_incident_trace_quality_rows(project, args.limit),
    )
    quality_governance_actions = build_quality_governance_actions(quality_report)
    weak_evidence_chain_actions = build_weak_evidence_chain_actions(quality_report)
    maturity_governance_actions = build_experience_maturity_actions(quality_reflection_rows)
    active_learning_queue = build_active_learning_queue(
        project,
        graph_signal_quality=graph_signal_quality,
        experience_usage=experience_usage,
        quality_report=quality_report,
        limit=args.limit,
    )
    active_learning_actions = build_active_learning_actions(active_learning_queue)
    skill_pattern_candidates = build_skill_pattern_candidates(project, review["unreviewed_reflections"])
    log_design_candidates = build_log_design_gap_candidates(project, review["unreviewed_reflections"])
    actions = build_maintain_plan_actions(locals())
    annotate_governance_action_priorities(actions)
    action_limit = max(1, int(getattr(args, "action_limit", 10) or 10))
    action_budget = build_governance_action_budget(
        actions,
        limit=action_limit,
        lane=getattr(args, "action_lane", None),
    )

    learn_governance_summary = build_learn_governance_summary(correction_rows, refresh_drifts)
    action_counts = Counter(str(action.get("action") or "") for action in actions)
    quality_action_counts = Counter(str(action.get("action") or "") for action in quality_governance_actions)
    maturity_action_counts = Counter(str(action.get("action") or "") for action in maturity_governance_actions)
    task_trace_action_counts = Counter(str(action.get("action") or "") for action in task_trace_actions)
    calibration_action_counts = Counter(str(action.get("action") or "") for action in calibration_feedback_actions)
    governance_summary = {
        "action_budget": action_budget,
        "counts_by_lane": count_actions_by_lane(actions),
        "incident_strategy_candidates": len(incident_strategy_candidates),
        "recurring_incident_fingerprints": len(recurring_incident_fingerprint_candidates),
        "log_design_gaps": action_counts["review_log_design_gap"],
        "correction_repairs": learn_governance_summary["correction_repairs"],
        "semantic_drift_reviews": learn_governance_summary["semantic_drift_reviews"],
        "semantic_patch_reviews": len(semantic_patch_rows),
        "retrieval_interference_reviews": len(retrieval_interference_candidates),
        "experience_conflict_reviews": len(experience_conflict_candidates),
        "incident_trace_reviews": len(incident_trace_actions),
        "low_quality_memory_reviews": quality_action_counts["review_low_quality_memory"],
        "high_value_experience_reviews": quality_action_counts["review_high_value_experience"],
        "weak_evidence_chain_reviews": len(weak_evidence_chain_actions),
        "immature_experience_reviews": maturity_action_counts["review_immature_experience"],
        "missing_counter_evidence_reviews": maturity_action_counts["review_missing_counter_evidence"],
        "maturity_regression_reviews": maturity_action_counts["review_maturity_regression"],
        "graph_quality_reviews": len(graph_quality_actions),
        "graph_signal_quality_reviews": len(graph_signal_quality_actions),
        "log_observability_gap_reviews": len(log_observability_gap_actions),
        "quality_gate_failure_reviews": len(quality_gate_actions),
        "recurring_quality_gate_failure_reviews": len(recurring_quality_gate_actions),
        "runtime_performance_reviews": len(runtime_performance_actions),
        "semantic_provider_reviews": len(semantic_provider_actions),
        "experience_usage_reviews": len(experience_usage_actions),
        "memory_tier_reviews": len(memory_tier_actions),
        "unreflected_task_trace_reviews": task_trace_action_counts["review_unreflected_task_trace"],
        "low_evidence_auto_summary_reviews": task_trace_action_counts["review_low_evidence_auto_summary"],
        "active_learning_queue_items": len(active_learning_actions),
        "retrieval_feedback_reviews": len(retrieval_feedback_actions),
        "overtrusted_memory_reviews": calibration_action_counts["review_overtrusted_memory"],
        "undertrusted_memory_reviews": calibration_action_counts["review_undertrusted_memory"],
    }

    data = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "execution_scope": {
            "mode": "full_fallback" if getattr(args, "action_lane", None) else "full",
            "selected_lane": getattr(args, "action_lane", None),
            "computed_groups": ["all"],
            "full_archive_summary": True,
        },
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
            "skill_pattern_candidates": len(skill_pattern_candidates),
            "incident_strategy_candidates": len(incident_strategy_candidates),
            "recurring_incident_fingerprints": len(recurring_incident_fingerprint_candidates),
            "semantic_patch_reviews": len(semantic_patch_rows),
            "retrieval_interference_reviews": len(retrieval_interference_candidates),
            "experience_conflict_reviews": len(experience_conflict_candidates),
            "incident_trace_reviews": len(incident_trace_actions),
        },
        "governance_summary": governance_summary,
        "learn_governance_summary": learn_governance_summary,
        "graph_quality": graph_quality,
        "graph_signal_quality": graph_signal_quality,
        "impact_feedback": impact_feedback,
        "last_quality_gate": last_quality_gate,
        "runtime_performance": runtime_performance,
        "semantic_provider": provider_health,
        "experience_usage": {
            "event_count": experience_usage["event_count"],
            "misleading_records": experience_usage["misleading_records"],
            "helpful_records": experience_usage["helpful_records"],
            "stable_signal_count": experience_usage["stable_signal_count"],
            "pending_signal_count": experience_usage["pending_signal_count"],
            "truncated": experience_usage["truncated"],
            "review_actions": len(experience_usage_actions),
        },
        "memory_tiers": memory_tiers,
        "active_learning_queue": active_learning_queue,
        "action_budget": action_budget,
        "retrieval_feedback_summary": {
            **retrieval_observations,
            "open_feedback": len(retrieval_feedback_rows),
            "review_actions": len(retrieval_feedback_actions),
        },
        "quality_summary": quality_report["summary"],
        "evidence_chain_summary": build_evidence_chain_summary(quality_reflection_rows),
        "low_quality_records": quality_report["low_quality_records"],
        "high_value_records": quality_report["high_value_records"],
        "actions": actions,
        "advisory_notice": "maintain-plan only proposes actions. Execute changes only after user confirmation.",
    }
    finish_maintain_plan(project, args, data, started_ms)


def finish_maintain_plan(
    project: Project,
    args: argparse.Namespace,
    data: dict[str, Any],
    started_ms: float,
) -> None:
    if getattr(args, "compact", False):
        data = compact_maintain_plan_payload(data)
    record_governance_usage(project, "maintain-plan", data)
    append_performance_sample(
        project,
        build_performance_sample(
            project,
            "maintain-plan",
            monotonic_ms() - started_ms,
            data["summary"],
            estimate_payload_tokens(data),
        ),
    )
    output(data, args.json)
