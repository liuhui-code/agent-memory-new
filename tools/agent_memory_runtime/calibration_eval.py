# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .models import Project
from .query import limited_context
from .records import output
from .retrieval_eval import candidate_matches, list_specs, ratio
from .storage import ensure_initialized, resolve_project


PASS_EXPECTED_TRUST_RATE = 0.8
PASS_BLOCKED_OVERTRUST_RATE = 1.0


def eval_calibration_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    cases = load_calibration_cases(Path(args.cases))
    data = evaluate_calibration_cases(project, cases)
    output(data, args.json)


def load_calibration_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"calibration cases file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid calibration cases JSON: {exc}") from exc
    if not isinstance(data, list):
        raise SystemExit("calibration cases JSON must be a list")
    return [case for case in data if isinstance(case, dict)]


def evaluate_calibration_cases(project: Project, cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_results = [evaluate_calibration_case(project, case) for case in cases]
    expected_total = sum(result["expected_trust_total"] for result in case_results)
    expected_hits = sum(result["expected_trust_hits"] for result in case_results)
    overtrust_total = sum(result["must_not_trust_total"] for result in case_results)
    blocked_overtrust = sum(result["blocked_overtrust_matches"] for result in case_results)
    expected_trust_rate = ratio(expected_hits, expected_total)
    blocked_overtrust_rate = ratio(blocked_overtrust, overtrust_total)
    quality_gate = (
        "pass"
        if expected_trust_rate >= PASS_EXPECTED_TRUST_RATE and blocked_overtrust_rate >= PASS_BLOCKED_OVERTRUST_RATE
        else "fail"
    )
    return {
        "project_id": project.project_id,
        "quality_gate": quality_gate,
        "summary": {
            "case_count": len(case_results),
            "expected_trust_total": expected_total,
            "expected_trust_hits": expected_hits,
            "expected_trust_rate": expected_trust_rate,
            "must_not_trust_total": overtrust_total,
            "blocked_overtrust_matches": blocked_overtrust,
            "blocked_overtrust_rate": blocked_overtrust_rate,
        },
        "cases": case_results,
        "thresholds": {
            "expected_trust_rate": PASS_EXPECTED_TRUST_RATE,
            "blocked_overtrust_rate": PASS_BLOCKED_OVERTRUST_RATE,
        },
    }


def evaluate_calibration_case(project: Project, case: dict[str, Any]) -> dict[str, Any]:
    query = str(case.get("query") or "").strip()
    if not query:
        raise SystemExit("calibration eval case query is required")
    context = limited_context(project, query)
    expected = list_specs(case.get("expected_trust"))
    must_not_trust = list_specs(case.get("must_not_trust"))
    missed_expected = [spec for spec in expected if not match_trust_spec(context, spec)]
    unexpected_trusted = [spec for spec in must_not_trust if match_forbidden_trust_spec(context, spec)]
    return {
        "name": case.get("name") or query,
        "query": query,
        "memory_intent": context.get("memory_intent"),
        "expected_trust_total": len(expected),
        "expected_trust_hits": len(expected) - len(missed_expected),
        "must_not_trust_total": len(must_not_trust),
        "blocked_overtrust_matches": len(must_not_trust) - len(unexpected_trusted),
        "missed_expected_trust": missed_expected,
        "unexpected_trusted_matches": unexpected_trusted,
        "result_counts": {
            key: len(value)
            for key, value in context.items()
            if isinstance(value, list)
        },
    }


def match_trust_spec(context: dict[str, Any], spec: dict[str, Any]) -> bool:
    return any(candidate_trust_matches(item, spec) for item in matching_candidates(context, spec))


def match_forbidden_trust_spec(context: dict[str, Any], spec: dict[str, Any]) -> bool:
    return any(candidate_forbidden_trust_matches(item, spec) for item in matching_candidates(context, spec))


def matching_candidates(context: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    result_type = str(spec.get("type") or "")
    if not result_type:
        return []
    values = context.get(result_type)
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict) and candidate_matches(item, spec)]


def candidate_trust_matches(item: dict[str, Any], spec: dict[str, Any]) -> bool:
    expected_level = spec.get("trust_level")
    if expected_level is not None and item.get("trust_level") != expected_level:
        return False
    min_score = spec.get("min_trust_score")
    if min_score is not None and float(item.get("trust_score") or 0.0) < float(min_score):
        return False
    return True


def candidate_forbidden_trust_matches(item: dict[str, Any], spec: dict[str, Any]) -> bool:
    levels = spec.get("trust_levels")
    if levels is None and spec.get("trust_level") is not None:
        levels = [spec.get("trust_level")]
    if isinstance(levels, list) and item.get("trust_level") in levels:
        return True
    min_score = spec.get("min_trust_score")
    return min_score is not None and float(item.get("trust_score") or 0.0) >= float(min_score)
