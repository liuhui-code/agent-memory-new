# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


def assess_context_quality(
    requirements: dict[str, Any],
    expected: set[str],
    observation: dict[str, Any],
) -> dict[str, Any]:
    ordered = string_list(observation.get("ordered_anchor_paths"))
    observed = set(ordered)
    precision = len(expected & observed) / len(observed) if observed else 0.0
    first_rank = next(
        (index for index, file_path in enumerate(ordered, start=1) if file_path in expected),
        None,
    )
    required_spans = requirements["required_source_spans"]
    observed_spans = record_list(observation.get("excerpt_spans"))
    matched_spans = [span for span in required_spans if span_is_observed(span, observed_spans)]
    span_recall = len(matched_spans) / len(required_spans) if required_spans else None
    checks: dict[str, bool] = {}
    if requirements["required_top_k"]:
        checks["expected_anchors_within_top_k"] = expected <= set(
            ordered[: requirements["required_top_k"]]
        )
    if requirements["min_anchor_precision"] is not None:
        checks["minimum_anchor_precision_met"] = (
            precision >= requirements["min_anchor_precision"]
        )
    if required_spans:
        checks["minimum_source_span_recall_met"] = (
            span_recall is not None
            and span_recall >= requirements["min_source_span_recall"]
        )
    missing_gaps = sorted(
        set(requirements["required_evidence_gaps"])
        - set(string_list(observation.get("evidence_gaps")))
    )
    if requirements["required_evidence_gaps"]:
        checks["required_evidence_gaps_reported"] = not missing_gaps
    abstained = no_context_evidence(observation)
    if requirements["require_abstention"]:
        checks["abstention_observed"] = abstained
    return {
        "checks": checks,
        "first_expected_anchor_rank": first_rank,
        "expected_anchor_mrr": round(1 / first_rank, 4) if first_rank else 0.0,
        "source_span_recall": round(span_recall, 4) if span_recall is not None else None,
        "missing_required_source_spans": [
            span for span in required_spans if span not in matched_spans
        ],
        "missing_required_evidence_gaps": missing_gaps,
        "abstention_observed": abstained,
    }


def span_is_observed(required: dict[str, Any], observed: list[dict[str, Any]]) -> bool:
    for item in observed:
        if item.get("file_path") != required.get("file_path"):
            continue
        if required.get("symbol") and item.get("symbol") == required.get("symbol"):
            return True
        if line_ranges_overlap(required, item):
            return True
    return False


def line_ranges_overlap(first: dict[str, Any], second: dict[str, Any]) -> bool:
    values = (
        first.get("start_line"), first.get("end_line"),
        second.get("start_line"), second.get("end_line"),
    )
    if not all(isinstance(value, int) and value > 0 for value in values):
        return False
    return int(first["start_line"]) <= int(second["end_line"]) and (
        int(second["start_line"]) <= int(first["end_line"])
    )


def no_context_evidence(observation: dict[str, Any]) -> bool:
    count_fields = (
        "anchor_count", "log_anchor_count", "experience_ref_count",
        "semantic_ref_count", "path_candidate_count", "relation_hint_count",
    )
    return all(nonnegative_int(observation.get(field)) == 0 for field in count_fields)


def record_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
