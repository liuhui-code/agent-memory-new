# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .models import ACTIVE_STATUS, Project
from .quality_scoring import score_reflection_quality, score_semantic_quality
from .records import row_dict
from .storage import connect


SCAN_LIMIT = 500
TARGET_LIMIT = 10


def build_memory_tiers(project: Project, limit: int = TARGET_LIMIT) -> dict[str, Any]:
    records = fetch_tier_records(project)
    counts = {"hot": 0, "warm": 0, "cold": 0, "archive_candidate": 0}
    review_targets: list[dict[str, Any]] = []
    for record in records:
        classified = classify_memory_record(record)
        tier = classified["tier"]
        counts[tier] = counts.get(tier, 0) + 1
        if tier in {"cold", "archive_candidate"}:
            review_targets.append(classified)
    review_targets.sort(
        key=lambda item: (
            1 if item["tier"] == "archive_candidate" else 0,
            float(item.get("priority_score") or 0.0),
            int(item.get("target_id") or 0),
        ),
        reverse=True,
    )
    return {
        "counts": counts,
        "scanned_records": len(records),
        "scan_limit_per_type": SCAN_LIMIT,
        "review_targets": review_targets[:limit],
    }


def fetch_tier_records(project: Project) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with connect(project) as conn:
        semantic_rows = conn.execute(
            """
            SELECT *
            FROM semantic_facts
            WHERE project_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, SCAN_LIMIT),
        ).fetchall()
        reflection_rows = conn.execute(
            """
            SELECT *
            FROM reflections
            WHERE project_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, SCAN_LIMIT),
        ).fetchall()
        episode_rows = conn.execute(
            """
            SELECT *
            FROM episodes
            WHERE project_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, SCAN_LIMIT),
        ).fetchall()
    for row in semantic_rows:
        item = row_dict(row)
        item["_record_type"] = "semantic"
        records.append(item)
    for row in reflection_rows:
        item = row_dict(row)
        item["_record_type"] = "reflection"
        records.append(item)
    for row in episode_rows:
        item = row_dict(row)
        item["_record_type"] = "episode"
        records.append(item)
    return records


def classify_memory_record(record: dict[str, Any]) -> dict[str, Any]:
    record_type = str(record.get("_record_type") or "memory")
    status = str(record.get("status") or ACTIVE_STATUS)
    use_count = int(record.get("use_count") or 0)
    confidence = confidence_value(record)
    quality_score = quality_value(record_type, record)
    reasons: list[str] = []
    if status in {"stale", "archived", "rejected", "merged"} or truthy(record.get("is_stale")):
        tier = "archive_candidate"
        reasons.append(f"status is {status}")
    elif use_count >= 3 or bool(str(record.get("last_used_at") or "").strip()):
        tier = "hot"
        reasons.append("recent or repeated usage")
    elif use_count == 0 and (confidence < 0.5 or quality_score < 0.45):
        tier = "cold"
        reasons.append("low confidence or quality with no use")
    else:
        tier = "warm"
        reasons.append("active memory without strong hot or cold signal")
    return {
        "tier": tier,
        "target_type": record_type,
        "target_id": record.get("id"),
        "title": title_for_record(record_type, record),
        "priority_score": tier_priority(tier, confidence, quality_score, use_count),
        "reason": "; ".join(reasons),
        "confidence": confidence,
        "quality_score": quality_score,
        "use_count": use_count,
        "status": status,
        "suggested_actions": suggested_actions_for_tier(tier, record_type),
    }


def build_memory_tier_actions(memory_tiers: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for target in memory_tiers.get("review_targets") or []:
        actions.append(
            {
                "action": "review_memory_tier",
                "governance_lane": "memory_tiers",
                "type": target.get("target_type"),
                "id": target.get("target_id"),
                "tier": target.get("tier"),
                "reason": target.get("reason"),
                "risk": "low" if target.get("tier") == "cold" else "medium",
                "requires_confirmation": True,
                "command": None,
                "memory_tier": target,
                "suggested_actions": target.get("suggested_actions") or [],
            }
        )
    return actions


def quality_value(record_type: str, record: dict[str, Any]) -> float:
    if record_type == "semantic":
        return float(score_semantic_quality(record)["quality_score"])
    if record_type == "reflection":
        return float(score_reflection_quality(record)["quality_score"])
    return 0.6


def confidence_value(record: dict[str, Any]) -> float:
    try:
        return float(record.get("confidence") if record.get("confidence") is not None else 0.8)
    except (TypeError, ValueError):
        return 0.8


def tier_priority(tier: str, confidence: float, quality_score: float, use_count: int) -> float:
    if tier == "archive_candidate":
        return round(80 + (1.0 - min(confidence, quality_score)) * 10, 3)
    if tier == "cold":
        return round(55 + (1.0 - min(confidence, quality_score)) * 20, 3)
    if tier == "hot":
        return round(45 + min(use_count, 10) * 2, 3)
    return 30.0


def suggested_actions_for_tier(tier: str, record_type: str) -> list[str]:
    if tier == "archive_candidate":
        return ["verify_stale_signal", "archive_after_confirmation", "merge_if_duplicate"]
    if tier == "cold":
        return ["verify_against_source", "tighten_or_enrich", "archive_if_unneeded"]
    if tier == "hot" and record_type == "reflection":
        return ["review_for_skill_or_pattern_promotion"]
    return ["keep_active"]


def title_for_record(record_type: str, record: dict[str, Any]) -> str:
    if record_type == "semantic":
        return str(record.get("fact") or "")[:120]
    if record_type == "reflection":
        return str(record.get("task") or record.get("lesson") or "")[:120]
    if record_type == "episode":
        return str(record.get("task") or record.get("summary") or "")[:120]
    return f"{record_type} #{record.get('id')}"


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes"}
