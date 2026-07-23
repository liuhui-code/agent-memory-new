# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .context_compact import COMPACT_TOKEN_BUDGET
from .context_capability_quality import assess_context_quality
from .context_hierarchical_metrics import assess_hierarchical_localization, localization_profile

OBSERVATION_SCHEMA = "agent-context-capability-observation/v1"
RESULT_SCHEMA = "agent-context-capability-result/v1"
def evaluate_context_capability(
    cases: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    by_case = validated_observations(cases, observations)
    scored = [score_case(case, by_case[case["id"]]) for case in cases]
    gate = "pass" if scored and all(item["status"] == "pass" for item in scored) else "fail"
    robustness = query_robustness_profile(scored)
    return {
        "schema_version": RESULT_SCHEMA,
        "status": gate,
        "system_context_gate": gate,
        "summary": {
            "case_count": len(cases),
            "passed_case_count": sum(item["status"] == "pass" for item in scored),
            "failed_case_count": sum(item["status"] == "fail" for item in scored),
            "scenario_count": robustness["scenario_count"],
            "stable_scenario_count": robustness["stable_scenario_count"],
            "query_variant_pass_rate": robustness["variant_pass_rate"],
            "average_context_tokens": average(scored, "context_token_estimate"),
            "average_memory_prepare_ms": average(scored, "memory_prepare_ms"),
            "average_query_elapsed_ms": average(scored, "query_elapsed_ms"),
        },
        "capability_profile": {
            **capability_profile(scored),
            "query_robustness": robustness,
        },
        "cases": scored,
        "audit": {
            "agent_invoked": False,
            "model_output_scored": False,
            "oracle_hidden_during_query": True,
            "source_bodies_persisted": False,
            "temporary_runtime_logs_persisted": False,
            "scope": "context_supply_only",
        },
        "next_gate": "paired_external_agent_ab" if gate == "pass" else "repair_context_supply",
    }

def validated_observations(
    cases: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    expected = {str(case["id"]) for case in cases}
    by_case: dict[str, dict[str, Any]] = {}
    for item in observations:
        if not isinstance(item, dict) or item.get("schema_version") != OBSERVATION_SCHEMA:
            raise SystemExit(f"context capability observation must use {OBSERVATION_SCHEMA}")
        case_id = str(item.get("case_id") or "").strip()
        if case_id not in expected:
            continue
        if case_id in by_case:
            raise SystemExit(f"duplicate context capability observation: {case_id}")
        by_case[case_id] = item
    missing = sorted(expected - set(by_case))
    if missing:
        raise SystemExit(f"missing context capability observations: {', '.join(missing)}")
    return by_case

def score_case(case: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    oracle = case.get("oracle") if isinstance(case.get("oracle"), dict) else {}
    requirements = context_requirements(oracle.get("context_requirements"))
    expected = string_set(oracle.get("expected_files"))
    forbidden = string_set(oracle.get("forbidden_files"))
    anchors = string_set(observation.get("anchor_paths"))
    primary = string_set(observation.get("primary_anchor_paths"))
    candidates = string_set(observation.get("candidate_anchor_paths"))
    excerpts = string_set(observation.get("excerpt_paths"))
    log_keywords = string_set(observation.get("log_keywords"), fold=True)
    log_evidence = string_set(observation.get("log_evidence_texts"), fold=True)
    log_files = string_set(observation.get("log_anchor_paths"))
    experience_types = string_set(observation.get("experience_types"), fold=True)
    main_experience = string_set(observation.get("main_experience_texts"), fold=True)
    guard_experience = string_set(observation.get("guard_experience_texts"), fold=True)
    path_files = string_set(observation.get("path_files"))
    path_relations = string_set(observation.get("path_relations"), fold=True)
    required_logs = requirements["required_log_keywords"]
    required_log_files = requirements["required_log_files"]
    required_experiences = requirements["required_experience_types"]
    required_paths = requirements["required_path_files"]
    missing_logs = unmatched_terms(required_logs, log_evidence)
    missing_log_files = sorted(set(required_log_files) - log_files)
    missing_experiences = unmatched_terms(required_experiences, experience_types)
    missing_paths = sorted(set(required_paths) - path_files)
    missing_path_relations = unmatched_terms(
        requirements["required_path_relations"], path_relations
    )
    forbidden_log_keyword_hits = matched_terms(
        requirements["forbidden_log_keywords"], log_evidence
    )
    forbidden_log_file_hits = sorted(
        set(requirements["forbidden_log_files"]) & log_files
    )
    forbidden_path_hits = sorted(
        set(requirements["forbidden_path_files"]) & path_files
    )
    missing_main_experience = unmatched_terms(
        requirements["required_main_experience_phrases"], main_experience
    )
    forbidden_main_experience = matched_terms(
        requirements["forbidden_main_experience_phrases"], main_experience
    )
    missing_guard_experience = unmatched_terms(
        requirements["required_guard_experience_phrases"], guard_experience
    )
    token_estimate = nonnegative_int(observation.get("context_token_estimate"))
    excerpt_hits = expected & excerpts
    quality = assess_context_quality(requirements, expected, observation)
    localization = assess_hierarchical_localization(expected, requirements, observation)
    checks = {
        "compact_schema_returned": (
            observation.get("context_schema_version") == "agent-context-compact/v1"
        ),
        "context_within_budget": 0 < token_estimate <= COMPACT_TOKEN_BUDGET,
    }
    checks.update(quality["checks"])
    if requirements["require_expected_anchors"]:
        checks["expected_anchors_recalled"] = bool(expected) and expected <= anchors
        checks["forbidden_anchors_absent"] = not bool(forbidden & anchors)
    if required_logs:
        checks["required_log_keywords_recalled"] = not missing_logs
    if required_log_files:
        checks["required_log_files_recalled"] = not missing_log_files
    if requirements["forbidden_log_keywords"]:
        checks["forbidden_log_keywords_absent"] = not forbidden_log_keyword_hits
    if requirements["forbidden_log_files"]:
        checks["forbidden_log_files_absent"] = not forbidden_log_file_hits
    if required_experiences:
        checks["required_experience_types_recalled"] = not missing_experiences
    if requirements["required_main_experience_phrases"]:
        checks["required_main_experience_recalled"] = not missing_main_experience
    if requirements["forbidden_main_experience_phrases"]:
        checks["forbidden_main_experience_absent"] = not forbidden_main_experience
    if requirements["required_guard_experience_phrases"]:
        checks["required_guard_experience_recalled"] = not missing_guard_experience
    if required_paths:
        checks["required_path_files_recalled"] = not missing_paths
    if requirements["required_path_relations"]:
        checks["required_path_relations_recalled"] = not missing_path_relations
    if requirements["forbidden_path_files"]:
        checks["forbidden_path_files_absent"] = not forbidden_path_hits
    if requirements["min_relation_hints"]:
        checks["minimum_relation_hints_met"] = (
            nonnegative_int(observation.get("relation_hint_count"))
            >= requirements["min_relation_hints"]
        )
    if requirements["min_path_candidates"]:
        checks["minimum_path_candidates_met"] = (
            nonnegative_int(observation.get("path_candidate_count"))
            >= requirements["min_path_candidates"]
        )
    if requirements["require_source_excerpt"]:
        checks["expected_source_excerpt_returned"] = bool(excerpt_hits)
    return {
        "case_id": case["id"],
        "scenario_id": case.get("scenario_id") or case["id"],
        "query_variant": case.get("query_variant") or "default",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "anchor_recall": recall(expected, anchors),
        "primary_anchor_recall": recall(expected, primary),
        "candidate_file_recall_at_20": recall(expected, candidates),
        "oracle_anchor_precision": precision(expected, anchors),
        "source_excerpt_recall": recall(expected, excerpts),
        "source_span_recall": quality["source_span_recall"],
        "first_expected_anchor_rank": quality["first_expected_anchor_rank"],
        "expected_anchor_mrr": quality["expected_anchor_mrr"],
        "observed_anchor_paths": sorted(anchors),
        "observed_primary_anchor_paths": sorted(primary),
        "observed_source_excerpt_paths": sorted(excerpts),
        "missing_expected_anchors": sorted(expected - anchors),
        "forbidden_anchor_hits": sorted(forbidden & anchors),
        "missing_required_log_keywords": missing_logs,
        "missing_required_log_files": missing_log_files,
        "forbidden_log_keyword_hits": forbidden_log_keyword_hits,
        "forbidden_log_file_hits": forbidden_log_file_hits,
        "missing_required_experience_types": missing_experiences,
        "missing_required_main_experience": missing_main_experience,
        "forbidden_main_experience_hits": forbidden_main_experience,
        "missing_required_guard_experience": missing_guard_experience,
        "missing_required_path_files": missing_paths,
        "missing_required_path_relations": missing_path_relations,
        "forbidden_path_file_hits": forbidden_path_hits,
        "missing_required_source_spans": quality["missing_required_source_spans"],
        "missing_required_evidence_gaps": quality["missing_required_evidence_gaps"],
        "hierarchical_localization": localization,
        "abstention_observed": quality["abstention_observed"],
        "anchor_count": len(anchors),
        "primary_anchor_count": len(primary),
        "source_excerpt_count": len(excerpts),
        "log_anchor_count": nonnegative_int(observation.get("log_anchor_count")),
        "experience_ref_count": nonnegative_int(observation.get("experience_ref_count")),
        "semantic_ref_count": nonnegative_int(observation.get("semantic_ref_count")),
        "path_candidate_count": nonnegative_int(observation.get("path_candidate_count")),
        "relation_hint_count": nonnegative_int(observation.get("relation_hint_count")),
        "evidence_gaps": string_list(observation.get("evidence_gaps")),
        "context_token_estimate": token_estimate,
        "memory_prepare_ms": nonnegative_int(observation.get("memory_prepare_ms")),
        "query_elapsed_ms": nonnegative_int(observation.get("query_elapsed_ms")),
        "requirements": requirements,
    }

def query_robustness_profile(scored: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in scored:
        grouped.setdefault(str(item["scenario_id"]), []).append(item)
    scenarios = []
    for scenario_id, variants in grouped.items():
        failed = [item["query_variant"] for item in variants if item["status"] != "pass"]
        scenarios.append({
            "scenario_id": scenario_id,
            "status": "pass" if not failed else "fail",
            "variant_count": len(variants),
            "passed_variant_count": len(variants) - len(failed),
            "failed_variants": failed,
        })
    passed = sum(item["status"] == "pass" for item in scored)
    stable = sum(item["status"] == "pass" for item in scenarios)
    return {
        "status": "pass" if scenarios and stable == len(scenarios) else "fail",
        "scenario_count": len(scenarios),
        "stable_scenario_count": stable,
        "variant_count": len(scored),
        "passed_variant_count": passed,
        "variant_pass_rate": round(passed / len(scored), 4) if scored else 0.0,
        "scenarios": scenarios,
    }

def capability_profile(scored: list[dict[str, Any]]) -> dict[str, Any]:
    code_cases = [item for item in scored if item["requirements"]["require_expected_anchors"]]
    code_checks = (
        "expected_anchors_recalled", "forbidden_anchors_absent",
        "expected_anchors_within_top_k", "minimum_anchor_precision_met",
    )
    return {
        "code_locator": {
            "status": (
                "pass" if code_cases and all(
                    all(item["checks"].get(check, True) for check in code_checks)
                    for item in code_cases
                ) else "fail"
                if code_cases else "informational"
            ),
            "evaluated_cases": len(code_cases),
            "anchor_recall": average(code_cases, "anchor_recall"),
            "primary_anchor_recall": average(code_cases, "primary_anchor_recall"),
            "candidate_file_recall_at_20": average(code_cases, "candidate_file_recall_at_20"),
            "oracle_anchor_precision": average(code_cases, "oracle_anchor_precision"),
            "expected_anchor_mrr": average(code_cases, "expected_anchor_mrr"),
        },
        "source_evidence": optional_profile(
            scored,
            ("require_source_excerpt", "required_source_spans"),
            ("expected_source_excerpt_returned", "minimum_source_span_recall_met"),
            {
                "source_excerpt_recall": average(scored, "source_excerpt_recall"),
                "source_span_recall": average(scored, "source_span_recall"),
            },
        ),
        "log_graph": optional_profile(
            scored,
            (
                "required_log_keywords", "required_log_files",
                "forbidden_log_keywords", "forbidden_log_files",
            ),
            (
                "required_log_keywords_recalled", "required_log_files_recalled",
                "forbidden_log_keywords_absent", "forbidden_log_files_absent",
            ),
        ),
        "experience": optional_profile(
            scored,
            (
                "required_experience_types", "required_main_experience_phrases",
                "forbidden_main_experience_phrases", "required_guard_experience_phrases",
            ),
            (
                "required_experience_types_recalled", "required_main_experience_recalled",
                "forbidden_main_experience_absent", "required_guard_experience_recalled",
            ),
        ),
        "causal_context": causal_profile(scored),
        "hierarchical_localization": localization_profile(scored),
        "abstention": optional_profile(
            scored,
            "require_abstention",
            ("abstention_observed", "required_evidence_gaps_reported"),
        ),
        "compactness": {
            "status": profile_status(scored, "context_within_budget"),
            "evaluated_cases": len(scored),
            "average_context_tokens": average(scored, "context_token_estimate"),
            "token_budget": COMPACT_TOKEN_BUDGET,
        },
    }

def optional_profile(
    scored: list[dict[str, Any]],
    requirement_key: str | tuple[str, ...],
    check_key: str | tuple[str, ...],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    requirement_keys = (requirement_key,) if isinstance(requirement_key, str) else requirement_key
    check_keys = (check_key,) if isinstance(check_key, str) else check_key
    evaluated = [
        item for item in scored
        if any(item["requirements"].get(key) for key in requirement_keys)
    ]
    passed = all(
        all(item["checks"].get(key, True) for key in check_keys)
        for item in evaluated
    )
    result = {
        "status": ("pass" if passed else "fail") if evaluated else "informational",
        "evaluated_cases": len(evaluated),
        "observed_case_count": sum(
            observed_capability(item, requirement_keys[0]) for item in scored
        ),
    }
    result.update(extra or {})
    return result


def causal_profile(scored: list[dict[str, Any]]) -> dict[str, Any]:
    evaluated = [
        item for item in scored
        if (
            item["requirements"]["required_path_files"]
            or item["requirements"]["required_path_relations"]
            or item["requirements"]["forbidden_path_files"]
            or item["requirements"]["min_relation_hints"]
            or item["requirements"]["min_path_candidates"]
        )
    ]
    checks = (
        "required_path_files_recalled",
        "required_path_relations_recalled",
        "forbidden_path_files_absent",
        "minimum_relation_hints_met",
        "minimum_path_candidates_met",
    )
    passed = all(
        all(item["checks"].get(check, True) for check in checks)
        for item in evaluated
    )
    return {
        "status": ("pass" if passed else "fail") if evaluated else "informational",
        "evaluated_cases": len(evaluated),
        "observed_path_case_count": sum(item["path_candidate_count"] > 0 for item in scored),
        "observed_relation_case_count": sum(item["relation_hint_count"] > 0 for item in scored),
    }


def context_requirements(value: Any) -> dict[str, Any]:
    item = value if isinstance(value, dict) else {}
    return {
        "required_log_keywords": string_list(item.get("required_log_keywords"), fold=True),
        "required_log_files": string_list(item.get("required_log_files")),
        "forbidden_log_keywords": string_list(item.get("forbidden_log_keywords"), fold=True),
        "forbidden_log_files": string_list(item.get("forbidden_log_files")),
        "required_experience_types": string_list(
            item.get("required_experience_types"), fold=True
        ),
        "required_main_experience_phrases": string_list(
            item.get("required_main_experience_phrases"), fold=True
        ),
        "forbidden_main_experience_phrases": string_list(
            item.get("forbidden_main_experience_phrases"), fold=True
        ),
        "required_guard_experience_phrases": string_list(
            item.get("required_guard_experience_phrases"), fold=True
        ),
        "required_path_files": string_list(item.get("required_path_files")),
        "required_path_relations": string_list(item.get("required_path_relations"), fold=True),
        "forbidden_path_files": string_list(item.get("forbidden_path_files")),
        "min_relation_hints": nonnegative_int(item.get("min_relation_hints")),
        "min_path_candidates": nonnegative_int(item.get("min_path_candidates")),
        "require_source_excerpt": bool(item.get("require_source_excerpt")),
        "require_expected_anchors": item.get("require_expected_anchors") is not False,
        "required_top_k": nonnegative_int(item.get("required_top_k")),
        "min_anchor_precision": optional_ratio(item.get("min_anchor_precision")),
        "required_source_spans": source_spans(item.get("required_source_spans")),
        "required_owner_spans": source_spans(item.get("required_owner_spans")),
        "hierarchical_callable_spans": source_spans(item.get("hierarchical_callable_spans")),
        "hierarchical_owner_spans": source_spans(item.get("hierarchical_owner_spans")),
        "hierarchical_range_spans": source_spans(item.get("hierarchical_range_spans")),
        "min_source_span_recall": optional_ratio(
            item.get("min_source_span_recall"), default=1.0
        ),
        "require_abstention": bool(item.get("require_abstention")),
        "required_evidence_gaps": string_list(item.get("required_evidence_gaps")),
    }


def observed_capability(item: dict[str, Any], requirement_key: str) -> bool:
    fields = {
        "require_source_excerpt": "source_excerpt_count",
        "required_log_keywords": "log_anchor_count",
        "required_experience_types": "experience_ref_count",
        "require_abstention": "abstention_observed",
    }
    return bool(item.get(fields[requirement_key], 0))


def profile_status(values: list[dict[str, Any]], check: str) -> str:
    return "pass" if values and all(item["checks"].get(check, False) for item in values) else "fail"


def unmatched_terms(required: list[str], observed: set[str]) -> list[str]:
    return [
        term for term in required
        if not any(term == value or term in value for value in observed)
    ]


def matched_terms(required: list[str], observed: set[str]) -> list[str]:
    return [
        term for term in required
        if any(term == value or term in value for value in observed)
    ]


def recall(expected: set[str], observed: set[str]) -> float:
    return round(len(expected & observed) / len(expected), 4) if expected else 1.0


def precision(expected: set[str], observed: set[str]) -> float:
    return round(len(expected & observed) / len(observed), 4) if observed else 0.0


def average(values: list[dict[str, Any]], key: str) -> float | None:
    numbers = [float(item[key]) for item in values if item.get(key) is not None]
    return round(sum(numbers) / len(numbers), 4) if numbers else None


def string_set(value: Any, fold: bool = False) -> set[str]:
    return set(string_list(value, fold))


def string_list(value: Any, fold: bool = False) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [str(item).strip() for item in value if str(item).strip()]
    if fold:
        items = [item.casefold() for item in items]
    return list(dict.fromkeys(items))


def nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def optional_ratio(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit("context capability ratio must be numeric") from exc
    if not 0.0 <= result <= 1.0:
        raise SystemExit("context capability ratio must be between 0 and 1")
    return result


def source_spans(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 20:
        raise SystemExit("required_source_spans must be a list with at most 20 items")
    result = []
    for item in value:
        if not isinstance(item, dict) or not str(item.get("file_path") or "").strip():
            raise SystemExit("required source span requires file_path")
        span = {"file_path": str(item["file_path"]).strip()}
        if item.get("symbol"):
            span["symbol"] = str(item["symbol"]).strip()
        if isinstance(item.get("start_line"), int) and isinstance(item.get("end_line"), int):
            if item["start_line"] <= 0 or item["end_line"] < item["start_line"]:
                raise SystemExit("required source span line range is invalid")
            span.update({"start_line": item["start_line"], "end_line": item["end_line"]})
        if "symbol" not in span and "start_line" not in span:
            raise SystemExit("required source span requires symbol or line range")
        result.append(span)
    return result
