# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .context_capability_quality import span_is_observed


def assess_hierarchical_localization(
    expected_files: set[str],
    requirements: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    required_callables = required_spans(
        requirements, "hierarchical_callable_spans", "required_source_spans"
    )
    required_owners = required_spans(
        requirements, "hierarchical_owner_spans", "required_owner_spans"
    )
    required_ranges = required_spans(
        requirements, "hierarchical_range_spans", "required_source_spans"
    )
    files = string_set(observation.get("hierarchical_file_paths"))
    callables = records(observation.get("hierarchical_callable_refs"))
    owners = records(observation.get("hierarchical_owner_refs"))
    ranges = records(observation.get("hierarchical_source_ranges"))
    callable_recall, missing_callables = span_recall(required_callables, callables)
    owner_recall, missing_owners = span_recall(required_owners, owners)
    range_recall, missing_ranges = span_recall(required_ranges, ranges)
    owner_precision = span_precision(required_owners, owners)
    return {
        "observed": bool(observation.get("hierarchical_schema_version")),
        "file_recall": recall(expected_files, files),
        "callable_recall": callable_recall,
        "owner_recall": owner_recall,
        "owner_precision": owner_precision,
        "range_recall": range_recall,
        "missing_callables": missing_callables,
        "missing_owners": missing_owners,
        "missing_ranges": missing_ranges,
        "file_candidate_count": len(files),
        "callable_candidate_count": len(callables),
        "owner_candidate_count": len(owners),
        "range_candidate_count": len(ranges),
        "audit_elapsed_ms": nonnegative_int(
            observation.get("hierarchical_audit_elapsed_ms")
        ),
    }


def required_spans(
    requirements: dict[str, Any],
    preferred_key: str,
    fallback_key: str,
) -> list[dict[str, Any]]:
    preferred = requirements.get(preferred_key)
    return records(preferred) if preferred else records(requirements.get(fallback_key))


def span_recall(
    required: list[dict[str, Any]],
    observed: list[dict[str, Any]],
) -> tuple[float | None, list[dict[str, Any]]]:
    if not required:
        return None, []
    matched = [item for item in required if span_is_observed(item, observed)]
    return round(len(matched) / len(required), 4), [
        item for item in required if item not in matched
    ]


def span_precision(
    expected: list[dict[str, Any]],
    observed: list[dict[str, Any]],
) -> float | None:
    if not expected:
        return None
    matched = sum(any(span_is_observed(item, observed) for item in expected) for item in observed)
    return round(matched / len(observed), 4) if observed else 0.0


def localization_profile(scored: list[dict[str, Any]]) -> dict[str, Any]:
    values = [item["hierarchical_localization"] for item in scored]
    observed = [item for item in values if item["observed"]]
    return {
        "status": "informational",
        "evaluated_cases": len(values),
        "observed_case_count": len(observed),
        "file_evaluated_case_count": measured_count(observed, "file_recall"),
        "callable_evaluated_case_count": measured_count(observed, "callable_recall"),
        "owner_evaluated_case_count": measured_count(observed, "owner_recall"),
        "range_evaluated_case_count": measured_count(observed, "range_recall"),
        "file_recall": average(observed, "file_recall"),
        "callable_recall": average(observed, "callable_recall"),
        "owner_recall": average(observed, "owner_recall"),
        "owner_precision": average(observed, "owner_precision"),
        "range_recall": average(observed, "range_recall"),
        "average_audit_elapsed_ms": average(observed, "audit_elapsed_ms"),
    }


def measured_count(values: list[dict[str, Any]], key: str) -> int:
    return sum(item.get(key) is not None for item in values)


def recall(expected: set[str], observed: set[str]) -> float | None:
    if not expected:
        return None
    return round(len(expected & observed) / len(expected), 4)


def string_set(value: Any) -> set[str]:
    return {
        str(item).strip()
        for item in value if str(item).strip()
    } if isinstance(value, list) else set()


def records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def average(values: list[dict[str, Any]], key: str) -> float | None:
    numbers = [float(item[key]) for item in values if item.get(key) is not None]
    return round(sum(numbers) / len(numbers), 4) if numbers else None


def nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
