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



from .governance_corrections import build_experience_conflict_candidates, build_retrieval_interference_candidates
from .governance_incidents import build_incident_strategy_candidates, build_log_design_gap_candidates, build_recurring_incident_fingerprint_candidates
from .governance_review import reflection_quality_issues
from .governance_skill_candidates import build_skill_pattern_candidates
from .governance_utils import duplicate_candidates, fetch_memory_rows

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
