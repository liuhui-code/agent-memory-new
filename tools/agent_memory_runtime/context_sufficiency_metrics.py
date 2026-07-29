# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


def sufficiency_profile(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Report readiness states without changing any retrieval quality gate."""
    values = [
        item.get("sufficiency") for item in observations
        if isinstance(item.get("sufficiency"), dict)
    ]
    statuses = [str(item.get("status") or "unknown") for item in values]
    reasons = [
        str(reason) for item in values
        for reason in item.get("reason_codes", [])
        if str(reason).strip()
    ]
    kinds = [str(item.get("kind") or "unknown") for item in values]
    return {
        "status": "informational",
        "evaluated_case_count": len(values),
        "missing_observation_count": len(observations) - len(values),
        "kind_counts": counts(kinds),
        "readiness_status_counts": counts(statuses),
        "reason_code_counts": counts(reasons),
        "scope": "shadow_observation_not_a_context_gate",
    }


def counts(values: list[str]) -> dict[str, int]:
    return {value: values.count(value) for value in sorted(set(values))}
