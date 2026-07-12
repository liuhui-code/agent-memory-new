# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


DEFAULT_TOP_LIMIT = 10

RISK_WEIGHT = {
    "high": 0.75,
    "medium": 0.5,
    "low": 0.25,
}

LANE_WEIGHT = {
    "semantic_conflict": 0.22,
    "learn_semantic_repair": 0.2,
    "experience_conflict": 0.18,
    "experience_staleness": 0.18,
    "memory_quality": 0.16,
    "retrieval_feedback": 0.15,
    "experience_usage": 0.15,
    "runtime_performance": 0.14,
    "memory_tiers": 0.12,
    "log_diagnosis": 0.1,
    "graph_quality": 0.1,
    "skill_evolution": 0.08,
}

ACTION_WEIGHT = {
    "review_experience_conflict": 0.22,
    "review_semantic_conflict": 0.2,
    "review_retrieval_interference": 0.18,
    "review_semantic_patch": 0.18,
    "review_runtime_performance_budget": 0.16,
    "review_experience_usage": 0.15,
    "review_active_learning_queue": 0.14,
    "review_memory_tier": 0.12,
    "review_query_miss": 0.1,
}


def annotate_governance_action_priorities(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for action in actions:
        score, reasons = score_governance_action(action)
        action["priority_score"] = score
        action["priority_reasons"] = reasons
    return actions


def build_governance_action_budget(
    actions: list[dict[str, Any]],
    limit: int = DEFAULT_TOP_LIMIT,
) -> dict[str, Any]:
    sorted_actions = sorted(
        actions,
        key=lambda item: (
            float(item.get("priority_score") or 0.0),
            1 if item.get("requires_confirmation") else 0,
            str(item.get("action") or ""),
            str(item.get("id") or ""),
        ),
        reverse=True,
    )
    return {
        "total_actions": len(actions),
        "requires_confirmation": sum(1 for action in actions if action.get("requires_confirmation")),
        "counts_by_lane": count_by(actions, "governance_lane"),
        "counts_by_risk": count_by(actions, "risk"),
        "top_limit": limit,
        "next_command_templates": next_command_templates(limit),
        "top_actions": [compact_action(action, index + 1) for index, action in enumerate(sorted_actions[:limit])],
    }


def compact_maintain_plan_payload(data: dict[str, Any]) -> dict[str, Any]:
    action_budget = data.get("action_budget") or {}
    memory_tiers = data.get("memory_tiers") or {}
    active_learning_queue = data.get("active_learning_queue") or {}
    graph_quality = data.get("graph_quality") or {}
    graph_signal_quality = data.get("graph_signal_quality") or {}
    runtime_performance = data.get("runtime_performance") or {}
    quality_summary = data.get("quality_summary") or {}
    evidence_chain_summary = data.get("evidence_chain_summary") or {}
    experience_usage = data.get("experience_usage") or {}
    retrieval_feedback_summary = data.get("retrieval_feedback_summary") or {}

    return {
        "project_id": data.get("project_id"),
        "project_path": data.get("project_path"),
        "compact": True,
        "summary": data.get("summary") or {},
        "governance_summary": data.get("governance_summary") or {},
        "learn_governance_summary": data.get("learn_governance_summary") or {},
        "action_budget": action_budget,
        "health_overview": {
            "graph_health_status": graph_quality.get("health_status"),
            "graph_signal_status": graph_signal_quality.get("health_status"),
            "graph_signal_repair_target_count": len(graph_signal_quality.get("top_repair_targets") or []),
            "runtime_performance_operations": sorted((runtime_performance.get("operations") or {}).keys()),
            "experience_usage_event_count": experience_usage.get("event_count", 0),
            "memory_tier_counts": memory_tiers.get("counts") or {},
            "active_learning_queue_count": active_learning_queue.get("queue_count", 0),
            "retrieval_feedback_open": retrieval_feedback_summary.get("open_feedback", 0),
            "low_quality_record_count": quality_summary.get("low_quality_count", 0),
            "high_value_record_count": quality_summary.get("high_value_count", 0),
            "evidence_chain_summary": evidence_chain_summary,
        },
        "actions": action_budget.get("top_actions") or [],
        "omitted_sections": [
            "graph_quality",
            "graph_signal_quality",
            "runtime_performance",
            "experience_usage",
            "memory_tiers",
            "active_learning_queue",
            "retrieval_feedback_summary",
            "quality_summary",
            "evidence_chain_summary",
            "low_quality_records",
            "high_value_records",
            "full_actions",
        ],
        "advisory_notice": data.get("advisory_notice"),
    }


def score_governance_action(action: dict[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.05
    risk = str(action.get("risk") or "low")
    lane = str(action.get("governance_lane") or "")
    action_name = str(action.get("action") or "")

    risk_score = RISK_WEIGHT.get(risk, 0.25)
    score += risk_score
    reasons.append(f"risk:{risk}")

    lane_score = LANE_WEIGHT.get(lane, 0.05)
    score += lane_score
    if lane:
        reasons.append(f"lane:{lane}")

    action_score = ACTION_WEIGHT.get(action_name, 0.04)
    score += action_score
    if action_name:
        reasons.append(f"action:{action_name}")

    if action.get("requires_confirmation"):
        score += 0.08
        reasons.append("requires_confirmation")

    embedded_score = embedded_priority_score(action)
    if embedded_score:
        score += min(0.25, embedded_score * 0.25)
        reasons.append("has_source_priority")

    if action.get("tier") == "archive_candidate":
        score += 0.08
        reasons.append("archive_candidate")
    elif action.get("tier") == "cold":
        score += 0.04
        reasons.append("cold_memory")

    miss_count = numeric_value(action.get("miss_count"))
    if miss_count >= 2:
        score += min(0.12, miss_count * 0.03)
        reasons.append("repeated_signal")

    return round(min(score, 1.0), 3), reasons


def embedded_priority_score(action: dict[str, Any]) -> float:
    direct = numeric_value(action.get("priority_score"))
    if direct:
        return direct
    queue_item = action.get("queue_item")
    if isinstance(queue_item, dict):
        return numeric_value(queue_item.get("priority_score"))
    memory_tier = action.get("memory_tier")
    if isinstance(memory_tier, dict):
        return numeric_value(memory_tier.get("priority_score"))
    return 0.0


def numeric_value(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def count_by(actions: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in actions:
        value = str(action.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def compact_action(action: dict[str, Any], rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "review_key": review_key(action, rank),
        "action": action.get("action"),
        "governance_lane": action.get("governance_lane"),
        "type": action.get("type"),
        "id": action.get("id"),
        "risk": action.get("risk"),
        "requires_confirmation": bool(action.get("requires_confirmation")),
        "priority_score": action.get("priority_score"),
        "priority_reasons": action.get("priority_reasons") or [],
        "source_hint": source_hint(action),
        "reason": action.get("reason"),
    }


def review_key(action: dict[str, Any], rank: int) -> str:
    action_name = safe_key_part(action.get("action") or "action")
    action_type = safe_key_part(action.get("type") or action.get("governance_lane") or "target")
    action_id = action.get("id")
    if action_id is None:
        action_id = action.get("target_id")
    if action_id is None:
        memory_tier = action.get("memory_tier")
        if isinstance(memory_tier, dict):
            action_id = memory_tier.get("target_id")
    identifier = safe_key_part(action_id if action_id is not None else f"rank_{rank}")
    return f"{action_name}:{action_type}:{identifier}"


def source_hint(action: dict[str, Any]) -> str:
    parts = [
        str(action.get("governance_lane") or "unknown_lane"),
        str(action.get("action") or "unknown_action"),
    ]
    if action.get("type"):
        parts.append(f"type={action.get('type')}")
    if action.get("id") is not None:
        parts.append(f"id={action.get('id')}")
    if action.get("reason"):
        parts.append(str(action.get("reason")))
    return " | ".join(parts)


def safe_key_part(value: Any) -> str:
    text = str(value or "").strip().lower()
    safe = "".join(char if char.isalnum() else "_" for char in text)
    return "_".join(part for part in safe.split("_") if part) or "unknown"


def next_command_templates(limit: int) -> dict[str, str]:
    bounded_limit = max(1, int(limit or DEFAULT_TOP_LIMIT))
    return {
        "compact_same_limit": f"python tools/agent_memory.py maintain-plan --project . --compact --action-limit {bounded_limit} --json",
        "compact_smaller": "python tools/agent_memory.py maintain-plan --project . --compact --action-limit 1 --json",
        "full_plan": "python tools/agent_memory.py maintain-plan --project . --json",
    }
