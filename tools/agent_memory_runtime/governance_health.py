# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import sqlite3
import re
from pathlib import Path
from typing import Any

from .active_learning_queue import build_active_learning_actions, build_active_learning_queue
from .agent_benchmark_governance import agent_benchmark_summary
from .code_wiki import semantic_followup_from_db
from .context_capability_governance import context_capability_summary
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
from .index_freshness import index_health_summary
from .design_outcome import design_calibration_summary
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
from .semantic_provider_metrics import semantic_provider_health
from .quality_scoring import build_quality_report
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



from .governance_incidents import (
    build_incident_strategy_candidates,
    build_log_design_gap_candidates,
    build_recurring_incident_fingerprint_candidates,
)
from .governance_quality_actions import fetch_incident_trace_quality_rows
from .governance_review_data import build_scope_health_rows
from .governance_utils import duplicate_candidates, fetch_memory_rows

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



def maintain_health(args: argparse.Namespace) -> None:
    started_ms = monotonic_ms()
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
    scope_overflow = sum(1 for row in scope_health_rows if row["health_status"] == "overflow")
    scope_boundary_drift = sum(1 for row in scope_health_rows if row["health_status"] == "boundary_drift")
    scope_with_drift = sum(1 for row in scope_health_rows if row["health_status"] in {"drift", "high_drift"})
    scope_high_drift = sum(1 for row in scope_health_rows if row["health_status"] == "high_drift")
    incident_strategy_candidates = build_incident_strategy_candidates(project, reflection_active_rows)
    recurring_incident_fingerprints = build_recurring_incident_fingerprint_candidates(project, reflection_active_rows)
    log_design_gaps = build_log_design_gap_candidates(project, reflection_active_rows)
    graph_quality = build_graph_quality(
        project,
        force_verify=bool(getattr(args, "verify_graph_quality", False)),
    )
    graph_signal_quality = build_graph_signal_quality(project, graph_quality=graph_quality)
    experience_usage = fetch_experience_usage_summary(project)
    memory_tiers = build_memory_tiers(project)
    health_quality_report = build_quality_report(
        semantic_active_rows[:10],
        enrich_reflections_with_evidence_chains(project, reflection_active_rows[:10]),
        fetch_incident_trace_quality_rows(project, 10),
    )
    active_learning_queue = build_active_learning_queue(
        project,
        graph_signal_quality=graph_signal_quality,
        experience_usage=experience_usage,
        quality_report=health_quality_report,
        limit=5,
    )
    last_quality_gate = load_quality_gate_snapshot(project)
    impact_feedback = impact_feedback_summary(project)
    design_calibration = design_calibration_summary(project)
    provider_health = semantic_provider_health(project)
    agent_benchmark = agent_benchmark_summary(project)
    context_capability = context_capability_summary(project)
    retrieval_observations = retrieval_feedback_summary(project)
    code_index = index_health_summary(project)

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
    if graph_quality["health_status"] != "ok":
        recommended_actions.append("Review code/log graph quality and refresh stale or orphan anchors.")
    if graph_signal_quality["health_status"] != "ok":
        recommended_actions.append("Review graph signal quality and enrich weak code/log anchors.")
    if experience_usage["misleading_records"]:
        recommended_actions.append("Review experience usage outcomes and tighten misleading memories.")
    if active_learning_queue["queue_count"]:
        recommended_actions.append("Use the active learning queue to handle the highest-priority miss, weak graph anchor, or experience outcome first.")
    if memory_tiers["review_targets"]:
        recommended_actions.append("Review cold or archive-candidate memories before adding heavier retrieval infrastructure.")
    if last_quality_gate.get("quality_gate") == "fail":
        failed = ", ".join(str(item) for item in (last_quality_gate.get("summary") or {}).get("failed_gate_names") or [])
        recommended_actions.append(f"Review latest quality gate failure{f': {failed}' if failed else ''}.")
    if int(provider_health.get("fallbacks") or 0) >= 2:
        recommended_actions.append("Review repeated semantic-provider fallback reasons before trusting static-only graph coverage.")
    if agent_benchmark.get("quality_gate") == "fail":
        failure_class = agent_benchmark.get("primary_failure_class")
        recommended_actions.append(
            "Review the latest Agent A/B benchmark regressions"
            f"{f' ({failure_class})' if failure_class else ''} before changing retrieval or design behavior."
        )
    if agent_benchmark.get("efficiency_gate") == "fail":
        recommended_actions.append(
            "Review Agent A/B token, elapsed-time, source-read amplification, and tool-output attribution before expanding retrieval context."
        )
    if context_capability.get("system_context_gate") == "fail":
        failed = ", ".join(context_capability.get("failed_case_ids") or [])
        failure_class = context_capability.get("primary_failure_class")
        failure_suffix = (
            f" Start with failure class {failure_class}." if failure_class else ""
        )
        recommended_actions.append(
            "Repair the latest system context capability failures"
            f"{f': {failed}' if failed else ''} before another external Agent A/B."
            f"{failure_suffix}"
        )
    if code_index["status"] == "legacy_unverified":
        recommended_actions.append(
            "Refresh learned scopes so source-derived rows receive content digests."
        )
    if scope_overflow:
        recommended_actions.append(
            "Review overflow learn scopes and run a confirmed full refresh by scope id."
        )
    if scope_boundary_drift:
        recommended_actions.append(
            "Review changed Scope boundary dependencies before trusting affected business context."
        )

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
            "scope_overflow": scope_overflow,
            "scope_boundary_drift": scope_boundary_drift,
            "scope_with_drift": scope_with_drift,
            "scope_high_drift": scope_high_drift,
            "incident_strategy_candidates": len(incident_strategy_candidates),
            "recurring_incident_fingerprints": len(recurring_incident_fingerprints),
            "log_design_gaps": len(log_design_gaps),
        },
        "scope_health": scope_health_rows[:10],
        "governance_summary": {
            "learn_semantic_repair": {
                "scope_with_drift": scope_with_drift,
                "scope_high_drift": scope_high_drift,
            },
            "incident_diagnosis": {
                "incident_strategy_candidates": len(incident_strategy_candidates),
                "recurring_incident_fingerprints": len(recurring_incident_fingerprints),
                "log_design_gaps": len(log_design_gaps),
            },
        },
        "graph_quality": graph_quality,
        "graph_signal_quality": graph_signal_quality,
        "experience_usage": {
            "event_count": experience_usage["event_count"],
            "misleading_records": experience_usage["misleading_records"],
            "helpful_records": experience_usage["helpful_records"],
            "stable_signal_count": experience_usage["stable_signal_count"],
            "pending_signal_count": experience_usage["pending_signal_count"],
            "truncated": experience_usage["truncated"],
            "records": experience_usage["records"],
        },
        "active_learning_queue": active_learning_queue,
        "memory_tiers": memory_tiers,
        "last_quality_gate": last_quality_gate,
        "impact_feedback": impact_feedback,
        "design_calibration": design_calibration,
        "agent_benchmark": agent_benchmark,
        "context_capability": context_capability,
        "retrieval_observations": retrieval_observations,
        "code_index": code_index,
        "runtime_performance": build_runtime_performance_summary(project),
        "semantic_provider": provider_health,
        "recommended_actions": recommended_actions,
    }
    append_performance_sample(
        project,
        build_performance_sample(
            project,
            "maintain-health",
            monotonic_ms() - started_ms,
            data["counts"],
            estimate_payload_tokens(data),
        ),
    )
    output(data, args.json)
