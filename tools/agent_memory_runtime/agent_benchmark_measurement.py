# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .agent_benchmark_treatment import SELECTIVE_TREATMENT_SCHEMA, TREATMENT_SCHEMA


def measurement_contract_audit(observations: list[dict[str, Any]]) -> dict[str, Any]:
    treatments = [item.get("treatment_metadata") for item in observations]
    if any(
        isinstance(item, dict) and item.get("schema_version") == SELECTIVE_TREATMENT_SCHEMA
        for item in treatments
    ):
        return selective_measurement_contract_audit(observations, treatments)
    enforced = any(
        isinstance(item, dict) and item.get("schema_version") == TREATMENT_SCHEMA
        for item in treatments
    )
    if not enforced:
        return {"status": "legacy_unreported", "enforced": False, "checks": {}}
    checks = {
        "all_treatments_reported": len(observations) > 0 and all(
            isinstance(item, dict) and item.get("schema_version") == TREATMENT_SCHEMA
            for item in treatments
        ),
        "shared_investigation_contract": one_value(
            item.get("investigation_contract_digest")
            for item in treatments if isinstance(item, dict)
        ),
        "baseline_context_absent": all(
            not bool(item.get("treatment_metadata", {}).get("context_present"))
            for item in observations if item.get("variant") == "baseline"
        ),
        "memory_context_present": all(
            bool(item.get("treatment_metadata", {}).get("context_present"))
            for item in observations if item.get("variant") == "memory"
        ),
        "latency_attribution_complete": all(
            bool(item.get("latency_metrics_reported")) for item in observations
        ),
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "enforced": True,
        "checks": checks,
    }


def selective_measurement_contract_audit(
    observations: list[dict[str, Any]],
    treatments: list[Any],
) -> dict[str, Any]:
    baseline = [item for item in observations if item.get("variant") == "baseline"]
    memory = [item for item in observations if item.get("variant") == "memory"]
    checks = {
        "all_treatments_reported": bool(observations) and all(
            isinstance(item, dict)
            and item.get("schema_version") == SELECTIVE_TREATMENT_SCHEMA
            for item in treatments
        ),
        "shared_investigation_contract": one_value(
            item.get("investigation_contract_digest")
            for item in treatments if isinstance(item, dict)
        ),
        "baseline_query_skill_absent": bool(baseline) and all(
            not bool(item.get("treatment_metadata", {}).get("query_skill_available"))
            for item in baseline
        ),
        "memory_query_skill_present": bool(memory) and all(
            bool(item.get("treatment_metadata", {}).get("query_skill_available"))
            and bool(item.get("treatment_metadata", {}).get("query_skill_digest"))
            for item in memory
        ),
        "preloaded_context_absent": all(
            not bool(item.get("treatment_metadata", {}).get("preloaded_context"))
            and not bool(item.get("treatment_metadata", {}).get("context_present"))
            for item in observations
        ),
        "baseline_memory_query_absent": all(
            int(item.get("memory_query_count") or 0) == 0 for item in baseline
        ),
        "memory_query_within_budget": all(
            0 <= int(item.get("memory_query_count") or 0)
            <= int(item.get("treatment_metadata", {}).get("query_limit") or 0)
            for item in memory
        ),
        "latency_attribution_complete": all(
            bool(item.get("latency_metrics_reported")) for item in observations
        ),
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "enforced": True,
        "mode": "selective_query_skill",
        "checks": checks,
    }


def evidence_segments(
    cases: list[dict[str, Any]], results: list[dict[str, Any]]
) -> dict[str, Any]:
    result_by_id = {item["case_id"]: item for item in results}
    groups = {
        "protocol_calibration": [],
        "real_cases": [],
    }
    for case in cases:
        role = evaluation_role(case)
        if case["id"] in result_by_id:
            groups[role].append(result_by_id[case["id"]])
    return {key: segment_summary(values) for key, values in groups.items()}


def evaluation_role(case: dict[str, Any]) -> str:
    explicit = str(case.get("evaluation_role") or "").strip()
    if explicit in {"protocol_calibration", "real_cases"}:
        return explicit
    provenance = case.get("provenance")
    kind = provenance.get("kind") if isinstance(provenance, dict) else None
    return "protocol_calibration" if kind == "mutation" else "real_cases"


def segment_summary(values: list[dict[str, Any]]) -> dict[str, Any]:
    variants = {
        variant: [
            item["variants"][variant]
            for item in values if variant in item.get("variants", {})
        ]
        for variant in ("baseline", "memory")
    }
    return {
        "case_count": len(values),
        "mechanism_case_count": sum(
            bool(item.get("mechanism_evidence_eligible"))
            for scores in variants.values() for item in scores
        ) // 2,
        "baseline": score_summary(variants["baseline"]),
        "memory": score_summary(variants["memory"]),
    }


def score_summary(values: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "localization_outcome_score": average(values, "agent_outcome_score"),
        "root_cause_category_accuracy": average(values, "agent_root_cause_match"),
        "mechanism_evidence_score": average(values, "mechanism_evidence_score"),
    }


def runner_configuration_consistent(observations: list[dict[str, Any]]) -> bool:
    values = [item.get("runner_metadata") for item in observations
              if isinstance(item.get("runner_metadata"), dict)]
    if not values:
        return True
    return len(values) == len(observations) and one_value(
        repr(sorted(value.items())) for value in values
    )


def memory_context_within_budget(
    observations: list[dict[str, Any]], token_budget: int = 1500
) -> bool:
    memory = [item for item in observations if item.get("variant") == "memory"]
    reported = [item for item in memory if item.get(
        "memory_context_metrics_reported", "memory_context_token_estimate" in item
    )]
    if not reported:
        return True
    return len(reported) == len(memory) and all(
        context_tokens_valid(item, token_budget) for item in reported
    )


def context_tokens_valid(item: dict[str, Any], token_budget: int) -> bool:
    tokens = int(item["memory_context_token_estimate"])
    metadata = item.get("treatment_metadata")
    if (
        isinstance(metadata, dict)
        and metadata.get("schema_version") == SELECTIVE_TREATMENT_SCHEMA
    ):
        queries = int(item.get("memory_query_count") or 0)
        return tokens == 0 if queries == 0 else 0 < tokens <= token_budget
    return 0 < tokens <= token_budget


def average(values: list[dict[str, Any]], key: str) -> float | None:
    numbers = [float(item[key]) for item in values if isinstance(item.get(key), (int, float))]
    return round(sum(numbers) / len(numbers), 4) if numbers else None


def one_value(values: Any) -> bool:
    selected = [value for value in values if value not in (None, "")]
    return bool(selected) and len(set(selected)) == 1
