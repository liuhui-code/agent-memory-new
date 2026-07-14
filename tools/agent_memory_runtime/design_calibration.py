# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .models import Project
from .records import row_dict
from .storage import connect


MIN_PROFILE_SAMPLES = 5


def design_features(
    proposal: dict[str, Any],
    evaluation: dict[str, Any],
    source_delta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    change_size = sum(len(proposal.get(field, [])) for field in (
        "add_nodes", "modify_nodes", "add_edges", "remove_edges",
    ))
    source_delta = source_delta or {}
    graph_delta = source_delta.get("graph_delta") or {}
    return {
        "archetype": proposal_archetype(proposal),
        "change_size_bucket": change_size_bucket(change_size),
        "change_size": change_size,
        "risk_count": len(evaluation.get("errors", [])) + len(evaluation.get("warnings", []))
        + len(proposal.get("assumptions", [])),
        "api_change_count": len(source_delta.get("api_changes", [])),
        "graph_delta_count": len(graph_delta.get("added_relations", []))
        + len(graph_delta.get("removed_relations", [])),
    }


def proposal_archetype(proposal: dict[str, Any]) -> str:
    terms = [
        str(node.get("kind", "")).lower() for node in proposal.get("add_nodes", [])
        if isinstance(node, dict)
    ]
    terms.extend(str(item).lower() for item in proposal.get("modify_nodes", []))
    groups = []
    if any("symbol:" in item or "api" in item or "interface" in item for item in terms):
        groups.append("api")
    if any(term in item for item in terms for term in ("storage", "repository", "database", "/data/", "data/")):
        groups.append("persistence")
    if any(term in item for item in terms for term in ("page", "component", "view", "/ui/")):
        groups.append("ui")
    if any(term in item for item in terms for term in ("service", "usecase", "domain")):
        groups.append("service")
    return "+".join(dict.fromkeys(groups)) or "general"


def change_size_bucket(change_size: int) -> str:
    if change_size <= 2:
        return "small"
    if change_size <= 6:
        return "medium"
    return "large"


def calibration_profile(project: Project, archetype: str, bucket: str) -> dict[str, Any]:
    with connect(project) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS sample_count,
                   SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) AS successes,
                   SUM(CASE WHEN outcome IN ('partial', 'failure') THEN 1 ELSE 0 END) AS risks,
                   AVG(replan_count) AS average_replan_count
            FROM design_outcomes
            WHERE project_id = ? AND archetype = ? AND change_size_bucket = ?
            """,
            (project.project_id, archetype, bucket),
        ).fetchone()
    value = row_dict(row)
    count = int(value.get("sample_count") or 0)
    risks = int(value.get("risks") or 0)
    risk_rate = round(risks / count, 4) if count else None
    return {
        "status": "advisory" if count >= MIN_PROFILE_SAMPLES else "insufficient_samples",
        "archetype": archetype,
        "change_size_bucket": bucket,
        "sample_count": count,
        "minimum_samples": MIN_PROFILE_SAMPLES,
        "historical_risk_rate": risk_rate if count >= MIN_PROFILE_SAMPLES else None,
        "risk_level": risk_level(risk_rate) if count >= MIN_PROFILE_SAMPLES else "unknown",
        "average_replan_count": round(float(value.get("average_replan_count") or 0.0), 4),
        "authority": "advisory_tie_break_only",
    }


def risk_level(rate: float | None) -> str:
    if rate is None:
        return "unknown"
    if rate >= 0.5:
        return "high"
    if rate >= 0.2:
        return "moderate"
    return "low"
