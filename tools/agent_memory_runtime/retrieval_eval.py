# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .models import Project
from .query import limited_context
from .records import output
from .storage import ensure_initialized, resolve_project


PASS_EXPECTED_HIT_RATE = 0.8
PASS_BLOCKED_BAD_RATE = 1.0
PASS_EXPECTED_TOP_HIT_RATE = 0.8
PASS_MAX_EXPERIENCE_NOISE_RATE = 0.2
PASS_INTENT_MATCH_RATE = 1.0
PASS_LANE_MATCH_RATE = 1.0


def eval_retrieval_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    cases = load_eval_cases(Path(args.cases))
    data = evaluate_retrieval_cases(project, cases)
    output(data, args.json)


def load_eval_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"eval cases file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid eval cases JSON: {exc}") from exc
    if not isinstance(data, list):
        raise SystemExit("eval cases JSON must be a list")
    return [case for case in data if isinstance(case, dict)]


def evaluate_retrieval_cases(project: Project, cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_results = [evaluate_retrieval_case(project, case) for case in cases]
    expected_total = sum(result["expected_total"] for result in case_results)
    expected_hits = sum(result["expected_hits"] for result in case_results)
    bad_total = sum(result["must_not_include_total"] for result in case_results)
    bad_blocked = sum(result["blocked_bad_matches"] for result in case_results)
    expected_top_total = sum(result["expected_top_total"] for result in case_results)
    expected_top_hits = sum(result["expected_top_hits"] for result in case_results)
    noise_total = sum(result["noise_total"] for result in case_results)
    noise_hits = sum(result["unexpected_noise_count"] for result in case_results)
    intent_total = sum(result["intent_total"] for result in case_results)
    intent_hits = sum(result["intent_hits"] for result in case_results)
    lane_total = sum(result["required_lane_total"] for result in case_results)
    lane_hits = sum(result["required_lane_hits"] for result in case_results)
    blocked_budget_total = sum(result["blocked_budget_total"] for result in case_results)
    blocked_budget_hits = sum(result["blocked_budget_hits"] for result in case_results)
    expected_hit_rate = ratio(expected_hits, expected_total)
    blocked_bad_rate = ratio(bad_blocked, bad_total)
    expected_top_hit_rate = ratio(expected_top_hits, expected_top_total)
    experience_noise_rate = ratio(noise_hits, noise_total) if noise_total else 0.0
    intent_match_rate = ratio(intent_hits, intent_total)
    required_lane_match_rate = ratio(lane_hits, lane_total)
    blocked_budget_rate = ratio(blocked_budget_hits, blocked_budget_total)
    exact_anchor_ranks = [
        rank
        for result in case_results
        for rank in result.get("expected_top_ranks", [])
        if rank is not None
    ]
    quality_gate = (
        "pass"
        if (
            expected_hit_rate >= PASS_EXPECTED_HIT_RATE
            and blocked_bad_rate >= PASS_BLOCKED_BAD_RATE
            and expected_top_hit_rate >= PASS_EXPECTED_TOP_HIT_RATE
            and experience_noise_rate <= PASS_MAX_EXPERIENCE_NOISE_RATE
            and intent_match_rate >= PASS_INTENT_MATCH_RATE
            and required_lane_match_rate >= PASS_LANE_MATCH_RATE
            and blocked_budget_rate >= 1.0
        )
        else "fail"
    )
    return {
        "project_id": project.project_id,
        "quality_gate": quality_gate,
        "summary": {
            "case_count": len(case_results),
            "expected_total": expected_total,
            "expected_hits": expected_hits,
            "expected_hit_rate": expected_hit_rate,
            "must_not_include_total": bad_total,
            "blocked_bad_matches": bad_blocked,
            "blocked_bad_rate": blocked_bad_rate,
            "expected_top_total": expected_top_total,
            "expected_top_hits": expected_top_hits,
            "expected_top_hit_rate": expected_top_hit_rate,
            "exact_anchor_rank": min(exact_anchor_ranks) if exact_anchor_ranks else None,
            "noise_total": noise_total,
            "unexpected_noise_count": noise_hits,
            "experience_noise_rate": experience_noise_rate,
            "intent_total": intent_total,
            "intent_hits": intent_hits,
            "intent_match_rate": intent_match_rate,
            "required_lane_total": lane_total,
            "required_lane_hits": lane_hits,
            "required_lane_match_rate": required_lane_match_rate,
            "blocked_budget_total": blocked_budget_total,
            "blocked_budget_hits": blocked_budget_hits,
            "blocked_budget_rate": blocked_budget_rate,
        },
        "cases": case_results,
        "thresholds": {
            "expected_hit_rate": PASS_EXPECTED_HIT_RATE,
            "blocked_bad_rate": PASS_BLOCKED_BAD_RATE,
            "expected_top_hit_rate": PASS_EXPECTED_TOP_HIT_RATE,
            "max_experience_noise_rate": PASS_MAX_EXPERIENCE_NOISE_RATE,
            "intent_match_rate": PASS_INTENT_MATCH_RATE,
            "required_lane_match_rate": PASS_LANE_MATCH_RATE,
            "blocked_budget_rate": 1.0,
        },
    }


def evaluate_retrieval_case(project: Project, case: dict[str, Any]) -> dict[str, Any]:
    query = str(case.get("query") or "").strip()
    if not query:
        raise SystemExit("eval case query is required")
    context = limited_context(project, query)
    expected = list_specs(case.get("expected"))
    must_not_include = list_specs(case.get("must_not_include"))
    expected_top = list_specs(case.get("expected_top"))
    noise = list_specs(case.get("noise"))
    missed_expected = [spec for spec in expected if not match_spec(context, spec)]
    unexpected_bad = [spec for spec in must_not_include if match_spec(context, spec)]
    top_ranks = [match_rank(context, spec) for spec in expected_top]
    missed_expected_top = [
        spec for spec, rank in zip(expected_top, top_ranks) if rank != 1
    ]
    unexpected_noise = [spec for spec in noise if match_high_trust_noise(context, spec)]
    expected_intent = str(case.get("expected_memory_intent") or "").strip()
    intent_hit = not expected_intent or context.get("memory_intent") == expected_intent
    required_lanes = [str(item) for item in case.get("required_preferred_lanes") or [] if str(item).strip()]
    preferred_lanes = preferred_lanes_from_context(context)
    missing_required_lanes = [lane for lane in required_lanes if lane not in preferred_lanes]
    max_blocked = case.get("max_blocked_memory_notes")
    blocked_count = len(context.get("blocked_memory_notes") or [])
    blocked_budget_hit = max_blocked is None or blocked_count <= int(max_blocked)
    return {
        "name": case.get("name") or query,
        "query": query,
        "memory_intent": context.get("memory_intent"),
        "expected_memory_intent": expected_intent or None,
        "intent_total": 1 if expected_intent else 0,
        "intent_hits": 1 if expected_intent and intent_hit else 0,
        "required_lane_total": len(required_lanes),
        "required_lane_hits": len(required_lanes) - len(missing_required_lanes),
        "required_preferred_lanes": required_lanes,
        "missing_required_preferred_lanes": missing_required_lanes,
        "blocked_memory_note_count": blocked_count,
        "max_blocked_memory_notes": max_blocked,
        "blocked_budget_total": 1 if max_blocked is not None else 0,
        "blocked_budget_hits": 1 if max_blocked is not None and blocked_budget_hit else 0,
        "expected_total": len(expected),
        "expected_hits": len(expected) - len(missed_expected),
        "must_not_include_total": len(must_not_include),
        "blocked_bad_matches": len(must_not_include) - len(unexpected_bad),
        "expected_top_total": len(expected_top),
        "expected_top_hits": len(expected_top) - len(missed_expected_top),
        "expected_top_ranks": top_ranks,
        "noise_total": len(noise),
        "unexpected_noise_count": len(unexpected_noise),
        "missed_expected": missed_expected,
        "unexpected_bad_matches": unexpected_bad,
        "missed_expected_top": missed_expected_top,
        "unexpected_noise_matches": unexpected_noise,
        "result_counts": {
            key: len(value)
            for key, value in context.items()
            if isinstance(value, list)
        },
    }


def preferred_lanes_from_context(context: dict[str, Any]) -> list[str]:
    lanes = context.get("retrieval_lanes")
    if not isinstance(lanes, dict):
        return []
    intent_profile = lanes.get("intent_profile")
    if not isinstance(intent_profile, dict):
        return []
    return [str(item) for item in intent_profile.get("preferred_lanes") or []]


def list_specs(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if not isinstance(value, list):
        raise SystemExit("expected and must_not_include must be lists")
    return [item for item in value if isinstance(item, dict)]


def match_spec(context: dict[str, Any], spec: dict[str, Any]) -> bool:
    result_type = str(spec.get("type") or "")
    if not result_type:
        return False
    values = context.get(result_type)
    if not isinstance(values, list):
        return False
    return any(candidate_matches(item, spec) for item in values if isinstance(item, dict))


def match_rank(context: dict[str, Any], spec: dict[str, Any]) -> int | None:
    result_type = str(spec.get("type") or "")
    values = context.get(result_type)
    if not isinstance(values, list):
        return None
    for index, item in enumerate(values, start=1):
        if isinstance(item, dict) and candidate_matches(item, spec):
            return index
    return None


def match_high_trust_noise(context: dict[str, Any], spec: dict[str, Any]) -> bool:
    result_type = str(spec.get("type") or "")
    values = context.get(result_type)
    if not isinstance(values, list):
        return False
    for item in values:
        if not isinstance(item, dict) or not candidate_matches(item, spec):
            continue
        if float(item.get("trust_score") or 0.0) >= float(spec.get("min_trust_score") or 0.75):
            return True
    return False


def candidate_matches(item: dict[str, Any], spec: dict[str, Any]) -> bool:
    if spec.get("id") is not None and int_or_none(item.get("id")) != int_or_none(spec.get("id")):
        return False
    text = spec.get("text")
    if text is not None:
        needle = str(text).lower()
        field = spec.get("field")
        haystack = str(item.get(str(field)) if field else json.dumps(item, ensure_ascii=False, sort_keys=True)).lower()
        if needle not in haystack:
            return False
    return True


def int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 3)
