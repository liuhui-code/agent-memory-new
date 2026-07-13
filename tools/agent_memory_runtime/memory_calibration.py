# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .experience_query_quality import explain_experience_trust
from .quality_scoring import experience_evidence_profile
from .text import json_list, unique_list


CALIBRATED_GROUPS = {
    "semantic_facts",
    "reflections",
    "episodes",
    "wiki_matches",
    "code_log_matches",
    "edge_matches",
    "incident_trace_matches",
    "correction_guards",
}


def memory_use_policy() -> dict[str, Any]:
    return {
        "mode": "advisory",
        "authority_order": [
            "current_source",
            "explicit_user_instruction",
            "source_truth",
            "verified_experience",
            "usable_hint",
            "weak_hint",
        ],
        "rules": [
            "Current source files and explicit user instructions override stored memory.",
            "Use conflict warnings and correction guards as inspection guardrails, not conclusions.",
            "Use weak hints only to choose what to inspect next.",
            "Do not let recency override evidence, status, confidence, or feedback penalties.",
        ],
    }


def calibrate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload["memory_use_policy"] = memory_use_policy()
    for group in CALIBRATED_GROUPS:
        if group in payload:
            payload[group] = calibrate_result_group(group, payload.get(group) or [])
    return payload


def calibrate_result_group(group: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [calibrate_record(group, row) for row in rows]


def calibrate_record(group: str, row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    if group in {"reflections", "correction_guards"} and not isinstance(item.get("experience_evidence_profile"), dict):
        item["experience_evidence_profile"] = experience_evidence_profile(item)
    trust_score, reasons = compute_trust_score(group, item)
    query_quality = explain_experience_trust(item) if group in {"reflections", "correction_guards"} else {}
    trust_cap = query_quality.get("trust_cap")
    if group in {"reflections", "correction_guards"}:
        source_case_quality = source_case_quality_profile(item)
        item["source_case_quality"] = source_case_quality
        source_case_cap = source_case_trust_cap(source_case_quality)
        if source_case_cap is not None and (trust_cap is None or source_case_cap < trust_cap):
            trust_cap = source_case_cap
            query_quality["trust_cap_reasons"] = unique_list(
                list(query_quality.get("trust_cap_reasons", [])) + ["source_cases are old, manual, unknown, or non-source-like"]
            )
        if source_case_quality["weak_source_cases"]:
            reasons.append("weak source_cases")
        if source_case_quality["source_like_cases"]:
            reasons.append("source-like source_cases")
    if trust_cap is not None and trust_score > trust_cap:
        trust_score = trust_cap
    reasons = unique_list(reasons + query_quality.get("trust_cap_reasons", []))
    item["query_risk_flags"] = query_quality.get("query_risk_flags", [])
    item["trust_cap"] = trust_cap
    item["trust_cap_reasons"] = query_quality.get("trust_cap_reasons", [])
    item["trust_score"] = round(max(0.0, min(1.0, trust_score)), 3)
    item["trust_level"] = trust_level_for(group, item, item["trust_score"])
    item["trust_reasons"] = reasons
    item["retrieval_explanation"] = build_retrieval_explanation(group, item)
    return item


def compute_trust_score(group: str, item: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.45
    reasons: list[str] = []
    confidence = safe_float(item.get("confidence"), 0.65)
    quality_score = safe_float(item.get("quality_score"), None)
    feedback_penalty = safe_float(item.get("feedback_penalty"), 0.0)
    calibration_bonus = safe_float(item.get("calibration_feedback_bonus"), 0.0)
    calibration_penalty = safe_float(item.get("calibration_feedback_penalty"), 0.0)
    maturity = str(item.get("experience_maturity") or "")

    score += (confidence - 0.5) * 0.35
    reasons.append(f"confidence={round(confidence, 3)}")
    if quality_score is not None:
        score += (quality_score - 0.5) * 0.35
        reasons.append(f"quality_score={round(quality_score, 3)}")
    if has_explicit_evidence(item):
        score += 0.16
        reasons.append("has explicit evidence")
    if item.get("verification_method"):
        score += 0.14
        reasons.append("verified by verification_method")
    source_case_quality = source_case_quality_profile(item)
    if source_case_quality["source_like_cases"]:
        score += 0.10
        reasons.append("has source-like source_cases")
    elif source_case_quality["weak_source_cases"]:
        score += 0.03
        reasons.append("has weak source_cases")
    if group in {"wiki_matches", "code_log_matches", "edge_matches", "incident_trace_matches"}:
        score += 0.12
        reasons.append("source-like code/log evidence")
    if maturity in {"verified_case", "reused_pattern", "skill_candidate"}:
        score += {"verified_case": 0.08, "reused_pattern": 0.12, "skill_candidate": 0.16}[maturity]
        reasons.append(f"experience_maturity={maturity}")
    elif maturity == "raw_observation":
        score -= 0.10
        reasons.append("experience_maturity=raw_observation")
    elif maturity == "deprecated_pattern":
        score -= 0.30
        reasons.append("experience_maturity=deprecated_pattern")
    if group == "reflections" and maturity in {"verified_case", "reused_pattern", "skill_candidate"}:
        counter_evidence = item.get("counter_evidence") if isinstance(item.get("counter_evidence"), dict) else {}
        if not counter_evidence.get("has_counter_evidence"):
            score -= 0.06
            reasons.append("missing counter_evidence")
    if item.get("status") in {"stale", "archived", "merged", "rejected"} or truthy(item.get("is_stale")):
        score -= 0.35
        reasons.append("stale or inactive status")
    if feedback_penalty:
        score -= min(0.35, feedback_penalty / 100.0)
        reasons.append("feedback penalty applied")
    if calibration_bonus:
        score += min(0.3, calibration_bonus)
        reasons.append("calibration feedback bonus applied")
    if calibration_penalty:
        score -= min(0.3, calibration_penalty)
        reasons.append("calibration feedback penalty applied")
    if safe_float(item.get("misleading_score"), 0.0) > 0:
        score -= min(0.25, safe_float(item.get("misleading_score"), 0.0) * 0.25)
        reasons.append("misleading signal present")
    if item.get("memory_lane") == "correction_guard" or group == "correction_guards":
        reasons.append("correction guardrail lane")
    if item.get("warning"):
        score -= 0.10
        reasons.append("record warning present")
    return score, unique_list(reasons)


def trust_level_for(group: str, item: dict[str, Any], score: float) -> str:
    if item.get("status") in {"stale", "archived", "merged", "rejected"} or truthy(item.get("is_stale")):
        return "possibly_stale"
    if item.get("memory_lane") == "correction_guard" or group == "correction_guards":
        return "conflict_warning"
    if item.get("experience_type") in {"correction_experience", "semantic_patch_experience"}:
        return "conflict_warning"
    if safe_float(item.get("misleading_score"), 0.0) >= 0.5:
        return "conflict_warning"
    if group in {"wiki_matches", "code_log_matches", "edge_matches", "incident_trace_matches"} and score >= 0.62:
        return "source_truth"
    if group == "semantic_facts" and has_explicit_evidence(item) and score >= 0.72:
        return "source_truth"
    if group == "reflections" and score >= 0.75 and item.get("verification_method"):
        return "verified_experience"
    if score < 0.45:
        return "weak_hint"
    return "usable_hint"


def build_retrieval_explanation(group: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": group,
        "score": item.get("score"),
        "rerank_score": item.get("rerank_score"),
        "match_reasons": json_list(item.get("match_reasons")),
        "gate_score": item.get("gate_score"),
        "gate_reasons": json_list(item.get("gate_reasons")),
        "quality_score": item.get("quality_score"),
        "quality_band": item.get("quality_band"),
        "experience_maturity": item.get("experience_maturity"),
        "experience_maturity_score": item.get("experience_maturity_score"),
        "feedback_penalty": item.get("feedback_penalty", 0.0),
        "feedback_reasons": json_list(item.get("feedback_reasons")),
        "calibration_feedback_bonus": item.get("calibration_feedback_bonus", 0.0),
        "calibration_feedback_penalty": item.get("calibration_feedback_penalty", 0.0),
        "calibration_feedback_reasons": json_list(item.get("calibration_feedback_reasons")),
        "query_risk_flags": json_list(item.get("query_risk_flags")),
        "intent_alignment": item.get("intent_alignment"),
        "interference_penalty": item.get("interference_penalty", 0.0),
        "interference_reasons": json_list(item.get("interference_reasons")),
        "trust_cap": item.get("trust_cap"),
        "trust_cap_reasons": json_list(item.get("trust_cap_reasons")),
        "status": item.get("status"),
        "confidence": item.get("confidence"),
        "experience_evidence_profile": item.get("experience_evidence_profile"),
        "source_case_quality": item.get("source_case_quality"),
    }


def has_explicit_evidence(item: dict[str, Any]) -> bool:
    if str(item.get("evidence") or "").strip():
        return True
    if json_list(item.get("source_cases")):
        return True
    source = str(item.get("source") or "").strip().lower()
    return source not in {"", "manual", "unknown"}


def source_case_quality_profile(item: dict[str, Any]) -> dict[str, Any]:
    cases = [str(case).strip() for case in json_list(item.get("source_cases")) if str(case).strip()]
    source_like_prefixes = (
        "file:",
        "code:",
        "symbol:",
        "log:",
        "code_log:",
        "incident_trace:",
        "runtime_log:",
        "test:",
        "commit:",
        "pr:",
    )
    weak_prefixes = ("old_case:", "manual:", "memory:", "note:", "unknown", "one_off:", "legacy:")
    source_like = [case for case in cases if case.lower().startswith(source_like_prefixes)]
    weak = [case for case in cases if case.lower().startswith(weak_prefixes)]
    non_source_like = [case for case in cases if case not in source_like and case not in weak]
    return {
        "source_case_count": len(cases),
        "source_like_cases": source_like,
        "weak_source_cases": [*weak, *non_source_like],
        "has_source_like_case": bool(source_like),
        "all_cases_weak": bool(cases) and not source_like,
    }


def source_case_trust_cap(profile: dict[str, Any]) -> float | None:
    if not profile.get("source_case_count"):
        return None
    if profile.get("all_cases_weak"):
        return 0.68
    return None


def truthy(value: Any) -> bool:
    return value in {1, True, "1", "true", "True"}


def safe_float(value: Any, default: float | None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
