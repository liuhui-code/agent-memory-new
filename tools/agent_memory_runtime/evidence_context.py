# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import Counter
from typing import Any

from .architecture_slice import evidence_paths
from .evidence_fusion import build_evidence_chains, evidence_gaps, evidence_tiers, fuse_evidence
from .evidence_query_execution import execute_evidence_plan
from .goal_planner import build_goal_plan
from .models import Project
from .repository_model import build_repository_model, public_repository_model


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
    if plan.goal == "design":
        repository_model = build_repository_model(project, query, evidence_paths(ranked))
        payload["repository_model"] = public_repository_model(repository_model)
        payload["architecture_slice"] = repository_model["architecture"]
        payload["evidence_gaps"].extend(repository_model["evidence_gaps"])
    return payload


def recommended_actions(ranked: list[Any], goal: str) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    code_locations = [item.location for item in ranked if item.source == "code" and item.location]
    if code_locations:
        actions.append({"action": "inspect_current_source", "target": code_locations[0]})
    if goal == "change_impact":
        actions.append({"action": "run_impact_scope", "target": "current Git diff"})
    if goal == "design":
        actions.append({"action": "compare_delta_graphs", "target": "candidate design proposals"})
    actions.append({"action": "verify_before_reflect", "target": "tests, source inspection, or runtime evidence"})
    return actions[:4]
