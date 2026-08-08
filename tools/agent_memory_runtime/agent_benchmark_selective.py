# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .agent_benchmark_treatment import SELECTIVE_TREATMENT_SCHEMA


ACTIVATION_EXPECTATIONS = {"required", "forbidden", "optional"}


def selective_query_audit(
    cases: list[dict[str, Any]], observations: list[dict[str, Any]],
) -> dict[str, Any] | None:
    selected = [item for item in observations if selective_observation(item)]
    if not selected:
        return None
    case_results = [case_audit(case, selected) for case in cases]
    memory = [item for item in selected if item.get("variant") == "memory"]
    expectation_passes = [item["expectation_met"] for item in case_results]
    checks = {
        "baseline_memory_isolated": all(
            int(item.get("memory_query_count") or 0) == 0
            for item in selected if item.get("variant") == "baseline"
        ),
        "query_budget_respected": all(
            not item["query_budget_exceeded"] for item in case_results
        ),
        "query_outcomes_accounted": all(query_outcomes_accounted(item) for item in memory),
        "activation_expectations_met": bool(expectation_passes) and all(
            expectation_passes
        ),
        "memory_queries_error_free": all(
            int(item.get("memory_query_error_count") or 0) == 0 for item in memory
        ),
        "memory_query_telemetry_complete": bool(memory) and all(
            bool(item.get("memory_query_metrics_reported")) for item in memory
        ),
    }
    return {
        "schema_version": "agent-selective-query-audit/v1",
        "status": "pass" if all(checks.values()) else "fail",
        "mode": "selective_query_skill",
        "checks": checks,
        "metrics": {
            "case_count": len(case_results),
            "memory_observation_count": len(memory),
            "activation_rate": ratio(
                sum(int(item.get("memory_query_count") or 0) > 0 for item in memory),
                len(memory),
            ),
            "average_query_count": average(
                [int(item.get("memory_query_count") or 0) for item in memory]
            ),
            "expectation_pass_rate": ratio(sum(expectation_passes), len(expectation_passes)),
        },
        "cases": case_results,
        "boundary": "observable_skill_use_not_hidden_reasoning_or_causal_attribution",
    }


def case_audit(
    case: dict[str, Any], observations: list[dict[str, Any]],
) -> dict[str, Any]:
    case_id = str(case.get("id") or "")
    values = [item for item in observations if item.get("case_id") == case_id]
    baseline = [item for item in values if item.get("variant") == "baseline"]
    memory = [item for item in values if item.get("variant") == "memory"]
    expectation = query_expectation(case)
    counts = [int(item.get("memory_query_count") or 0) for item in memory]
    maximum = int(expectation["max_queries"])
    budget_exceeded = any(value > maximum for value in counts)
    met = expectation_met(str(expectation["activation"]), counts) and not budget_exceeded
    return {
        "case_id": case_id,
        "activation_expectation": expectation["activation"],
        "max_queries": maximum,
        "memory_trial_count": len(memory),
        "memory_query_counts": counts,
        "expectation_met": met,
        "query_budget_exceeded": budget_exceeded,
        "first_observable_loss": first_observable_loss(
            baseline, memory, str(expectation["activation"]), maximum
        ),
    }


def first_observable_loss(
    baseline: list[dict[str, Any]],
    memory: list[dict[str, Any]],
    activation: str,
    maximum: int,
) -> str | None:
    if any(int(item.get("memory_query_count") or 0) for item in baseline):
        return "treatment_isolation"
    if any(not query_outcomes_accounted(item) for item in memory):
        return "telemetry_accounting"
    if any(int(item.get("memory_query_count") or 0) > maximum for item in memory):
        return "query_budget"
    if any(int(item.get("memory_query_error_count") or 0) for item in memory):
        return "skill_execution"
    counts = [int(item.get("memory_query_count") or 0) for item in memory]
    if activation == "required" and (not counts or any(value == 0 for value in counts)):
        return "skill_activation"
    if activation == "forbidden" and any(counts):
        return "selective_routing"
    if any(
        int(item.get("memory_query_count") or 0) > 0
        and int(item.get("memory_query_success_count") or 0) == 0
        for item in memory
    ):
        return "context_retrieval"
    return None


def query_outcomes_accounted(value: dict[str, Any]) -> bool:
    total = int(value.get("memory_query_count") or 0)
    success = int(value.get("memory_query_success_count") or 0)
    errors = int(value.get("memory_query_error_count") or 0)
    return success + errors == total


def query_expectation(case: dict[str, Any]) -> dict[str, Any]:
    oracle = case.get("oracle") if isinstance(case.get("oracle"), dict) else {}
    value = oracle.get("query_skill_expectation")
    value = value if isinstance(value, dict) else {}
    activation = str(value.get("activation") or "optional")
    if activation not in ACTIVATION_EXPECTATIONS:
        activation = "optional"
    maximum = max(0, min(3, int(value.get("max_queries", 3))))
    return {"activation": activation, "max_queries": maximum}


def expectation_met(activation: str, counts: list[int]) -> bool:
    if not counts:
        return False
    if activation == "required":
        return all(value > 0 for value in counts)
    if activation == "forbidden":
        return all(value == 0 for value in counts)
    return True


def selective_observation(value: dict[str, Any]) -> bool:
    metadata = value.get("treatment_metadata")
    return (
        isinstance(metadata, dict)
        and metadata.get("schema_version") == SELECTIVE_TREATMENT_SCHEMA
    )


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def average(values: list[int]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None
