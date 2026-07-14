# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import Counter
from typing import Any

from .evidence_collectors import collect_evidence_candidates
from .evidence_models import EvidenceItem, GoalPlan
from .models import Project
from .storage import connect


def execute_evidence_plan(
    project: Project,
    plan: GoalPlan,
) -> tuple[list[EvidenceItem], dict[str, Any]]:
    selected: dict[str, EvidenceItem] = {}
    rounds: list[dict[str, Any]] = []
    primary_metadata: dict[str, Any] = {}
    stop_reason = "max_rounds"
    for index, subquery in enumerate(plan.subqueries[: plan.max_rounds], start=1):
        candidates, metadata = collect_evidence_candidates(project, subquery)
        if index == 1:
            primary_metadata = metadata
        before = len(selected)
        for item in candidates:
            previous = selected.get(item.evidence_id)
            if previous is None or item.original_score > previous.original_score:
                selected[item.evidence_id] = item
        new_count = len(selected) - before
        novelty = new_count / max(1, len(candidates))
        rounds.append(
            {
                "round": index,
                "query": subquery,
                "candidate_count": len(candidates),
                "new_evidence_count": new_count,
                "novelty_ratio": round(novelty, 3),
            }
        )
        if index == 1 and has_sufficient_coverage(plan, list(selected.values())):
            stop_reason = "sufficient_cross_lane_coverage"
            break
        if index > 1 and new_count == 0:
            stop_reason = "no_new_evidence"
            break
        if index > 1 and novelty < plan.novelty_threshold:
            stop_reason = "low_novelty"
            break
    if plan.query_scope == "global":
        for item in collect_global_evidence(project):
            selected[item.evidence_id] = item
    metadata = dict(primary_metadata)
    metadata["query_execution"] = {
        "scope": plan.query_scope,
        "rounds": rounds,
        "round_count": len(rounds),
        "stop_reason": stop_reason,
        "unique_evidence_count": len(selected),
    }
    metadata["candidate_counts"] = dict(Counter(item.source for item in selected.values()))
    return list(selected.values()), metadata


def has_sufficient_coverage(plan: GoalPlan, items: list[EvidenceItem]) -> bool:
    sources = {item.source for item in items}
    if len(items) < 3:
        return False
    if plan.goal == "diagnosis":
        return "code" in sources and bool({"log", "incident"} & sources)
    if plan.goal == "change_impact":
        return "code" in sources and "edge" in sources
    if plan.goal == "design":
        return "code" in sources and "edge" in sources
    if plan.goal == "experience_reuse":
        return "reflection" in sources and "code" in sources
    if plan.goal == "governance":
        return bool({"reflection", "semantic"} & sources)
    return "code" in sources and bool({"edge", "log"} & sources)


def collect_global_evidence(project: Project) -> list[EvidenceItem]:
    with connect(project) as conn:
        languages = aggregate_rows(
            conn,
            "SELECT COALESCE(language, 'unknown') AS name, COUNT(*) AS count FROM code_files WHERE project_id = ? GROUP BY language ORDER BY count DESC LIMIT 8",
            project.project_id,
        )
        relations = aggregate_rows(
            conn,
            "SELECT relation AS name, COUNT(*) AS count FROM memory_edges WHERE project_id = ? AND valid_to IS NULL GROUP BY relation ORDER BY count DESC LIMIT 8",
            project.project_id,
        )
        incidents = aggregate_rows(
            conn,
            "SELECT arkts_scene || ':' || status AS name, COUNT(*) AS count FROM incident_traces WHERE project_id = ? GROUP BY arkts_scene, status ORDER BY count DESC LIMIT 8",
            project.project_id,
        )
        experiences = aggregate_rows(
            conn,
            "SELECT COALESCE(experience_type, 'untyped') AS name, COUNT(*) AS count FROM reflections WHERE project_id = ? AND COALESCE(status, 'active') = 'active' GROUP BY experience_type ORDER BY count DESC LIMIT 8",
            project.project_id,
        )
    return [
        aggregate_item("code_languages", "code", "Code language distribution", languages),
        aggregate_item("graph_relations", "edge", "Active graph relation distribution", relations),
        aggregate_item("incident_scenes", "incident", "Incident scene and status distribution", incidents),
        aggregate_item("experience_types", "reflection", "Active experience type distribution", experiences),
    ]


def aggregate_rows(conn: Any, sql: str, project_id: str) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql, (project_id,)).fetchall()]


def aggregate_item(key: str, source: str, title: str, rows: list[dict[str, Any]]) -> EvidenceItem:
    summary = ", ".join(f"{row['name']}={row['count']}" for row in rows) or "no data"
    return EvidenceItem(
        evidence_id=f"aggregate:{key}",
        source=source,
        kind="aggregate_summary",
        record_id=None,
        title=title,
        summary=summary,
        location=None,
        authority="aggregate_evidence",
        original_score=1.0,
        reasons=["bounded global aggregate"],
        raw={"rows": rows},
    )
