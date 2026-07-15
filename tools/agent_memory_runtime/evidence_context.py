# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any

from .architecture_slice import evidence_paths
from .diagnosis_hypotheses import build_evidence_hypothesis_ledger, persist_hypothesis_ledger
from .evidence_fusion import build_evidence_chains, evidence_gaps, evidence_tiers, fuse_evidence
from .evidence_query_execution import execute_evidence_plan
from .goal_planner import build_goal_plan
from .models import Project
from .performance_scoring import append_performance_sample, build_performance_sample, estimate_payload_tokens, monotonic_ms
from .records import output
from .repository_model import build_repository_model, public_repository_model
from .query_results import record_query_miss_if_empty
from .storage import ensure_initialized, resolve_project
from .usage_samples import record_query_usage


def evidence_context_command(args: argparse.Namespace) -> None:
    started_ms = monotonic_ms()
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    payload = build_evidence_context(
        project,
        args.query,
        explicit_goal=args.goal,
        max_items=args.max_items,
        explicit_scope=args.scope,
    )
    persist_last_evidence_context(project, payload)
    if payload.get("hypothesis_ledger"):
        persist_hypothesis_ledger(project, payload["hypothesis_ledger"])
    compact_usage = usage_view(payload)
    record_query_usage(project, "evidence-context", args.query, compact_usage)
    record_query_miss_if_empty(project, "evidence-context", args.query, compact_usage)
    append_performance_sample(
        project,
        build_performance_sample(
            project,
            "evidence-context",
            monotonic_ms() - started_ms,
            payload["audit"]["counts_by_source"],
            estimate_payload_tokens(payload),
        ),
    )
    output(payload, args.json)


def build_evidence_context(
    project: Project,
    query: str,
    explicit_goal: str | None = None,
    max_items: int = 20,
    explicit_scope: str | None = None,
) -> dict[str, Any]:
    plan = build_goal_plan(query, explicit_goal, max_items, explicit_scope)
    candidates, retrieval = execute_evidence_plan(project, plan)
    ranked = fuse_evidence(candidates, plan)
    counts_by_source = Counter(item.source for item in ranked)
    counts_by_authority = Counter(item.authority for item in ranked)
    chains = build_evidence_chains(ranked)
    gaps = evidence_gaps(ranked, plan)
    payload = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "query": query,
        "goal_plan": plan.to_dict(),
        "advisory_notice": "Current source and explicit user instructions override historical memory.",
        "evidence": evidence_tiers(ranked),
        "evidence_chains": chains,
        "evidence_gaps": gaps,
        "recommended_actions": recommended_actions(ranked, plan.goal),
        "retrieval_metadata": retrieval,
        "audit": {
            "candidate_counts": retrieval["candidate_counts"],
            "returned_count": len(ranked),
            "counts_by_source": dict(counts_by_source),
            "counts_by_authority": dict(counts_by_authority),
            "score_model": "bounded_goal_evidence_fusion_v1",
            "score_range": [0, 100],
        },
    }
    if plan.goal == "diagnosis":
        payload["hypothesis_ledger"] = build_evidence_hypothesis_ledger(query, chains, gaps)
    if plan.goal == "design":
        repository_model = build_repository_model(project, query, evidence_paths(ranked))
        payload["repository_model"] = public_repository_model(repository_model)
        payload["architecture_slice"] = repository_model["architecture"]
        payload["evidence_gaps"].extend(repository_model["evidence_gaps"])
    return payload


def recommended_actions(ranked: list[Any], goal: str) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    code_locations = [item.location for item in ranked if item.source == "code" and item.location]
    log_locations = [item.location for item in ranked if item.source == "log" and item.location]
    if code_locations:
        actions.append({"action": "inspect_current_source", "target": code_locations[0]})
    if goal == "diagnosis" and log_locations:
        actions.append({"action": "match_runtime_log", "target": log_locations[0]})
    if goal == "change_impact":
        actions.append({"action": "run_impact_scope", "target": "current Git diff"})
    if goal == "design":
        actions.append({"action": "compare_delta_graphs", "target": "candidate design proposals"})
    actions.append({"action": "verify_before_reflect", "target": "tests, source inspection, or runtime evidence"})
    return actions[:4]


def usage_view(payload: dict[str, Any]) -> dict[str, Any]:
    groups = {
        "semantic_facts": "semantic",
        "reflections": "reflection",
        "episodes": "episode",
        "wiki_matches": "code",
        "code_log_matches": "log",
        "edge_matches": "edge",
        "incident_trace_matches": "incident",
    }
    counts = payload["audit"]["counts_by_source"]
    view: dict[str, Any] = {
        key: [{} for _ in range(int(counts.get(source, 0)))]
        for key, source in groups.items()
    }
    view["followup_focus"] = payload["goal_plan"]["goal"]
    view["suggested_followup_terms"] = [
        gap["kind"] for gap in payload.get("evidence_gaps") or []
    ]
    view["query_execution"] = payload.get("retrieval_metadata", {}).get("query_execution") or {}
    view["causal_levels"] = [
        str(chain.get("causal_evidence", {}).get("level") or "association")
        for chain in payload.get("evidence_chains") or []
    ]
    return view


def persist_last_evidence_context(project: Project, payload: dict[str, Any]) -> None:
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_evidence_context.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
