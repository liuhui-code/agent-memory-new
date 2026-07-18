# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .agent_benchmark_cost import COST_METRIC_FIELDS, evaluate_efficiency
from .source_exploration import source_exploration_within_budget


CATEGORY_ALIASES = {
    "route": ("route", "router", "navigation", "navigate", "nav ", "路由", "跳转"),
    "resource": ("resource", "asset", "image", "资源", "图片"),
    "media": ("media", "sticker", "video", "webm", "媒体", "贴纸", "视频"),
    "ui_layout": ("ui layout", "layout", "spacing", "width", "breakpoint", "布局", "间距", "宽度", "断点"),
    "database_failure": ("database", "sqlite", "rdb", "db failure", "数据库"),
    "push": ("push", "notification", "推送", "通知"),
    "lifecycle": ("lifecycle", "startup", "onappear", "oncreate", "生命周期", "启动"),
    "state": ("state", "session", "cache", "状态", "会话", "缓存"),
    "async": ("async", "await", "race", "ordering", "异步", "竞态", "时序"),
    "api": ("api", "interface", "endpoint", "接口"),
}
CAUSAL_LEVELS = {"association": 0, "supported": 1, "verified": 2}
MEMORY_CONTEXT_TOKEN_BUDGET = 1500


def evaluate_agent_benchmark(
    pack: dict[str, Any],
    cases: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    selected_case_ids = {case["id"] for case in cases}
    selected_observations = [
        item for item in observations if item.get("case_id") in selected_case_ids
    ]
    by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    duplicates: list[str] = []
    for item in observations:
        key = (item["case_id"], item["variant"], int(item.get("trial_index") or 1))
        if key in by_key:
            duplicates.append(f"{key[0]}:{key[1]}:{key[2]}")
        by_key[key] = item
    results: list[dict[str, Any]] = []
    missing: list[str] = []
    for case in cases:
        results.append(build_case_result(case, by_key, missing))
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
        "every_case_outcome_non_regression": every_case_non_regression(results),
        "trial_stability_non_regression": trial_stability_non_regression(results),
        "memory_root_cause_trial_stability": memory_root_cause_trial_stability(results),
        "runner_configuration_consistent": runner_configuration_consistent(
            selected_observations
        ),
        "memory_context_within_budget": memory_context_within_budget(
            selected_observations
        ),
        "source_exploration_within_budget": source_exploration_within_budget(
            selected_observations
        ),
    }
    gate = "pass" if all(checks.values()) else "fail"
    efficiency = evaluate_efficiency(aggregates, selected_observations)
    return {
        "schema_version": "agent-benchmark-result/v1",
        "status": gate,
        "quality_gate": gate,
        "promotion_gate": (
            "pass" if gate == "pass" and efficiency["efficiency_gate"] == "pass"
            else "fail"
        ),
        "summary": {
            "case_count": len(cases),
            "observation_count": len(observations),
            "missing_observations": missing,
            "duplicate_observations": duplicates,
            "suite": pack.get("suite") or "development",
            "trial_count": max((item["trial_count"] for item in results), default=0),
            "stability_evaluated": max(
                (item["trial_count"] for item in results), default=0
            ) >= 3,
        },
        "metrics": aggregates,
        "context_uplift": deltas,
        "gate_checks": checks,
        **efficiency,
        "minimum_case_count": minimum,
        "cases": results,
        "audit": {
            "llm_judge_used": False,
            "oracle_hidden_during_run": True,
            "reasoning_persisted": False,
            "tool_output_persisted": False,
        },
    }


def build_case_result(
    case: dict[str, Any],
    by_key: dict[tuple[str, str, int], dict[str, Any]],
    missing: list[str],
) -> dict[str, Any]:
    trial_indexes = sorted({
        key[2] for key in by_key if key[0] == case["id"]
    }) or [1]
    trial_results = []
    scores_by_variant: dict[str, list[dict[str, Any]]] = {"baseline": [], "memory": []}
    for trial_index in trial_indexes:
        variants = {}
        for variant in ("baseline", "memory"):
            observation = by_key.get((case["id"], variant, trial_index))
            if not observation:
                missing.append(f"{case['id']}:{variant}:{trial_index}")
                continue
            score = score_observation(case, observation)
            variants[variant] = score
            scores_by_variant[variant].append(score)
        trial_results.append({
            "trial_index": trial_index,
            "variants": variants,
            "context_outcome_delta": score_delta(variants, "agent_outcome_score"),
        })
    variants = {
        variant: aggregate_trial_scores(scores)
        for variant, scores in scores_by_variant.items()
        if scores
    }
    deltas = [
        item["context_outcome_delta"]
        for item in trial_results
        if item["context_outcome_delta"] is not None
    ]
    memory_scores = scores_by_variant["memory"]
    return {
        "case_id": case["id"],
        "task_type": case["task_type"],
        "review_status": case["review_status"],
        "trial_count": len(trial_indexes),
        "trial_non_regression_rate": round(
            sum(float(item) >= 0 for item in deltas) / len(deltas), 4
        ) if deltas else None,
        "memory_root_cause_consistency": consistency_rate(
            memory_scores, "predicted_root_cause_category"
        ),
        "memory_predicted_files_consistency": consistency_rate(
            memory_scores, "predicted_files", list_value=True
        ),
        "variants": variants,
        "trial_results": trial_results if len(trial_indexes) > 1 else [],
        "context_outcome_delta": score_delta(variants, "agent_outcome_score"),
    }


def aggregate_trial_scores(values: list[dict[str, Any]]) -> dict[str, Any]:
    if len(values) == 1:
        return values[0]
    return {
        "agent_outcome_score": average(values, "agent_outcome_score"),
        "agent_root_cause_match": average(values, "agent_root_cause_match"),
        "predicted_root_cause_category": most_common(values, "predicted_root_cause_category"),
        "expected_root_cause_category": values[0]["expected_root_cause_category"],
        "expected_file_recall": average(values, "expected_file_recall"),
        "predicted_file_precision": average(values, "predicted_file_precision"),
        "forbidden_direction_hit": average(values, "forbidden_direction_hit"),
        "forbidden_files": sorted({
            path for item in values for path in item["forbidden_files"]
        }),
        "causal_level_match": average(values, "causal_level_match"),
        "verification_status": most_common(values, "verification_status"),
        "query_rounds": average(values, "query_rounds"),
        "source_search_count": average(values, "source_search_count"),
        "source_search_count_sources": sorted({
            item["source_search_count_source"] for item in values
        }),
        **{key: average(values, key) for key in COST_METRIC_FIELDS},
        "cost_metrics_reported": all(item["cost_metrics_reported"] for item in values),
        "token_estimate": average(values, "token_estimate"),
        "memory_context_bytes": average(values, "memory_context_bytes"),
        "memory_context_token_estimate": average(values, "memory_context_token_estimate"),
        "elapsed_ms": average(values, "elapsed_ms"),
        "source_file_count": average(values, "source_file_count"),
        "memory_anchor_hit_count": average(values, "memory_anchor_hit_count"),
        "memory_anchor_hit_rate": average(values, "memory_anchor_hit_rate"),
        "primary_anchor_hit_count": average(values, "primary_anchor_hit_count"),
        "non_anchor_file_count": average(values, "non_anchor_file_count"),
        "expansion_rounds": average(values, "expansion_rounds"),
        "expansion_file_count": average(values, "expansion_file_count"),
        "expansion_accounting_sources": sorted({
            item["expansion_accounting_source"] for item in values
        }),
        "expansion_reason_codes": sorted({
            reason for item in values for reason in item["expansion_reason_codes"]
        }),
        "stop_reason": most_common(values, "stop_reason"),
        "exploration_metrics_reported": all(
            item["exploration_metrics_reported"] for item in values
        ),
        "predicted_files": sorted({
            path for item in values for path in item["predicted_files"]
        })[:20],
        "supporting_files": sorted({
            path for item in values for path in item["supporting_files"]
        })[:20],
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
        "source_search_count": observation.get("source_search_count", 0),
        "source_search_count_source": observation.get(
            "source_search_count_source", "agent_reported"
        ),
        "token_estimate": observation["token_estimate"],
        **{key: observation.get(key, 0) for key in COST_METRIC_FIELDS},
        "cost_metrics_reported": bool(observation.get("cost_metrics_reported")),
        "memory_context_bytes": observation.get("memory_context_bytes", 0),
        "memory_context_token_estimate": observation.get("memory_context_token_estimate", 0),
        "elapsed_ms": observation["elapsed_ms"],
        "source_file_count": observation.get("source_file_count", 0),
        "memory_anchor_hit_count": observation.get("memory_anchor_hit_count", 0),
        "memory_anchor_hit_rate": anchor_hit_rate(observation),
        "primary_anchor_hit_count": observation.get("primary_anchor_hit_count", 0),
        "non_anchor_file_count": observation.get("non_anchor_file_count", 0),
        "expansion_rounds": observation.get("expansion_rounds", 0),
        "expansion_file_count": observation.get("expansion_file_count", 0),
        "expansion_accounting_source": observation.get(
            "expansion_accounting_source", "agent_trace"
        ),
        "expansion_reason_codes": observation.get("expansion_reason_codes", []),
        "stop_reason": observation.get("stop_reason", "unreported"),
        "exploration_metrics_reported": bool(
            observation.get("exploration_metrics_reported")
        ),
        "predicted_files": observation["predicted_files"][:20],
        "supporting_files": observation.get("supporting_files", [])[:20],
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
        "agent_root_cause_accuracy": average(values, "agent_root_cause_match"),
        "expected_file_recall": average(values, "expected_file_recall"),
        "predicted_file_precision": average(values, "predicted_file_precision"),
        "forbidden_direction_rate": average(values, "forbidden_direction_hit"),
        "causal_calibration_accuracy": average(values, "causal_level_match"),
        "verification_pass_rate": value_rate(values, "verification_status", "pass"),
        "average_query_rounds": average(values, "query_rounds"),
        "average_source_search_count": average(values, "source_search_count"),
        "average_token_estimate": average(values, "token_estimate"),
        **{
            f"average_{key}": average(values, key)
            for key in COST_METRIC_FIELDS
        },
        "average_memory_context_bytes": average(values, "memory_context_bytes"),
        "average_memory_context_token_estimate": average(values, "memory_context_token_estimate"),
        "average_elapsed_ms": average(values, "elapsed_ms"),
        "average_source_file_count": average(values, "source_file_count"),
        "average_memory_anchor_hit_count": average(values, "memory_anchor_hit_count"),
        "average_memory_anchor_hit_rate": average(values, "memory_anchor_hit_rate"),
        "average_primary_anchor_hit_count": average(values, "primary_anchor_hit_count"),
        "average_non_anchor_file_count": average(values, "non_anchor_file_count"),
        "average_supporting_file_count": round(
            sum(len(item["supporting_files"]) for item in values) / len(values), 4
        ) if values else None,
        "average_expansion_rounds": average(values, "expansion_rounds"),
        "average_expansion_file_count": average(values, "expansion_file_count"),
        "reported_stop_reasons": sorted({
            str(item["stop_reason"])
            for item in values
            if item.get("stop_reason") not in {None, "unreported"}
        }),
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


def every_case_non_regression(results: list[dict[str, Any]]) -> bool:
    return all(
        item.get("context_outcome_delta") is not None
        and float(item["context_outcome_delta"]) >= 0
        for item in results
    )


def trial_stability_non_regression(results: list[dict[str, Any]]) -> bool:
    evaluated = [item for item in results if int(item.get("trial_count") or 0) >= 3]
    return all(
        item.get("trial_non_regression_rate") is not None
        and float(item["trial_non_regression_rate"]) >= (2 / 3)
        for item in evaluated
    )


def memory_root_cause_trial_stability(results: list[dict[str, Any]]) -> bool:
    evaluated = [item for item in results if int(item.get("trial_count") or 0) >= 3]
    return all(
        item.get("memory_root_cause_consistency") is not None
        and float(item["memory_root_cause_consistency"]) >= (2 / 3)
        for item in evaluated
    )


def consistency_rate(
    values: list[dict[str, Any]],
    key: str,
    list_value: bool = False,
) -> float | None:
    selected = []
    for item in values:
        value = item.get(key)
        if value is None:
            continue
        selected.append(tuple(sorted(value)) if list_value and isinstance(value, list) else value)
    if not selected:
        return None
    return round(max(selected.count(value) for value in set(selected)) / len(selected), 4)


def anchor_hit_rate(observation: dict[str, Any]) -> float | None:
    if observation.get("variant") != "memory":
        return None
    source_count = int(observation.get("source_file_count") or 0)
    if source_count <= 0:
        return 0.0
    return round(
        min(int(observation.get("memory_anchor_hit_count") or 0), source_count) / source_count,
        4,
    )


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


def most_common(values: list[dict[str, Any]], key: str) -> Any:
    selected = [item.get(key) for item in values if item.get(key) is not None]
    return max(selected, key=selected.count) if selected else None


def rounded_difference(left: Any, right: Any) -> float | None:
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
        return None
    return round(float(left) - float(right), 4)


def runner_configuration_consistent(observations: list[dict[str, Any]]) -> bool:
    values = [
        item.get("runner_metadata")
        for item in observations
        if isinstance(item.get("runner_metadata"), dict)
    ]
    if not values:
        return True
    if len(values) != len(observations):
        return False
    return len({
        repr(sorted(value.items()))
        for value in values
    }) == 1


def memory_context_within_budget(observations: list[dict[str, Any]]) -> bool:
    memory = [item for item in observations if item.get("variant") == "memory"]
    reported = [
        item for item in memory
        if item.get(
            "memory_context_metrics_reported",
            "memory_context_token_estimate" in item,
        )
    ]
    if not reported:
        return True
    return len(reported) == len(memory) and all(
        0 < int(item["memory_context_token_estimate"]) <= MEMORY_CONTEXT_TOKEN_BUDGET
        for item in reported
    )
