# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .scoring_models import QUALITY_WEIGHTS, boolish, clamp_score, score_band, value_present, weighted_score
from .text import json_list


HIGH_VALUE_THRESHOLD = 0.75
LOW_QUALITY_THRESHOLD = 0.45


def confidence_value(row: dict[str, Any], default: float = 0.8) -> float:
    try:
        return clamp_score(float(row.get("confidence") if row.get("confidence") is not None else default))
    except (TypeError, ValueError):
        return default


def misleading_value(row: dict[str, Any]) -> float:
    try:
        return clamp_score(float(row.get("misleading_score") or 0.0))
    except (TypeError, ValueError):
        return 0.0


def recommended_action(score: float, row: dict[str, Any]) -> str:
    status = str(row.get("status") or "active")
    if score < LOW_QUALITY_THRESHOLD or status == "stale" or boolish(row.get("is_stale")):
        return "review_or_stale"
    if score >= HIGH_VALUE_THRESHOLD:
        return "keep_active"
    return "watch"


def score_reflection_quality(row: dict[str, Any]) -> dict[str, Any]:
    source_cases = json_list(row.get("source_cases"))
    has_evidence = any(value_present(row, key) for key in ("evidence", "verification_method", "source_cases"))
    has_procedure_fields = all(value_present(row, key) for key in ("trigger_condition", "repair_action"))
    has_semantic_anchor = all(value_present(row, key) for key in ("anchor_type", "anchor_key", "semantic_field"))
    confidence = confidence_value(row)
    misleading = misleading_value(row)
    is_stale = boolish(row.get("is_stale")) or str(row.get("status") or "active") == "stale"
    reuse_text = " ".join(json_list(row.get("reuse_feedback")) or [str(row.get("reuse_feedback") or "")]).lower()
    reuse_success = 0.85 if any(term in reuse_text for term in ("success", "helped", "reused", "pass")) else 0.45
    if not value_present(row, "reuse_feedback"):
        reuse_success = 0.35

    parts = {
        "retrieval_relevance": 0.85 if value_present(row, "experience_type") else 0.55,
        "evidence_strength": min(1.0, 0.35 + (0.3 if has_evidence else 0) + (0.2 if source_cases else 0) + (0.2 if has_semantic_anchor else 0)),
        "freshness": 0.2 if is_stale else confidence,
        "conflict_safety": clamp_score(1.0 - misleading - (0.25 if value_present(row, "superseded_by") else 0.0)),
        "reuse_success": reuse_success,
        "governance_completeness": min(1.0, 0.35 + (0.25 if has_procedure_fields else 0) + (0.2 if value_present(row, "scope") else 0) + (0.2 if value_present(row, "lesson") else 0)),
    }
    score = weighted_score(parts, QUALITY_WEIGHTS)
    reasons = reflection_reasons(row, parts, source_cases, has_procedure_fields, has_semantic_anchor)
    return quality_payload("reflection", row, score, parts, reasons)


def reflection_reasons(
    row: dict[str, Any],
    parts: dict[str, float],
    source_cases: list[str],
    has_procedure_fields: bool,
    has_semantic_anchor: bool,
) -> list[str]:
    reasons: list[str] = []
    if value_present(row, "verification_method"):
        reasons.append("has verification_method")
    if source_cases:
        reasons.append("has source_cases")
    if has_procedure_fields:
        reasons.append("has trigger_condition and repair_action")
    if has_semantic_anchor:
        reasons.append("has semantic anchor")
    if parts["conflict_safety"] < 0.6:
        reasons.append("conflict or misleading risk")
    if parts["freshness"] < 0.5:
        reasons.append("stale or low confidence")
    return reasons or ["minimal quality evidence"]


def score_semantic_quality(row: dict[str, Any]) -> dict[str, Any]:
    is_stale = boolish(row.get("is_stale")) or str(row.get("status") or "active") == "stale"
    confidence = confidence_value(row)
    source = str(row.get("source") or "").strip().lower()
    grounded_source = bool(source and source not in {"manual", "unknown"})
    parts = {
        "retrieval_relevance": 0.75 if value_present(row, "category") or value_present(row, "scope") else 0.55,
        "evidence_strength": min(1.0, 0.25 + (0.25 if grounded_source else 0) + (0.3 if value_present(row, "evidence") else 0)),
        "freshness": 0.2 if is_stale else confidence,
        "conflict_safety": 0.85,
        "reuse_success": 0.5,
        "governance_completeness": min(1.0, 0.4 + (0.25 if value_present(row, "scope") else 0) + (0.2 if value_present(row, "fact") else 0)),
    }
    score = weighted_score(parts, QUALITY_WEIGHTS)
    reasons = ["has grounded source"] if grounded_source else ["missing grounded source"]
    if value_present(row, "evidence"):
        reasons.append("has evidence")
    return quality_payload("semantic", row, score, parts, reasons)


def score_incident_trace_quality(row: dict[str, Any]) -> dict[str, Any]:
    linked_targets = json_list(row.get("linked_targets"))
    candidate_chain = json_list(row.get("candidate_chain"))
    resolved = str(row.get("status") or "") == "resolved"
    confidence = confidence_value(row, 0.7)
    parts = {
        "retrieval_relevance": 0.8 if value_present(row, "arkts_scene") else 0.55,
        "evidence_strength": min(1.0, 0.35 + (0.25 if linked_targets else 0) + (0.2 if candidate_chain else 0) + (0.15 if value_present(row, "dominant_log_events") else 0)),
        "freshness": confidence,
        "conflict_safety": 0.85,
        "reuse_success": 0.85 if resolved else 0.45,
        "governance_completeness": min(1.0, 0.4 + (0.2 if value_present(row, "symptom") else 0) + (0.2 if value_present(row, "resolution") else 0)),
    }
    score = weighted_score(parts, QUALITY_WEIGHTS)
    reasons = ["has compact incident trace"]
    if linked_targets:
        reasons.append("has linked code/log anchors")
    if resolved:
        reasons.append("resolved incident")
    return quality_payload("incident_trace", row, score, parts, reasons)


def quality_payload(
    record_type: str,
    row: dict[str, Any],
    score: float,
    parts: dict[str, float],
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "record_type": record_type,
        "record_id": row.get("id"),
        "quality_score": score,
        "quality_band": score_band(score),
        "score_parts": {key: clamp_score(value) for key, value in parts.items()},
        "reasons": reasons,
        "recommended_action": recommended_action(score, row),
        "experience_type": row.get("experience_type"),
        "confidence": row.get("confidence"),
        "status": row.get("status") or "active",
    }


def build_quality_report(
    semantic_rows: list[dict[str, Any]],
    reflection_rows: list[dict[str, Any]],
    incident_trace_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    scored = [
        *(score_semantic_quality(row) for row in semantic_rows),
        *(score_reflection_quality(row) for row in reflection_rows),
        *(score_incident_trace_quality(row) for row in incident_trace_rows),
    ]
    low_quality = [item for item in scored if item["quality_score"] < LOW_QUALITY_THRESHOLD]
    high_value = [item for item in scored if item["quality_score"] >= HIGH_VALUE_THRESHOLD]
    high_value.sort(key=lambda item: (item["quality_score"], int(item["record_id"] or 0)), reverse=True)
    low_quality.sort(key=lambda item: (item["quality_score"], int(item["record_id"] or 0)))
    return {
        "summary": {
            "scored_records": len(scored),
            "low_quality_records": len(low_quality),
            "high_value_records": len(high_value),
            "average_quality_score": average_quality(scored),
        },
        "low_quality_records": low_quality[:10],
        "high_value_records": high_value[:10],
    }


def average_quality(scored: list[dict[str, Any]]) -> float:
    if not scored:
        return 0.0
    return clamp_score(sum(float(item["quality_score"]) for item in scored) / len(scored))
