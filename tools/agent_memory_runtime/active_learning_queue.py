# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .models import Project
from .records import row_dict
from .storage import connect


def build_active_learning_queue(
    project: Project,
    graph_signal_quality: dict[str, Any] | None = None,
    experience_usage: dict[str, Any] | None = None,
    quality_report: dict[str, Any] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    items.extend(query_miss_items(project))
    items.extend(graph_signal_items(graph_signal_quality or {}))
    items.extend(experience_usage_items(experience_usage or {}))
    items.extend(low_quality_items(quality_report or {}))
    items.sort(key=lambda item: (float(item["priority_score"]), str(item["queue_id"])), reverse=True)
    top_items = items[:limit]
    lanes: dict[str, int] = {}
    for item in items:
        lane = str(item["lane"])
        lanes[lane] = lanes.get(lane, 0) + 1
    return {
        "queue_count": len(items),
        "top_priority_score": top_items[0]["priority_score"] if top_items else 0,
        "lanes": lanes,
        "top_items": top_items,
    }


def query_miss_items(project: Project, limit: int = 20) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM query_misses
            WHERE project_id = ?
              AND status = 'open'
            ORDER BY COALESCE(miss_count, 1) DESC, COALESCE(last_seen_at, created_at) DESC, id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = row_dict(row)
        miss_count = int(item.get("miss_count") or 1)
        score = 50 + min(miss_count, 10) * 4
        items.append(
            {
                "queue_id": f"query_miss:{item['id']}",
                "priority_score": round(float(score), 3),
                "lane": "query_miss",
                "target_type": "query_miss",
                "target_id": item["id"],
                "title": str(item.get("query") or ""),
                "reason": "repeated query miss needs learning, business terms, or reflection repair",
                "suggested_action": "review_query_miss",
                "source_signals": {
                    "miss_count": miss_count,
                    "source": item.get("source"),
                    "last_seen_at": item.get("last_seen_at") or item.get("created_at"),
                },
            }
        )
    return items


def graph_signal_items(graph_signal_quality: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for target in graph_signal_quality.get("top_repair_targets") or []:
        missing = len(target.get("missing_signals") or [])
        score = 45 + missing * 3
        title = str(target.get("message_template") or target.get("function_name") or target.get("file_path") or target.get("target_type"))
        items.append(
            {
                "queue_id": f"graph_signal:{target.get('target_type')}:{target.get('target_id')}",
                "priority_score": round(float(score), 3),
                "lane": "graph_signal",
                "target_type": target.get("target_type"),
                "target_id": target.get("target_id"),
                "title": title,
                "reason": target.get("reason") or "graph anchor has weak diagnostic or business signal",
                "suggested_action": "repair_graph_signal",
                "source_signals": {
                    "file_path": target.get("file_path"),
                    "missing_signals": target.get("missing_signals") or [],
                    "suggested_fields": target.get("suggested_fields") or [],
                    "log_signal_score": target.get("log_signal_score"),
                },
            }
        )
    return items


def experience_usage_items(experience_usage: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for record in experience_usage.get("records") or []:
        outcomes = record.get("outcomes") or {}
        negative_count = int(record.get("negative_count") or 0)
        positive_count = int(record.get("positive_count") or 0)
        if negative_count:
            score = 65 + negative_count * 5
            suggested_action = "tighten_or_stale_experience"
            reason = "experience has misleading or superseded task outcomes"
        elif positive_count:
            score = 42 + positive_count * 3
            suggested_action = "review_for_promotion_or_reuse"
            reason = "experience has helpful task outcomes"
        else:
            continue
        items.append(
            {
                "queue_id": f"experience_usage:{record.get('record_type')}:{record.get('record_id')}",
                "priority_score": round(float(score), 3),
                "lane": "experience_usage",
                "target_type": record.get("record_type"),
                "target_id": record.get("record_id"),
                "title": f"{record.get('record_type')} #{record.get('record_id')}",
                "reason": reason,
                "suggested_action": suggested_action,
                "source_signals": {
                    "outcomes": outcomes,
                    "dominant_outcome": record.get("dominant_outcome"),
                    "negative_count": negative_count,
                    "positive_count": positive_count,
                    "last_seen_at": record.get("last_seen_at"),
                },
            }
        )
    return items


def low_quality_items(quality_report: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for record in quality_report.get("low_quality_records") or []:
        try:
            quality_score = float(record.get("quality_score") or 0.0)
        except (TypeError, ValueError):
            quality_score = 0.0
        score = 40 + (1.0 - max(0.0, min(1.0, quality_score))) * 20
        record_type = str(record.get("record_type") or "memory")
        record_id = record.get("record_id")
        items.append(
            {
                "queue_id": f"low_quality:{record_type}:{record_id}",
                "priority_score": round(float(score), 3),
                "lane": "low_quality_memory",
                "target_type": record_type,
                "target_id": record_id,
                "title": f"{record_type} #{record_id}",
                "reason": "memory quality score is below review threshold",
                "suggested_action": "review_low_quality_memory",
                "source_signals": {
                    "quality_score": quality_score,
                    "quality_band": record.get("quality_band"),
                    "quality_reasons": record.get("reasons") or [],
                },
            }
        )
    return items


def build_active_learning_actions(queue: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for item in queue.get("top_items") or []:
        actions.append(
            {
                "action": "review_active_learning_queue",
                "governance_lane": "active_learning",
                "type": item.get("target_type"),
                "id": item.get("target_id"),
                "reason": item.get("reason"),
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                "queue_item": item,
                "suggested_actions": [item.get("suggested_action")],
            }
        )
    return actions
