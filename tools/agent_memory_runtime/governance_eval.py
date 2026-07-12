# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .active_learning_queue import build_active_learning_actions, build_active_learning_queue
from .graph_quality import build_graph_signal_quality
from .memory_tiers import build_memory_tier_actions, build_memory_tiers
from .quality_scoring import build_quality_report
from .records import output
from .storage import ensure_initialized, resolve_project


PASS_EXPECTED_ACTION_RATE = 0.8
PASS_BLOCKED_BAD_ACTION_RATE = 1.0


def eval_governance_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    cases = load_governance_cases(Path(args.cases))
    actions = collect_eval_governance_actions(project)
    data = evaluate_governance_cases(project.project_id, cases, actions)
    output(data, args.json)


def load_governance_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"governance eval cases file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid governance eval cases JSON: {exc}") from exc
    if not isinstance(data, list):
        raise SystemExit("governance eval cases JSON must be a list")
    return [item for item in data if isinstance(item, dict)]


def collect_eval_governance_actions(project: Any) -> list[dict[str, Any]]:
    memory_tiers = build_memory_tiers(project)
    graph_signal_quality = build_graph_signal_quality(project)
    active_learning_queue = build_active_learning_queue(
        project,
        graph_signal_quality=graph_signal_quality,
        experience_usage={"records": []},
        quality_report=build_quality_report([], [], []),
        limit=10,
    )
    return [
        *build_memory_tier_actions(memory_tiers),
        *build_active_learning_actions(active_learning_queue),
    ]


def evaluate_governance_cases(project_id: str, cases: list[dict[str, Any]], actions: list[dict[str, Any]]) -> dict[str, Any]:
    results = [evaluate_governance_case(case, actions) for case in cases]
    expected_total = sum(item["expected_total"] for item in results)
    expected_hits = sum(item["expected_hits"] for item in results)
    bad_total = sum(item["must_not_total"] for item in results)
    bad_blocked = sum(item["blocked_bad_actions"] for item in results)
    expected_rate = ratio(expected_hits, expected_total)
    blocked_rate = ratio(bad_blocked, bad_total)
    quality_gate = "pass" if expected_rate >= PASS_EXPECTED_ACTION_RATE and blocked_rate >= PASS_BLOCKED_BAD_ACTION_RATE else "fail"
    return {
        "project_id": project_id,
        "quality_gate": quality_gate,
        "summary": {
            "case_count": len(results),
            "action_count": len(actions),
            "expected_total": expected_total,
            "expected_hits": expected_hits,
            "expected_action_hit_rate": expected_rate,
            "must_not_total": bad_total,
            "blocked_bad_actions": bad_blocked,
            "blocked_bad_action_rate": blocked_rate,
        },
        "cases": results,
        "thresholds": {
            "expected_action_hit_rate": PASS_EXPECTED_ACTION_RATE,
            "blocked_bad_action_rate": PASS_BLOCKED_BAD_ACTION_RATE,
        },
    }


def evaluate_governance_case(case: dict[str, Any], actions: list[dict[str, Any]]) -> dict[str, Any]:
    expected = list_specs(case.get("expected_actions"))
    must_not = list_specs(case.get("must_not_actions"))
    missed = [spec for spec in expected if not any(action_matches(action, spec) for action in actions)]
    unexpected = [spec for spec in must_not if any(action_matches(action, spec) for action in actions)]
    return {
        "name": case.get("name") or "governance case",
        "expected_total": len(expected),
        "expected_hits": len(expected) - len(missed),
        "must_not_total": len(must_not),
        "blocked_bad_actions": len(must_not) - len(unexpected),
        "missed_expected_actions": missed,
        "unexpected_bad_actions": unexpected,
    }


def list_specs(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if not isinstance(value, list):
        raise SystemExit("expected_actions and must_not_actions must be lists")
    return [item for item in value if isinstance(item, dict)]


def action_matches(action: dict[str, Any], spec: dict[str, Any]) -> bool:
    for key, expected_value in spec.items():
        if str(action.get(str(key)) or "") != str(expected_value):
            return False
    return True


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 3)
