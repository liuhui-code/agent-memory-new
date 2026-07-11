# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .text import unique_list


INACTIVE_STATUSES = {"stale", "archived", "merged", "rejected"}


def explain_experience_trust(row: dict[str, Any]) -> dict[str, Any]:
    flags: list[str] = []
    reasons: list[str] = []
    caps: list[float] = []

    status = str(row.get("status") or "")
    maturity = str(row.get("experience_maturity") or "")
    experience_type = str(row.get("experience_type") or "")

    if status in INACTIVE_STATUSES or truthy(row.get("is_stale")):
        flags.append("inactive_or_stale_experience")
        reasons.append("trust capped by stale or inactive status")
        caps.append(0.35)
    if str(row.get("last_outcome") or "") == "misleading" or safe_float(row.get("misleading_score")) >= 0.5:
        flags.append("misleading_experience")
        reasons.append("trust capped by misleading experience feedback")
        caps.append(0.25)
    if maturity == "deprecated_pattern":
        flags.append("deprecated_experience")
        reasons.append("trust capped by deprecated maturity")
        caps.append(0.25)
    elif maturity == "raw_observation":
        flags.append("raw_observation_experience")
        reasons.append("trust capped by raw observation maturity")
        caps.append(0.55)

    counter_evidence = row.get("counter_evidence") if isinstance(row.get("counter_evidence"), dict) else {}
    if experience_type == "procedure_experience" and maturity in {"verified_case", "reused_pattern", "skill_candidate"}:
        if not counter_evidence.get("has_counter_evidence"):
            flags.append("missing_counter_evidence")
            if has_positive_calibration(row):
                reasons.append("missing counter-evidence remains a risk despite positive calibration feedback")
            else:
                reasons.append("trust capped until procedure experience has negative applicability boundaries")
                caps.append(0.70)

    if experience_type in {"correction_experience", "semantic_patch_experience"}:
        flags.append("semantic_correction_guidance")
        reasons.append("use as semantic correction guidance, not a reusable procedure rule")

    return {
        "query_risk_flags": unique_list(flags),
        "trust_cap": min(caps) if caps else None,
        "trust_cap_reasons": unique_list(reasons),
    }


def truthy(value: Any) -> bool:
    return value in {1, True, "1", "true", "True"}


def safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def has_positive_calibration(row: dict[str, Any]) -> bool:
    if safe_float(row.get("calibration_feedback_bonus")) > 0:
        return True
    reasons = row.get("calibration_feedback_reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    return any(str(reason) in {"verified_useful", "useful", "undertrusted"} for reason in reasons)
