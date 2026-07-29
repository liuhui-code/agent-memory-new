# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


UTILITY_SCHEMA = "agent-evidence-utility/v1"
SUPPORTED_LEVELS = {"supported", "verified"}
UNCERTAINTY_STOPS = {"budget_exhausted_report_uncertainty", "no_new_evidence"}


def evaluate_agent_evidence_utility(
    cases: list[dict[str, Any]], observations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Report diagnostic evidence utility without making it a promotion gate."""
    by_case: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for item in observations:
        case_id = str(item.get("case_id") or "")
        variant = str(item.get("variant") or "")
        if case_id and variant in {"baseline", "memory"}:
            by_case.setdefault(case_id, {}).setdefault(variant, []).append(item)
    results = [case_utility(case, by_case.get(str(case.get("id") or ""), {})) for case in cases]
    return {
        "schema_version": UTILITY_SCHEMA,
        "status": "informational",
        "promotion_eligible": False,
        "case_count": len(results),
        "metrics": {variant: aggregate(results, variant) for variant in ("baseline", "memory")},
        "cases": results,
        "boundary": "offline_agent_evaluation_not_runtime_diagnosis",
    }


def case_utility(case: dict[str, Any], grouped: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    expected = string_set((case.get("oracle") or {}).get("expected_files"))
    return {
        "case_id": case.get("id"),
        "variants": {
            variant: aggregate_observations(grouped.get(variant, []), expected)
            for variant in ("baseline", "memory")
        },
    }


def aggregate_observations(values: list[dict[str, Any]], expected: set[str]) -> dict[str, Any]:
    measures = [observation_utility(item, expected) for item in values]
    return {
        "trial_count": len(measures),
        "expected_evidence_seen_rate": average(measures, "expected_evidence_seen"),
        "evidence_sufficiency_rate": average(measures, "evidence_sufficient"),
        "uncertainty_integrity_rate": average(measures, "uncertainty_integrity"),
        "anchor_guidance_rate": average(measures, "anchor_guided"),
        "average_source_search_count": average(measures, "source_search_count"),
        "average_non_anchor_file_count": average(measures, "non_anchor_file_count"),
    }


def observation_utility(value: dict[str, Any], expected: set[str]) -> dict[str, float]:
    investigated = string_set(value.get("investigated_files"))
    expected_seen = bool(expected & investigated)
    supported = str(value.get("causal_level") or "") in SUPPORTED_LEVELS
    stop = str(value.get("stop_reason") or "")
    uncertain = not expected_seen and stop in UNCERTAINTY_STOPS
    anchor_guided = bool(value.get("memory_anchor_hit_count")) and expected_seen
    return {
        "expected_evidence_seen": float(expected_seen),
        "evidence_sufficient": float(expected_seen and supported),
        "uncertainty_integrity": float(expected_seen or uncertain),
        "anchor_guided": float(anchor_guided),
        "source_search_count": float(value.get("source_search_count") or 0),
        "non_anchor_file_count": float(value.get("non_anchor_file_count") or 0),
    }


def aggregate(results: list[dict[str, Any]], variant: str) -> dict[str, float | None]:
    values = [item["variants"][variant] for item in results]
    return {
        key: average(values, key)
        for key in (
            "expected_evidence_seen_rate", "evidence_sufficiency_rate",
            "uncertainty_integrity_rate", "anchor_guidance_rate",
            "average_source_search_count", "average_non_anchor_file_count",
        )
    }


def average(values: list[dict[str, Any]], key: str) -> float | None:
    numbers = [float(item[key]) for item in values if isinstance(item.get(key), (int, float))]
    return round(sum(numbers) / len(numbers), 4) if numbers else None


def string_set(value: Any) -> set[str]:
    return {str(item) for item in value if str(item)} if isinstance(value, list) else set()
