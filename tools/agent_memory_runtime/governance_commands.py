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



from .governance_incidents import build_incident_strategy_candidates, build_recurring_incident_fingerprint_candidates
from .governance_skill_artifacts import (
    annotate_skill_pattern_artifacts,
    build_skill_candidate_markdown,
    build_skill_candidate_package_markdown,
    build_skill_promotion_checklist_markdown,
    guarded_write_artifact,
    read_frontmatter_metadata,
    skill_candidate_package_path,
    skill_candidate_promotion_checklist_path,
)
from .governance_skill_candidates import build_skill_pattern_candidates
from .governance_review_data import active_reflection_rows

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



def maintain_incident_fingerprint_draft(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    candidates = build_recurring_incident_fingerprint_candidates(project, active_reflection_rows(project))
    candidate = next((item for item in candidates if item["fingerprint_name"] == args.fingerprint_name), None)
    if not candidate:
        raise SystemExit(f"incident fingerprint candidate not found: {args.fingerprint_name}")
    draft_path = project.root / candidate["draft_path"]
    write_result = guarded_write_artifact(draft_path, candidate["draft_markdown"])
    payload = {
        "fingerprint_name": candidate["fingerprint_name"],
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
