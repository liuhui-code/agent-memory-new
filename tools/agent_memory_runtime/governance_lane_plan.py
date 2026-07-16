# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from typing import Any

from .active_learning_queue import build_active_learning_actions, build_active_learning_queue
from .evidence_chain_quality import build_evidence_chain_summary, enrich_reflections_with_evidence_chains
from .experience_usage import build_experience_usage_actions, fetch_experience_usage_summary
from .graph_quality import (
    build_graph_quality,
    build_graph_quality_actions,
    build_graph_signal_quality,
    build_graph_signal_quality_actions,
    build_log_observability_gap_actions,
)
from .governance_action_budget import annotate_governance_action_priorities, build_governance_action_budget
from .governance_corrections import build_experience_conflict_candidates, build_retrieval_interference_candidates
from .governance_incidents import (
    build_incident_strategy_candidates,
    build_log_design_gap_candidates,
    build_recurring_incident_fingerprint_candidates,
)
from .governance_learn_actions import (
    build_learn_business_payload_template,
    build_query_miss_data,
    build_recent_refresh_drifts,
    build_recent_semantic_conflicts,
    build_semantic_gap_targets,
)
from .governance_plan_actions import build_maintain_plan_actions
from .governance_quality_actions import (
    build_calibration_feedback_actions,
    build_experience_maturity_actions,
    build_quality_governance_actions,
    build_retrieval_feedback_actions,
    build_weak_evidence_chain_actions,
    fetch_incident_trace_quality_rows,
    fetch_quality_memory_rows,
)
from .governance_review import build_reflect_review_data
from .governance_review_data import active_reflection_rows, build_review_data
from .governance_skill_candidates import build_skill_pattern_candidates
from .incident_trace_governance import build_incident_trace_actions
from .memory_tiers import build_memory_tier_actions, build_memory_tiers
from .models import Project, REVIEW_DUPLICATE_POOL_LIMIT
from .performance_scoring import build_runtime_performance_actions, build_runtime_performance_summary
from .quality_gate_eval import (
    build_quality_gate_failure_actions,
    build_recurring_quality_gate_failure_actions,
    load_quality_gate_history_report,
    load_quality_gate_snapshot,
)
from .quality_scoring import build_quality_report
from .retrieval_feedback import fetch_open_retrieval_feedback, retrieval_feedback_summary
from .semantic_provider_metrics import build_semantic_provider_actions, semantic_provider_health
from .task_trace_governance import build_task_trace_actions


KNOWN_GOVERNANCE_LANES = {
    "active_learning",
    "auto_reflection",
    "experience_conflict",
    "experience_staleness",
    "experience_usage",
    "graph_quality",
    "incident_recurrence",
    "incident_trace",
    "learn_semantic_repair",
    "log_diagnosis",
    "memory_hygiene",
    "memory_quality",
    "memory_tiers",
    "quality_gate",
    "retrieval_interference",
    "runtime_performance",
    "semantic_conflict",
    "skill_evolution",
}


def selected_known_lane(args: argparse.Namespace) -> str | None:
    selected = str(getattr(args, "action_lane", "") or "").strip()
    return selected if selected in KNOWN_GOVERNANCE_LANES else None


def empty_action_context(
    project: Project,
    args: argparse.Namespace,
    lane: str,
) -> dict[str, Any]:
    return {
        "project": project,
        "args": args,
        "selected_lane": lane,
        "review": {
            "stale_memories": [], "duplicate_candidates": [], "low_confidence": [],
            "unreviewed_reflections": [], "unreviewed_episodes": [],
        },
        "reflection_quality": {"reflections": []},
        "query_misses": [],
        "semantic_conflicts": [],
        "refresh_drifts": [],
        "semantic_gap_targets": {},
        "learn_business_payload_template": {"files": []},
        "incident_strategy_candidates": [],
        "recurring_incident_fingerprint_candidates": [],
        "retrieval_interference_candidates": [],
        "experience_conflict_candidates": [],
        "incident_trace_actions": [],
        "graph_quality_actions": [],
        "graph_signal_quality_actions": [],
        "log_observability_gap_actions": [],
        "quality_gate_actions": [],
        "recurring_quality_gate_actions": [],
        "runtime_performance_actions": [],
        "semantic_provider_actions": [],
        "experience_usage_actions": [],
        "memory_tier_actions": [],
        "task_trace_actions": [],
        "active_learning_actions": [],
        "retrieval_feedback_actions": [],
        "calibration_feedback_actions": [],
        "quality_governance_actions": [],
        "weak_evidence_chain_actions": [],
        "maturity_governance_actions": [],
        "skill_pattern_candidates": [],
        "log_design_candidates": [],
    }


def empty_sections() -> dict[str, Any]:
    return {
        "graph_quality": {}, "graph_signal_quality": {}, "runtime_performance": {},
        "semantic_provider": {}, "experience_usage": {}, "memory_tiers": {},
        "active_learning_queue": {}, "retrieval_feedback_summary": {},
        "last_quality_gate": {}, "quality_summary": {}, "evidence_chain_summary": {},
        "low_quality_records": [], "high_value_records": [],
    }


def load_graph_group(
    project: Project,
    args: argparse.Namespace,
    ctx: dict[str, Any],
    sections: dict[str, Any],
) -> dict[str, Any]:
    quality = build_graph_quality(
        project,
        force_verify=bool(getattr(args, "verify_graph_quality", False)),
    )
    signal = build_graph_signal_quality(project, graph_quality=quality)
    sections["graph_quality"] = quality
    sections["graph_signal_quality"] = signal
    ctx["graph_quality_actions"] = build_graph_quality_actions(quality)
    ctx["graph_signal_quality_actions"] = build_graph_signal_quality_actions(signal)
    return signal


def load_quality_group(
    project: Project,
    limit: int,
    ctx: dict[str, Any],
    sections: dict[str, Any],
) -> dict[str, Any]:
    semantic_rows, reflection_rows = fetch_quality_memory_rows(project, limit)
    reflection_rows = enrich_reflections_with_evidence_chains(project, reflection_rows)
    report = build_quality_report(
        semantic_rows,
        reflection_rows,
        fetch_incident_trace_quality_rows(project, limit),
    )
    ctx["quality_governance_actions"] = build_quality_governance_actions(report)
    ctx["weak_evidence_chain_actions"] = build_weak_evidence_chain_actions(report)
    ctx["maturity_governance_actions"] = build_experience_maturity_actions(reflection_rows)
    sections["quality_summary"] = report["summary"]
    sections["evidence_chain_summary"] = build_evidence_chain_summary(reflection_rows)
    sections["low_quality_records"] = report["low_quality_records"]
    sections["high_value_records"] = report["high_value_records"]
    return report


def load_lane_dependencies(
    project: Project,
    args: argparse.Namespace,
    lane: str,
    ctx: dict[str, Any],
    sections: dict[str, Any],
) -> list[str]:
    groups: list[str] = []
    limit = int(args.limit)
    if lane == "memory_tiers":
        sections["memory_tiers"] = build_memory_tiers(project, limit)
        ctx["memory_tier_actions"] = build_memory_tier_actions(sections["memory_tiers"])
        return ["memory_tiers"]
    if lane == "graph_quality":
        load_graph_group(project, args, ctx, sections)
        sections["semantic_provider"] = semantic_provider_health(project)
        ctx["semantic_provider_actions"] = build_semantic_provider_actions(sections["semantic_provider"])
        return ["graph_quality", "graph_signal_quality", "semantic_provider"]
    if lane == "log_diagnosis":
        signal = load_graph_group(project, args, ctx, sections)
        review = build_review_data(project, limit)
        ctx["log_observability_gap_actions"] = build_log_observability_gap_actions(signal)
        ctx["log_design_candidates"] = build_log_design_gap_candidates(project, review["unreviewed_reflections"])
        ctx["query_misses"] = build_query_miss_data(project, limit)
        ctx["semantic_gap_targets"] = build_semantic_gap_targets(project)
        ctx["learn_business_payload_template"] = build_learn_business_payload_template(project)
        return ["graph_quality", "graph_signal_quality", "log_design", "query_misses", "semantic_gaps"]
    if lane == "memory_hygiene":
        ctx["review"] = build_review_data(project, limit)
        ctx["reflection_quality"] = build_reflect_review_data(project, limit)
        return ["review", "reflection_quality"]
    if lane in {"learn_semantic_repair", "experience_staleness", "skill_evolution", "incident_recurrence"}:
        ctx["review"] = build_review_data(project, limit)
        groups.append("review")
    if lane == "learn_semantic_repair":
        ctx["semantic_conflicts"] = build_recent_semantic_conflicts(project, limit)
        ctx["refresh_drifts"] = build_recent_refresh_drifts(project, limit)
        ctx["semantic_gap_targets"] = build_semantic_gap_targets(project)
        ctx["learn_business_payload_template"] = build_learn_business_payload_template(project)
        load_quality_group(project, limit, ctx, sections)
        return groups + ["semantic_repair", "quality"]
    if lane == "experience_staleness":
        ctx["refresh_drifts"] = build_recent_refresh_drifts(project, limit)
        return groups + ["refresh_drift"]
    if lane == "skill_evolution":
        rows = ctx["review"]["unreviewed_reflections"]
        ctx["incident_strategy_candidates"] = build_incident_strategy_candidates(project, rows)
        ctx["skill_pattern_candidates"] = build_skill_pattern_candidates(project, rows)
        load_quality_group(project, limit, ctx, sections)
        return groups + ["skill_candidates", "quality"]
    if lane == "incident_recurrence":
        rows = ctx["review"]["unreviewed_reflections"]
        ctx["recurring_incident_fingerprint_candidates"] = build_recurring_incident_fingerprint_candidates(project, rows)
        return groups + ["incident_recurrence"]
    if lane in {"experience_conflict", "retrieval_interference"}:
        rows = active_reflection_rows(project, limit=REVIEW_DUPLICATE_POOL_LIMIT)
        key = f"{lane}_candidates"
        ctx[key] = (
            build_experience_conflict_candidates(rows, limit)
            if lane == "experience_conflict"
            else build_retrieval_interference_candidates(rows, limit)
        )
        return ["active_reflections"]
    if lane == "semantic_conflict":
        ctx["semantic_conflicts"] = build_recent_semantic_conflicts(project, limit)
        return ["semantic_conflicts"]
    if lane == "incident_trace":
        ctx["incident_trace_actions"] = build_incident_trace_actions(project, limit)
        return ["incident_trace"]
    if lane == "quality_gate":
        sections["last_quality_gate"] = load_quality_gate_snapshot(project)
        ctx["quality_gate_actions"] = build_quality_gate_failure_actions(sections["last_quality_gate"])
        history = load_quality_gate_history_report(project, limit=20)
        ctx["recurring_quality_gate_actions"] = build_recurring_quality_gate_failure_actions(history)
        return ["quality_gate"]
    if lane == "runtime_performance":
        sections["runtime_performance"] = build_runtime_performance_summary(project)
        ctx["runtime_performance_actions"] = build_runtime_performance_actions(sections["runtime_performance"])
        return ["runtime_performance"]
    if lane == "experience_usage":
        sections["experience_usage"] = fetch_experience_usage_summary(project, limit)
        ctx["experience_usage_actions"] = build_experience_usage_actions(sections["experience_usage"])
        return ["experience_usage"]
    if lane == "auto_reflection":
        ctx["task_trace_actions"] = build_task_trace_actions(project)
        return ["task_trace"]
    if lane == "memory_quality":
        load_quality_group(project, limit, ctx, sections)
        feedback = fetch_open_retrieval_feedback(project, limit)
        ctx["retrieval_feedback_actions"] = build_retrieval_feedback_actions(feedback)
        ctx["calibration_feedback_actions"] = build_calibration_feedback_actions(feedback)
        sections["retrieval_feedback_summary"] = {
            **retrieval_feedback_summary(project),
            "open_feedback": len(feedback),
            "review_actions": len(ctx["retrieval_feedback_actions"]),
        }
        return ["quality", "retrieval_feedback"]
    if lane == "active_learning":
        signal = load_graph_group(project, args, ctx, sections)
        report = load_quality_group(project, limit, ctx, sections)
        sections["experience_usage"] = fetch_experience_usage_summary(project, limit)
        queue = build_active_learning_queue(
            project,
            graph_signal_quality=signal,
            experience_usage=sections["experience_usage"],
            quality_report=report,
            limit=limit,
        )
        sections["active_learning_queue"] = queue
        ctx["active_learning_actions"] = build_active_learning_actions(queue)
        return ["graph_quality", "graph_signal_quality", "quality", "experience_usage", "active_learning"]
    raise ValueError(f"unsupported focused governance lane: {lane}")


def build_focused_maintain_plan(
    project: Project,
    args: argparse.Namespace,
    lane: str,
) -> dict[str, Any]:
    ctx = empty_action_context(project, args, lane)
    sections = empty_sections()
    groups = load_lane_dependencies(project, args, lane, ctx, sections)
    actions = build_maintain_plan_actions(ctx)
    annotate_governance_action_priorities(actions)
    action_limit = max(1, int(getattr(args, "action_limit", 10) or 10))
    action_budget = build_governance_action_budget(actions, limit=action_limit, lane=lane)
    return {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "execution_scope": {
            "mode": "focused", "selected_lane": lane,
            "computed_groups": groups, "full_archive_summary": False,
        },
        "summary": {"selected_lane": lane, "candidate_actions": len(actions)},
        "governance_summary": {
            "counts_by_lane": {lane: len(actions)},
            "selected_lane_reviews": len(actions),
        },
        "learn_governance_summary": {},
        **sections,
        "action_budget": action_budget,
        "actions": actions,
        "advisory_notice": "maintain-plan only proposes actions. Execute changes only after user confirmation.",
    }
