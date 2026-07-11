# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .text import json_list, unique_list


COUNTER_EVIDENCE_FIELDS = [
    "negative_preconditions",
    "does_not_apply_to",
    "what_failed",
    "anti_pattern",
    "misleading_followup_terms",
]


def score_experience_maturity(row: dict[str, Any]) -> dict[str, Any]:
    counter_evidence = build_counter_evidence_summary(row)
    if is_deprecated(row):
        return maturity_payload(
            "deprecated_pattern",
            0.18,
            deprecated_reasons(row),
            counter_evidence,
            "deprecate_or_rewrite",
        )

    score = 0.15
    reasons: list[str] = []

    if row.get("experience_type"):
        score += 0.04
        reasons.append("has experience_type")
    if row.get("scope"):
        score += 0.06
        reasons.append("has scope")
    if row.get("trigger_condition"):
        score += 0.12
        reasons.append("has trigger_condition")
    if row.get("repair_action"):
        score += 0.12
        reasons.append("has repair_action")
    if row.get("verification_method"):
        score += 0.18
        reasons.append("has verification_method")
    if json_list(row.get("source_cases")):
        score += 0.16
        reasons.append("has source_cases")
    if row.get("evidence"):
        score += 0.10
        reasons.append("has evidence")
    if row.get("final_verification_path"):
        score += 0.08
        reasons.append("has final_verification_path")
    if counter_evidence["has_counter_evidence"]:
        score += 0.08
        reasons.append("has counter_evidence")

    positive_reuse = has_positive_reuse(row)
    if positive_reuse:
        score += 0.18
        reasons.append("positive reuse signal")
    if has_positive_calibration(row):
        score += 0.08
        reasons.append("positive calibration signal")

    level = maturity_level(row, score, positive_reuse)
    action = recommended_action(level, counter_evidence)
    return maturity_payload(level, score, reasons, counter_evidence, action)


def build_counter_evidence_summary(row: dict[str, Any]) -> dict[str, Any]:
    fields = [
        field
        for field in COUNTER_EVIDENCE_FIELDS
        if has_field_value(row.get(field))
    ]
    return {
        "has_counter_evidence": bool(fields),
        "fields": fields,
        "missing_fields": [field for field in COUNTER_EVIDENCE_FIELDS if field not in fields],
    }


def maturity_level(row: dict[str, Any], score: float, positive_reuse: bool) -> str:
    if row.get("skill_candidate") and positive_reuse and has_verification_anchor(row):
        return "skill_candidate"
    if positive_reuse and has_verification_anchor(row):
        return "reused_pattern"
    if has_verification_anchor(row):
        return "verified_case"
    if row.get("trigger_condition") and row.get("repair_action"):
        return "structured_candidate"
    if score >= 0.55:
        return "structured_candidate"
    return "raw_observation"


def has_verification_anchor(row: dict[str, Any]) -> bool:
    return bool(
        row.get("verification_method")
        and (
            json_list(row.get("source_cases"))
            or row.get("evidence")
            or row.get("final_verification_path")
            or row.get("anchor_key")
        )
    )


def has_positive_reuse(row: dict[str, Any]) -> bool:
    if int_value(row.get("applied_count")) > 0 and str(row.get("last_outcome") or "") != "misleading":
        return True
    feedback = str(row.get("reuse_feedback") or "").lower()
    return any(token in feedback for token in ("reused successfully", "helped", "useful"))


def has_positive_calibration(row: dict[str, Any]) -> bool:
    reasons = [str(reason) for reason in json_list(row.get("calibration_feedback_reasons"))]
    return any(reason in {"useful", "verified_useful", "undertrusted"} for reason in reasons)


def is_deprecated(row: dict[str, Any]) -> bool:
    if row.get("status") in {"stale", "archived", "merged", "rejected"}:
        return True
    if truthy(row.get("is_stale")):
        return True
    if row.get("superseded_by"):
        return True
    if row.get("last_outcome") == "misleading":
        return True
    if float_value(row.get("misleading_score")) >= 0.5:
        return True
    reasons = [str(reason) for reason in json_list(row.get("calibration_feedback_reasons"))]
    return "overtrusted" in reasons


def deprecated_reasons(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if row.get("status") in {"stale", "archived", "merged", "rejected"} or truthy(row.get("is_stale")):
        reasons.append("stale or inactive status")
    if row.get("superseded_by"):
        reasons.append("superseded by another memory")
    if row.get("last_outcome") == "misleading" or float_value(row.get("misleading_score")) >= 0.5:
        reasons.append("misleading outcome")
    if "overtrusted" in [str(reason) for reason in json_list(row.get("calibration_feedback_reasons"))]:
        reasons.append("overtrusted calibration feedback")
    return reasons or ["deprecated signal present"]


def recommended_action(level: str, counter_evidence: dict[str, Any]) -> str:
    if level == "deprecated_pattern":
        return "deprecate_or_rewrite"
    if level == "raw_observation":
        return "add_structure"
    if level in {"structured_candidate", "verified_case"} and not counter_evidence["has_counter_evidence"]:
        return "add_counter_evidence"
    if level == "skill_candidate":
        return "review_for_skill_evolution"
    return "keep_active"


def maturity_payload(
    level: str,
    score: float,
    reasons: list[str],
    counter_evidence: dict[str, Any],
    action: str,
) -> dict[str, Any]:
    return {
        "experience_maturity": level,
        "experience_maturity_score": round(max(0.0, min(1.0, score)), 3),
        "maturity_reasons": unique_list(reasons),
        "counter_evidence": counter_evidence,
        "recommended_maturity_action": action,
    }


def has_field_value(value: Any) -> bool:
    if json_list(value):
        return True
    text = str(value or "").strip()
    return bool(text and text not in {"[]", "{}"})


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def float_value(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def truthy(value: Any) -> bool:
    return value in {1, True, "1", "true", "True"}
