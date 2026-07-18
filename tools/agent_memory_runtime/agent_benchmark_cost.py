# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


TOKEN_OVERHEAD_RATIO_LIMIT = 0.10
ELAPSED_OVERHEAD_RATIO_LIMIT = 0.15
SOURCE_READ_AMPLIFICATION_LIMIT = 2.0
COST_METRIC_FIELDS = (
    "model_input_tokens",
    "model_cached_input_tokens",
    "model_uncached_input_tokens",
    "model_output_tokens",
    "model_reasoning_tokens",
    "command_count",
    "command_output_bytes",
    "source_read_count",
    "source_read_output_bytes",
    "tool_error_count",
    "source_search_miss_count",
    "source_search_error_count",
    "source_read_error_count",
    "other_tool_error_count",
)


def evaluate_efficiency(
    aggregates: dict[str, dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline = aggregates["baseline"]
    memory = aggregates["memory"]
    per_case = per_case_efficiency(observations)
    metrics = {
        "cost_attribution_coverage": attribution_coverage(observations),
        "token_overhead_ratio": overhead_ratio(
            baseline, memory, "average_token_estimate"
        ),
        "elapsed_overhead_ratio": overhead_ratio(
            baseline, memory, "average_elapsed_ms"
        ),
        "command_output_overhead_ratio": overhead_ratio(
            baseline, memory, "average_command_output_bytes"
        ),
        "source_read_output_overhead_ratio": overhead_ratio(
            baseline, memory, "average_source_read_output_bytes"
        ),
        "memory_cached_input_ratio": cached_input_ratio(memory),
        "baseline_source_read_amplification": source_read_amplification(baseline),
        "memory_source_read_amplification": source_read_amplification(memory),
        "per_case": per_case,
    }
    checks = {
        "cost_attribution_complete": metrics["cost_attribution_coverage"] == 1.0,
        "token_overhead_within_budget": ratio_within(
            metrics["token_overhead_ratio"], TOKEN_OVERHEAD_RATIO_LIMIT
        ),
        "elapsed_overhead_within_budget": ratio_within(
            metrics["elapsed_overhead_ratio"], ELAPSED_OVERHEAD_RATIO_LIMIT
        ),
        "source_search_non_regression": metric_non_regression(
            baseline, memory, "average_source_search_count"
        ),
        "source_read_amplification_within_budget": ratio_within(
            metrics["memory_source_read_amplification"],
            SOURCE_READ_AMPLIFICATION_LIMIT,
        ),
        "source_read_amplification_non_regression": metric_values_non_regression(
            metrics["baseline_source_read_amplification"],
            metrics["memory_source_read_amplification"],
        ),
        "every_case_token_overhead_within_budget": every_case_check(
            per_case, "token_overhead_within_budget"
        ),
        "every_case_elapsed_overhead_within_budget": every_case_check(
            per_case, "elapsed_overhead_within_budget"
        ),
        "every_case_source_search_non_regression": every_case_check(
            per_case, "source_search_non_regression"
        ),
        "every_case_source_read_amplification_within_budget": every_case_check(
            per_case, "source_read_amplification_within_budget"
        ),
        "every_case_source_read_amplification_non_regression": every_case_check(
            per_case, "source_read_amplification_non_regression"
        ),
    }
    return {
        "efficiency_gate": "pass" if all(checks.values()) else "fail",
        "efficiency_gate_checks": checks,
        "efficiency_metrics": metrics,
        "efficiency_limits": {
            "token_overhead_ratio": TOKEN_OVERHEAD_RATIO_LIMIT,
            "elapsed_overhead_ratio": ELAPSED_OVERHEAD_RATIO_LIMIT,
            "source_read_amplification": SOURCE_READ_AMPLIFICATION_LIMIT,
        },
    }


def attribution_coverage(observations: list[dict[str, Any]]) -> float:
    if not observations:
        return 0.0
    reported = sum(bool(item.get("cost_metrics_reported")) for item in observations)
    return round(reported / len(observations), 4)


def overhead_ratio(
    baseline: dict[str, Any],
    memory: dict[str, Any],
    key: str,
) -> float | None:
    baseline_value = baseline.get(key)
    memory_value = memory.get(key)
    if not isinstance(baseline_value, (int, float)) or baseline_value <= 0:
        return None
    if not isinstance(memory_value, (int, float)):
        return None
    return round((float(memory_value) - float(baseline_value)) / float(baseline_value), 4)


def cached_input_ratio(memory: dict[str, Any]) -> float | None:
    input_tokens = memory.get("average_model_input_tokens")
    cached_tokens = memory.get("average_model_cached_input_tokens")
    if not isinstance(input_tokens, (int, float)) or input_tokens <= 0:
        return None
    if not isinstance(cached_tokens, (int, float)):
        return None
    return round(float(cached_tokens) / float(input_tokens), 4)


def source_read_amplification(variant: dict[str, Any]) -> float | None:
    files = variant.get("average_source_file_count")
    reads = variant.get("average_source_read_count")
    if files == 0 and reads == 0:
        return 0.0
    if not isinstance(files, (int, float)) or files <= 0:
        return None
    if not isinstance(reads, (int, float)):
        return None
    return round(float(reads) / float(files), 4)


def ratio_within(value: Any, limit: float) -> bool:
    return isinstance(value, (int, float)) and float(value) <= limit


def metric_non_regression(
    baseline: dict[str, Any],
    memory: dict[str, Any],
    key: str,
) -> bool:
    baseline_value = baseline.get(key)
    memory_value = memory.get(key)
    return (
        isinstance(baseline_value, (int, float))
        and isinstance(memory_value, (int, float))
        and float(memory_value) <= float(baseline_value)
    )


def metric_values_non_regression(baseline_value: Any, memory_value: Any) -> bool:
    return (
        isinstance(baseline_value, (int, float))
        and isinstance(memory_value, (int, float))
        and float(memory_value) <= float(baseline_value)
    )


def per_case_efficiency(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    case_ids = sorted({str(item.get("case_id") or "") for item in observations})
    result = []
    for case_id in case_ids:
        variants = {
            variant: [
                item for item in observations
                if item.get("case_id") == case_id and item.get("variant") == variant
            ]
            for variant in ("baseline", "memory")
        }
        baseline = case_costs(variants["baseline"])
        memory = case_costs(variants["memory"])
        token_ratio = value_overhead_ratio(
            baseline["average_token_estimate"], memory["average_token_estimate"]
        )
        elapsed_ratio = value_overhead_ratio(
            baseline["average_elapsed_ms"], memory["average_elapsed_ms"]
        )
        baseline_amp = value_ratio(
            baseline["average_source_read_count"], baseline["average_source_file_count"]
        )
        memory_amp = value_ratio(
            memory["average_source_read_count"], memory["average_source_file_count"]
        )
        checks = {
            "token_overhead_within_budget": ratio_within(
                token_ratio, TOKEN_OVERHEAD_RATIO_LIMIT
            ),
            "elapsed_overhead_within_budget": ratio_within(
                elapsed_ratio, ELAPSED_OVERHEAD_RATIO_LIMIT
            ),
            "source_search_non_regression": metric_values_non_regression(
                baseline["average_source_search_count"],
                memory["average_source_search_count"],
            ),
            "source_read_amplification_within_budget": ratio_within(
                memory_amp, SOURCE_READ_AMPLIFICATION_LIMIT
            ),
            "source_read_amplification_non_regression": metric_values_non_regression(
                baseline_amp, memory_amp
            ),
        }
        result.append({
            "case_id": case_id,
            "token_overhead_ratio": token_ratio,
            "elapsed_overhead_ratio": elapsed_ratio,
            "baseline_source_read_amplification": baseline_amp,
            "memory_source_read_amplification": memory_amp,
            "checks": checks,
        })
    return result


def case_costs(observations: list[dict[str, Any]]) -> dict[str, float | None]:
    return {
        f"average_{field}": average_field(observations, field)
        for field in (
            "token_estimate",
            "elapsed_ms",
            "source_search_count",
            "source_read_count",
            "source_file_count",
        )
    }


def average_field(observations: list[dict[str, Any]], field: str) -> float | None:
    values = [item.get(field) for item in observations]
    if not values or not all(isinstance(item, (int, float)) for item in values):
        return None
    return sum(float(item) for item in values) / len(values)


def value_overhead_ratio(baseline: Any, memory: Any) -> float | None:
    if not isinstance(baseline, (int, float)) or baseline <= 0:
        return None
    if not isinstance(memory, (int, float)):
        return None
    return round((float(memory) - float(baseline)) / float(baseline), 4)


def value_ratio(numerator: Any, denominator: Any) -> float | None:
    if denominator == 0 and numerator == 0:
        return 0.0
    if not isinstance(denominator, (int, float)) or denominator <= 0:
        return None
    if not isinstance(numerator, (int, float)):
        return None
    return round(float(numerator) / float(denominator), 4)


def every_case_check(values: list[dict[str, Any]], key: str) -> bool:
    return bool(values) and all(bool(item["checks"].get(key)) for item in values)
