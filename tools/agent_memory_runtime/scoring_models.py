# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


QUALITY_WEIGHTS = {
    "retrieval_relevance": 0.20,
    "evidence_strength": 0.25,
    "freshness": 0.20,
    "conflict_safety": 0.15,
    "reuse_success": 0.10,
    "governance_completeness": 0.10,
}


def clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


def score_band(score: float) -> str:
    if score >= 0.8:
        return "excellent"
    if score >= 0.65:
        return "good"
    if score >= 0.45:
        return "watch"
    return "poor"


def weighted_score(parts: dict[str, float], weights: dict[str, float]) -> float:
    return clamp_score(sum(clamp_score(parts.get(name, 0.0)) * weight for name, weight in weights.items()))


def value_present(row: dict[str, Any], key: str) -> bool:
    value = row.get(key)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip() not in {"[]", "{}"}
    return bool(value)


def boolish(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "active", "stale"}
    return bool(value)
