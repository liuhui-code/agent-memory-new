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



from .governance_corrections import build_correction_targets
from .governance_review_data import active_reflection_rows
from .governance_utils import extract_path_like_values, stable_unique_strings

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



def build_learn_governance_summary(
    correction_rows: list[dict[str, Any]],
    refresh_drifts: list[dict[str, Any]],
) -> dict[str, Any]:
    top_affected_paths = stable_unique_strings(
        [
            *[
                path
                for row in correction_rows
                for path in build_correction_targets(row).get("file_paths", [])
            ],
            *[
                path
                for drift in refresh_drifts
                for path in [
                    *(drift.get("added_files") or []),
                    *(drift.get("changed_files") or []),
                    *(drift.get("removed_files") or []),
                ]
            ],
        ]
    )[:10]
    return {
        "correction_repairs": len(correction_rows),
        "semantic_drift_reviews": len(refresh_drifts),
        "top_affected_paths": top_affected_paths,
    }



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
