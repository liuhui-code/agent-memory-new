# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from .benchmark_context_setup import context_setup_audit


PROFILE_SCHEMA = "agent-memory-longitudinal-stage/v1"
STAGES = ("structural_context", "agent_memory", "ideal_memory")


def evaluate_longitudinal_value(
    cases: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    benchmark_result: dict[str, Any],
) -> dict[str, Any] | None:
    groups = validate_longitudinal_cases(cases)
    if not groups:
        return None
    case_results = {
        str(item.get("case_id") or ""): item
        for item in benchmark_result.get("cases") or []
    }
    observation_map = {
        (str(item.get("case_id") or ""), str(item.get("variant") or ""),
         int(item.get("trial_index") or 1)): item
        for item in observations
    }
    results = [
        evaluate_group(group_id, stage_cases, case_results, observation_map)
        for group_id, stage_cases in sorted(groups.items())
    ]
    return {
        "schema_version": "agent-memory-longitudinal-value/v1",
        "evidence_level": "development",
        "serving_behavior_changed": False,
        "group_count": len(results),
        "groups": results,
        "audit": {
            "llm_judge_used": False,
            "raw_logs_persisted_to_memory": False,
            "setup_hidden_from_runner": True,
            "setup_digest_proves_validity": False,
        },
    }


def validate_longitudinal_cases(
    cases: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    groups: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    any_profile = False
    for case in cases:
        profile = case.get("longitudinal")
        if profile is None:
            continue
        any_profile = True
        if not isinstance(profile, dict) or profile.get("schema_version") != PROFILE_SCHEMA:
            raise SystemExit(f"case {case['id']} has invalid longitudinal profile")
        group_id = required_text(profile, "group_id", case["id"])
        stage = required_text(profile, "stage", case["id"])
        if stage not in STAGES:
            raise SystemExit(f"case {case['id']} has unsupported longitudinal stage: {stage}")
        if stage in groups[group_id]:
            raise SystemExit(f"longitudinal group {group_id} repeats stage {stage}")
        required_text(profile, "history_cutoff", case["id"])
        required_text(profile, "setup_origin", case["id"])
        groups[group_id][stage] = case
    if not any_profile:
        return {}
    for group_id, stage_cases in groups.items():
        missing = [stage for stage in STAGES if stage not in stage_cases]
        if missing:
            raise SystemExit(
                f"longitudinal group {group_id} is missing stages: {', '.join(missing)}"
            )
        validate_group_contract(group_id, stage_cases)
    return dict(groups)


def validate_group_contract(
    group_id: str,
    stage_cases: dict[str, dict[str, Any]],
) -> None:
    identities = {
        canonical_identity(case)
        for case in stage_cases.values()
    }
    if len(identities) != 1:
        raise SystemExit(f"longitudinal group {group_id} must share task, source, and oracle")
    cutoffs = {
        str(case["longitudinal"]["history_cutoff"])
        for case in stage_cases.values()
    }
    if len(cutoffs) != 1:
        raise SystemExit(f"longitudinal group {group_id} must share one history cutoff")
    structural = context_setup_audit(stage_cases["structural_context"].get("context_setup"))
    agent = context_setup_audit(stage_cases["agent_memory"].get("context_setup"))
    ideal = context_setup_audit(stage_cases["ideal_memory"].get("context_setup"))
    if structural["reflection_count"] != 0:
        raise SystemExit(f"longitudinal group {group_id} structural stage cannot inject history")
    if agent["reflection_count"] < 1 or ideal["reflection_count"] < 1:
        raise SystemExit(f"longitudinal group {group_id} memory stages require reflections")


def evaluate_group(
    group_id: str,
    stage_cases: dict[str, dict[str, Any]],
    case_results: dict[str, dict[str, Any]],
    observations: dict[tuple[str, str, int], dict[str, Any]],
) -> dict[str, Any]:
    stages = {
        stage: stage_result(case, case_results.get(case["id"]), observations)
        for stage, case in stage_cases.items()
    }
    structural_delta = stages["structural_context"]["outcome_delta"]
    agent_delta = stages["agent_memory"]["outcome_delta"]
    ideal_delta = stages["ideal_memory"]["outcome_delta"]
    first_loss = classify_first_loss(structural_delta, agent_delta, ideal_delta)
    profiles = [case["longitudinal"] for case in stage_cases.values()]
    ideal_frozen = all(bool(item.get("ideal_pre_target_frozen")) for item in profiles)
    return {
        "group_id": group_id,
        "history_cutoff": profiles[0]["history_cutoff"],
        "stages": stages,
        "comparisons": {
            "structural_vs_source_only": structural_delta,
            "agent_memory_increment_over_structural": difference(agent_delta, structural_delta),
            "ideal_increment_over_agent_memory": difference(ideal_delta, agent_delta),
        },
        "observed_first_value_loss": first_loss,
        "ideal_upper_bound_validity": (
            "pre_target_frozen" if ideal_frozen else "development_posthoc_or_unverified"
        ),
        "decision_scope": (
            "development_observation" if not ideal_frozen else "development_pre_target_control"
        ),
    }


def stage_result(
    case: dict[str, Any],
    result: dict[str, Any] | None,
    observations: dict[tuple[str, str, int], dict[str, Any]],
) -> dict[str, Any]:
    expected_setup = context_setup_audit(case.get("context_setup"))
    memory_observations = [
        value for key, value in observations.items()
        if key[0] == case["id"] and key[1] == "memory"
    ]
    setup_verified = bool(memory_observations) and all(
        item.get("memory_setup") == expected_setup for item in memory_observations
    )
    variants = result.get("variants") if isinstance(result, dict) else {}
    baseline = variants.get("baseline") if isinstance(variants, dict) else None
    memory = variants.get("memory") if isinstance(variants, dict) else None
    return {
        "case_id": case["id"],
        "setup_origin": case["longitudinal"]["setup_origin"],
        "setup": expected_setup,
        "setup_verified": setup_verified,
        "baseline_outcome_score": metric(baseline, "agent_outcome_score"),
        "memory_outcome_score": metric(memory, "agent_outcome_score"),
        "outcome_delta": result.get("context_outcome_delta") if isinstance(result, dict) else None,
        "memory_anchor_hit_count": metric(memory, "memory_anchor_hit_count"),
        "memory_context_tokens": metric(memory, "memory_context_token_estimate"),
    }


def classify_first_loss(
    structural: float | None,
    agent: float | None,
    ideal: float | None,
) -> dict[str, str]:
    if None in (structural, agent, ideal):
        return {"layer": "experiment_execution", "reason": "incomplete paired observations"}
    if ideal <= 0:
        return {
            "layer": "memory_value_unproven",
            "reason": "even ideal history did not improve the source-only baseline",
        }
    if structural < 0:
        return {
            "layer": "structural_context_interference",
            "reason": "code/log context reduced Agent outcome before history was injected",
        }
    if agent < structural:
        return {
            "layer": "agent_memory_interference",
            "reason": "Agent-authored history reduced uplift relative to structural context",
        }
    if ideal > agent:
        return {
            "layer": "experience_capture_quality",
            "reason": "reviewed ideal history outperformed Agent-authored history",
        }
    return {"layer": "none_observed", "reason": "no ordered value loss was observed"}


def canonical_identity(case: dict[str, Any]) -> str:
    return json.dumps(
        {key: case.get(key) for key in ("task_type", "task", "source", "oracle")},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def required_text(value: dict[str, Any], key: str, case_id: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise SystemExit(f"case {case_id} longitudinal profile requires {key}")
    return item.strip()


def metric(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, dict) else None


def difference(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(float(left) - float(right), 4)
