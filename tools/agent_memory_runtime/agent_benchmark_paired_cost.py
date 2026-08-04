# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from statistics import median
from typing import Any


PAIRED_METRICS = (
    "token_estimate",
    "model_uncached_input_tokens",
    "model_output_tokens",
    "elapsed_ms",
    "source_search_count",
    "source_read_count",
)


def paired_effect_summary(observations: list[dict[str, Any]]) -> dict[str, Any]:
    indexed = {
        (str(item.get("case_id") or ""), int(item.get("trial_index") or 1),
         str(item.get("variant") or "")): item
        for item in observations
    }
    pair_keys = sorted({(case_id, trial) for case_id, trial, _ in indexed})
    pairs = [
        (indexed[(case_id, trial, "baseline")], indexed[(case_id, trial, "memory")])
        for case_id, trial in pair_keys
        if (case_id, trial, "baseline") in indexed
        and (case_id, trial, "memory") in indexed
    ]
    return {
        "pair_count": len(pairs),
        "metrics": {metric: summarize_metric(pairs, metric) for metric in PAIRED_METRICS},
    }


def summarize_metric(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]], metric: str
) -> dict[str, Any]:
    values = [
        (float(baseline[metric]), float(memory[metric]))
        for baseline, memory in pairs
        if isinstance(baseline.get(metric), (int, float))
        and isinstance(memory.get(metric), (int, float))
    ]
    deltas = [memory - baseline for baseline, memory in values]
    ratios = [(memory - baseline) / baseline for baseline, memory in values if baseline > 0]
    return {
        "reported_pairs": len(values),
        "mean_delta": rounded_mean(deltas),
        "median_delta": round(median(deltas), 4) if deltas else None,
        "mean_overhead_ratio": rounded_mean(ratios),
        "median_overhead_ratio": round(median(ratios), 4) if ratios else None,
        "worst_overhead_ratio": round(max(ratios), 4) if ratios else None,
    }


def rounded_mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None
