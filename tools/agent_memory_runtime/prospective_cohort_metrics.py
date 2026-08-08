# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .prospective_cohort_snapshot import canonical_digest


def sanitize_usage_trace(trace: dict[str, Any], sample_id: str) -> dict[str, Any]:
    bound = bool(trace) and trace.get("sample_id") == sample_id
    execution = trace.get("query_execution") if isinstance(trace.get("query_execution"), dict) else {}
    numeric_execution = {
        str(key): value
        for key, value in execution.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        and safe_metric_name(str(key))
    }
    matched = trace.get("matched_anchor_counts")
    matched = matched if isinstance(matched, dict) else {}
    matched_counts = {
        str(key): int(value)
        for key, value in matched.items()
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
    }
    query_count = int(trace.get("query_rounds") or 0) if bound else 0
    return {
        "schema_version": "prospective-usage-metrics/v1",
        "reported": bound,
        "trace_digest": canonical_digest(trace) if trace else None,
        "command_kinds": sorted({str(item) for item in trace.get("commands") or []}) if bound else [],
        "command_count": len(trace.get("commands") or []) if bound else 0,
        "query_count": query_count,
        "query_error_count": sum(
            int(value) for key, value in numeric_execution.items() if "error" in key
        ),
        "context_use_count": len(trace.get("context_used") or []) if bound else 0,
        "matched_anchor_count": sum(matched_counts.values()) if bound else 0,
        "matched_anchor_counts": matched_counts if bound else {},
        "query_execution_metrics": numeric_execution if bound else {},
    }


def sanitize_benchmark_result(path: Path | None, case_id: str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"failed to read cohort benchmark result: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid cohort benchmark result JSON: {path}") from exc
    if not isinstance(raw, dict) or raw.get("treatment_mode") != "selective-query-skill":
        raise SystemExit("cohort benchmark result must use selective-query-skill")
    selected = [str(item) for item in raw.get("selected_case_ids") or []]
    if not case_id or selected != [case_id]:
        raise SystemExit("cohort benchmark result must contain exactly the linked case")
    measurement = raw.get("measurement_contract")
    if not isinstance(measurement, dict) or measurement.get("status") != "pass":
        raise SystemExit("cohort benchmark measurement contract must pass")
    selective = matching_case(raw.get("selective_query", {}).get("cases"), case_id)
    scored = matching_case(raw.get("cases"), case_id)
    variants = scored.get("variants") if isinstance(scored.get("variants"), dict) else {}
    baseline = metric_projection(variants.get("baseline"))
    memory = metric_projection(variants.get("memory"))
    return {
        "schema_version": "prospective-benchmark-metrics/v1",
        "result_digest": canonical_digest(raw),
        "quality_gate": str(raw.get("quality_gate") or "unknown"),
        "efficiency_gate": str(raw.get("efficiency_gate") or "unknown"),
        "promotion_gate": str(raw.get("promotion_gate") or "unknown"),
        "outcome_delta": number(scored.get("context_outcome_delta")),
        "query_counts": [int(item) for item in selective.get("memory_query_counts") or []],
        "activation_expectation": selective.get("activation_expectation"),
        "expectation_met": bool(selective.get("expectation_met")),
        "first_observable_loss": selective.get("first_observable_loss"),
        "baseline": baseline,
        "memory": memory,
    }


def build_cohort_report(
    cohort: dict[str, Any], tasks: list[dict[str, Any]], chain_valid: bool,
) -> dict[str, Any]:
    evidence_origin = str(cohort.get("protocol", {}).get("evidence_origin") or "unknown")
    eligible = [item for item in tasks if item["eligibility"] == "eligible"]
    opportunity = [item for item in eligible if item["opportunity"] == "present"]
    completed = [item for item in eligible if item["status"] == "completed"]
    benchmark_count = sum(bool(item.get("benchmark_metrics")) for item in completed)
    terminal = all(item["status"] in {"completed", "excluded"} for item in tasks)
    target_met = len(tasks) == int(cohort["target_presented_tasks"])
    trace_coverage = ratio(
        sum(bool(item.get("usage_metrics", {}).get("reported")) for item in completed),
        len(completed),
    )
    trace_complete = all(
        bool(item.get("usage_metrics", {}).get("reported")) for item in completed
    )
    quality_ready = (
        chain_valid and target_met and terminal
        and len(completed) == len(eligible) and trace_complete
    )
    return {
        "schema_version": "prospective-agent-cohort-report/v1",
        "cohort_id": cohort["cohort_id"],
        "status": cohort["status"],
        "protocol_digest": cohort["protocol_digest"],
        "data_quality": {
            "status": "pass" if quality_ready else "in_progress",
            "chain_valid": chain_valid,
            "sequence_contiguous": sequence_contiguous(tasks),
            "target_met": target_met,
            "terminal_complete": terminal,
            "presented_count": len(tasks),
            "target_presented_tasks": int(cohort["target_presented_tasks"]),
            "eligible_count": len(eligible),
            "excluded_count": len(tasks) - len(eligible),
            "usage_trace_coverage": trace_coverage,
            "benchmark_binding_coverage": ratio(benchmark_count, len(completed)),
            "clean_source_replay_coverage": ratio(
                sum(bool(item.get("replay_eligible")) for item in eligible), len(eligible)
            ),
            "opportunity_label_coverage": ratio(
                sum(item["opportunity"] != "unknown" for item in eligible), len(eligible)
            ),
            "exclusion_reasons": dict(sorted(Counter(
                item["exclusion_reason"] for item in tasks if item.get("exclusion_reason")
            ).items())),
        },
        "segments": {
            "natural": segment_metrics(eligible),
            "memory_opportunity": segment_metrics(opportunity),
        },
        "evidence_mode": (
            "paired_selective_query" if completed and benchmark_count == len(completed)
            else "mixed" if benchmark_count else "observational"
        ),
        "evidence_origin": evidence_origin,
        "evidence_level": (
            "protocol_calibration"
            if evidence_origin == "generated_protocol_calibration"
            else "prospective_development"
        ),
        "capability_claim": (
            "protocol_only"
            if evidence_origin == "generated_protocol_calibration"
            else "development_observation"
        ),
        "promotion_eligible": False,
        "external_consecutiveness": "self_attested",
        "statistical_scope": "descriptive_development_not_generalization",
        "privacy": {
            "raw_task_persisted": False,
            "raw_query_persisted": False,
            "raw_logs_persisted": False,
            "reasoning_persisted": False,
        },
    }


def segment_metrics(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [item for item in tasks if item["status"] == "completed"]
    usage = [item.get("usage_metrics") or {} for item in completed]
    benchmarks = [item.get("benchmark_metrics") for item in completed if item.get("benchmark_metrics")]
    outcomes = Counter(str(item.get("outcome") or "unknown") for item in completed)
    losses = Counter(
        str(item.get("first_observable_loss") or "none") for item in benchmarks
    )
    verified = [item for item in completed if item.get("verification") != "unverified"]
    return {
        "eligible_count": len(tasks),
        "completed_count": len(completed),
        "outcomes": dict(sorted(outcomes.items())),
        "verified_success_rate": ratio(
            sum(item.get("outcome") == "pass" for item in verified), len(verified)
        ),
        "activation_rate": ratio(sum(int(item.get("query_count") or 0) > 0 for item in usage), len(usage)),
        "average_query_count": average([float(item.get("query_count") or 0) for item in usage]),
        "query_error_count": sum(int(item.get("query_error_count") or 0) for item in usage),
        "paired_benchmark_count": len(benchmarks),
        "paired_quality_pass_rate": ratio(
            sum(item.get("quality_gate") == "pass" for item in benchmarks), len(benchmarks)
        ),
        "paired_efficiency_pass_rate": ratio(
            sum(item.get("efficiency_gate") == "pass" for item in benchmarks), len(benchmarks)
        ),
        "average_outcome_delta": average([
            float(item["outcome_delta"]) for item in benchmarks
            if isinstance(item.get("outcome_delta"), (int, float))
        ]),
        "first_observable_losses": dict(sorted(losses.items())),
        "average_memory_anchor_hit_count": average([
            float(item.get("memory", {}).get("memory_anchor_hit_count") or 0)
            for item in benchmarks
        ]),
        "average_token_overhead_ratio": average_overhead(
            benchmarks, "token_estimate"
        ),
        "average_elapsed_overhead_ratio": average_overhead(
            benchmarks, "elapsed_ms"
        ),
        "average_source_search_delta": average_delta(
            benchmarks, "source_search_count"
        ),
    }


def metric_projection(value: Any) -> dict[str, Any]:
    value = value if isinstance(value, dict) else {}
    keys = (
        "agent_outcome_score", "source_search_count", "source_read_count",
        "token_estimate", "elapsed_ms", "memory_anchor_hit_count",
    )
    return {key: number(value.get(key)) for key in keys}


def matching_case(values: Any, case_id: str) -> dict[str, Any]:
    matches = [item for item in values or [] if isinstance(item, dict) and item.get("case_id") == case_id]
    if len(matches) != 1:
        raise SystemExit(f"cohort benchmark result is missing case metrics: {case_id}")
    return matches[0]


def sequence_contiguous(tasks: list[dict[str, Any]]) -> bool:
    return [int(item["sequence_no"]) for item in tasks] == list(range(1, len(tasks) + 1))


def safe_metric_name(value: str) -> bool:
    return value.endswith(("_count", "_ms", "_tokens", "_bytes"))


def number(value: Any) -> int | float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def average_overhead(values: list[dict[str, Any]], key: str) -> float | None:
    ratios = []
    for item in values:
        baseline = item.get("baseline", {}).get(key)
        memory = item.get("memory", {}).get(key)
        if isinstance(baseline, (int, float)) and baseline > 0 and isinstance(memory, (int, float)):
            ratios.append((float(memory) - float(baseline)) / float(baseline))
    return average(ratios)


def average_delta(values: list[dict[str, Any]], key: str) -> float | None:
    deltas = []
    for item in values:
        baseline = item.get("baseline", {}).get(key)
        memory = item.get("memory", {}).get(key)
        if isinstance(baseline, (int, float)) and isinstance(memory, (int, float)):
            deltas.append(float(memory) - float(baseline))
    return average(deltas)
