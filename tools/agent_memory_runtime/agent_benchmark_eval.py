# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


CATEGORY_ALIASES = {
    "route": ("route", "router", "navigation", "navigate", "路由", "跳转"),
    "resource": ("resource", "asset", "image", "资源", "图片"),
    "state": ("state", "session", "cache", "状态", "会话", "缓存"),
    "async": ("async", "await", "race", "ordering", "异步", "竞态", "时序"),
    "api": ("api", "interface", "endpoint", "接口"),
}
CAUSAL_LEVELS = {"association": 0, "supported": 1, "verified": 2}


def evaluate_agent_benchmark(
    pack: dict[str, Any],
    cases: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    duplicates: list[str] = []
    for item in observations:
        key = (item["case_id"], item["variant"])
        if key in by_key:
            duplicates.append(":".join(key))
        by_key[key] = item
    results: list[dict[str, Any]] = []
    missing: list[str] = []
    for case in cases:
        variant_scores: dict[str, dict[str, Any]] = {}
        for variant in ("baseline", "memory"):
            observation = by_key.get((case["id"], variant))
            if not observation:
                missing.append(f"{case['id']}:{variant}")
                continue
            variant_scores[variant] = score_observation(case, observation)
        results.append({
            "case_id": case["id"],
            "task_type": case["task_type"],
            "review_status": case["review_status"],
            "variants": variant_scores,
            "context_outcome_delta": score_delta(variant_scores, "agent_outcome_score"),
        })
    aggregates = {
        variant: aggregate_variant(results, variant)
        for variant in ("baseline", "memory")
    }
    deltas = aggregate_deltas(aggregates)
    minimum = 10 if pack.get("suite") == "holdout" else 1
    checks = {
        "minimum_cases": len(cases) >= minimum,
        "complete_pairs": not missing and not duplicates,
        "context_agent_outcome_non_regression": compare_metric(aggregates, "agent_outcome_score", higher=True),
        "context_agent_root_cause_non_regression": compare_metric(aggregates, "agent_root_cause_accuracy", higher=True),
        "context_forbidden_direction_non_regression": compare_metric(
            aggregates, "forbidden_direction_rate", higher=False
        ),
    }
    gate = "pass" if all(checks.values()) else "fail"
    return {
        "schema_version": "agent-benchmark-result/v1",
        "status": gate,
        "quality_gate": gate,
        "summary": {
            "case_count": len(cases),
            "observation_count": len(observations),
            "missing_observations": missing,
            "duplicate_observations": duplicates,
            "suite": pack.get("suite") or "development",
        },
        "metrics": aggregates,
        "context_uplift": deltas,
        "gate_checks": checks,
        "minimum_case_count": minimum,
        "cases": results,
        "audit": {
            "llm_judge_used": False,
            "oracle_hidden_during_run": True,
            "reasoning_persisted": False,
        },
    }


def score_observation(case: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    oracle = case["oracle"]
    expected = set(oracle["expected_files"])
    predicted = set(observation["predicted_files"])
    forbidden = set(oracle.get("forbidden_files") or [])
    overlap = expected & predicted
    recall = len(overlap) / len(expected) if expected else 0.0
    precision = len(overlap) / len(predicted) if predicted else 0.0
    predicted_category = canonical_category(observation["root_cause_category"])
    expected_category = canonical_category(str(oracle.get("root_cause_category") or ""))
    category_match = predicted_category == expected_category
    forbidden_hits = predicted & forbidden
    expected_level = str(oracle.get("expected_causal_level") or "")
    causal_match = causal_level_satisfies(observation["causal_level"], expected_level)
    quality = (
        0.4 * float(category_match)
        + 0.35 * recall
        + 0.15 * precision
        + 0.1 * float(causal_match)
        - 0.25 * float(bool(forbidden_hits))
    )
    return {
        "agent_outcome_score": round(max(0.0, min(1.0, quality)), 4),
        "agent_root_cause_match": category_match,
        "predicted_root_cause_category": predicted_category,
        "expected_root_cause_category": expected_category,
        "expected_file_recall": round(recall, 4),
        "predicted_file_precision": round(precision, 4),
        "forbidden_direction_hit": bool(forbidden_hits),
        "forbidden_files": sorted(forbidden_hits),
        "causal_level_match": causal_match,
        "verification_status": observation["verification_status"],
        "query_rounds": observation["query_rounds"],
        "token_estimate": observation["token_estimate"],
        "elapsed_ms": observation["elapsed_ms"],
        "predicted_files": observation["predicted_files"][:20],
    }


def canonical_category(value: str) -> str:
    lowered = str(value or "").casefold().strip()
    for category, aliases in CATEGORY_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return category
    return lowered.replace(" ", "_")


def causal_level_satisfies(observed: str, expected: str) -> bool:
    if not expected:
        return True
    observed_level = str(observed or "").casefold()
    expected_level = str(expected or "").casefold()
    if observed_level == "rejected" or expected_level == "rejected":
        return observed_level == expected_level
    if observed_level not in CAUSAL_LEVELS or expected_level not in CAUSAL_LEVELS:
        return observed_level == expected_level
    return CAUSAL_LEVELS[observed_level] >= CAUSAL_LEVELS[expected_level]


def aggregate_variant(results: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    values = [item["variants"][variant] for item in results if variant in item["variants"]]
    return {
        "sample_count": len(values),
        "agent_outcome_score": average(values, "agent_outcome_score"),
        "agent_root_cause_accuracy": boolean_rate(values, "agent_root_cause_match"),
        "expected_file_recall": average(values, "expected_file_recall"),
        "predicted_file_precision": average(values, "predicted_file_precision"),
        "forbidden_direction_rate": boolean_rate(values, "forbidden_direction_hit"),
        "causal_calibration_accuracy": boolean_rate(values, "causal_level_match"),
        "verification_pass_rate": value_rate(values, "verification_status", "pass"),
        "average_query_rounds": average(values, "query_rounds"),
        "average_token_estimate": average(values, "token_estimate"),
        "average_elapsed_ms": average(values, "elapsed_ms"),
    }


def aggregate_deltas(aggregates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    baseline = aggregates["baseline"]
    memory = aggregates["memory"]
    higher = (
        "agent_outcome_score", "agent_root_cause_accuracy", "expected_file_recall",
        "predicted_file_precision", "causal_calibration_accuracy", "verification_pass_rate",
    )
    result = {
        f"{key}_delta": rounded_difference(memory.get(key), baseline.get(key))
        for key in higher
    }
    result["forbidden_direction_rate_delta"] = rounded_difference(
        memory.get("forbidden_direction_rate"), baseline.get("forbidden_direction_rate")
    )
    result["token_savings"] = rounded_difference(
        baseline.get("average_token_estimate"), memory.get("average_token_estimate")
    )
    result["elapsed_ms_savings"] = rounded_difference(
        baseline.get("average_elapsed_ms"), memory.get("average_elapsed_ms")
    )
    return result


def compare_metric(aggregates: dict[str, dict[str, Any]], key: str, higher: bool) -> bool:
    baseline = aggregates["baseline"].get(key)
    memory = aggregates["memory"].get(key)
    if baseline is None or memory is None:
        return False
    return memory >= baseline if higher else memory <= baseline


def score_delta(values: dict[str, dict[str, Any]], key: str) -> float | None:
    if "baseline" not in values or "memory" not in values:
        return None
    return rounded_difference(values["memory"].get(key), values["baseline"].get(key))


def average(values: list[dict[str, Any]], key: str) -> float | None:
    numbers = [float(item[key]) for item in values if isinstance(item.get(key), (int, float))]
    return round(sum(numbers) / len(numbers), 4) if numbers else None


def boolean_rate(values: list[dict[str, Any]], key: str) -> float | None:
    selected = [bool(item[key]) for item in values if key in item]
    return round(sum(selected) / len(selected), 4) if selected else None


def value_rate(values: list[dict[str, Any]], key: str, expected: str) -> float | None:
    selected = [item[key] for item in values if item.get(key) not in {None, "unknown"}]
    return round(sum(item == expected for item in selected) / len(selected), 4) if selected else None


def rounded_difference(left: Any, right: Any) -> float | None:
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
        return None
    return round(float(left) - float(right), 4)
