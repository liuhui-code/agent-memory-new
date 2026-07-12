# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .graph_quality import build_graph_signal_quality
from .models import Project
from .records import output
from .storage import ensure_initialized, resolve_project


DEFAULT_MIN_COVERAGE_SCORE = 0.6
DEFAULT_MAX_REPAIR_TARGETS = 10


def eval_graph_signal_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    cases = load_graph_signal_cases(Path(args.cases))
    data = evaluate_graph_signal_cases(project, cases)
    output(data, args.json)


def load_graph_signal_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"graph signal eval cases file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid graph signal cases JSON: {exc}") from exc
    if not isinstance(data, list):
        raise SystemExit("graph signal cases JSON must be a list")
    return [case for case in data if isinstance(case, dict)]


def evaluate_graph_signal_cases(project: Project, cases: list[dict[str, Any]]) -> dict[str, Any]:
    signal_quality = build_graph_signal_quality(project)
    case_results = [evaluate_graph_signal_case(case, signal_quality) for case in cases]
    passed = sum(1 for result in case_results if result["quality_gate"] == "pass")
    failed = len(case_results) - passed
    return {
        "project_id": project.project_id,
        "quality_gate": "pass" if failed == 0 else "fail",
        "summary": {
            "case_count": len(case_results),
            "passed_cases": passed,
            "failed_cases": failed,
            "coverage_score": (signal_quality.get("coverage_scorecard") or {}).get("coverage_score"),
            "coverage_status": (signal_quality.get("coverage_scorecard") or {}).get("coverage_status"),
            "repair_target_count": len(signal_quality.get("top_repair_targets") or []),
        },
        "cases": case_results,
        "graph_signal_quality": signal_quality,
        "thresholds": {
            "default_min_coverage_score": DEFAULT_MIN_COVERAGE_SCORE,
            "default_max_repair_targets": DEFAULT_MAX_REPAIR_TARGETS,
        },
    }


def evaluate_graph_signal_case(case: dict[str, Any], signal_quality: dict[str, Any]) -> dict[str, Any]:
    scorecard = signal_quality.get("coverage_scorecard") or {}
    min_score = float(case.get("min_coverage_score", DEFAULT_MIN_COVERAGE_SCORE))
    max_targets = int(case.get("max_repair_targets", DEFAULT_MAX_REPAIR_TARGETS))
    expected_statuses = [str(item) for item in case.get("allowed_coverage_statuses") or [] if str(item).strip()]
    required_targets = list_specs(case.get("required_repair_targets"))
    missing_targets = [spec for spec in required_targets if not repair_target_matches(signal_quality, spec)]
    coverage_score = float(scorecard.get("coverage_score") or 0.0)
    coverage_status = str(scorecard.get("coverage_status") or "")
    repair_target_count = len(signal_quality.get("top_repair_targets") or [])
    status_ok = not expected_statuses or coverage_status in expected_statuses
    passed = (
        coverage_score >= min_score
        and repair_target_count <= max_targets
        and status_ok
        and not missing_targets
    )
    return {
        "name": case.get("name") or "graph-signal-case",
        "quality_gate": "pass" if passed else "fail",
        "coverage_score": coverage_score,
        "coverage_status": coverage_status,
        "min_coverage_score": min_score,
        "allowed_coverage_statuses": expected_statuses,
        "repair_target_count": repair_target_count,
        "max_repair_targets": max_targets,
        "required_repair_target_count": len(required_targets),
        "missing_required_repair_targets": missing_targets,
    }


def list_specs(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if not isinstance(value, list):
        raise SystemExit("required_repair_targets must be a list")
    return [item for item in value if isinstance(item, dict)]


def repair_target_matches(signal_quality: dict[str, Any], spec: dict[str, Any]) -> bool:
    targets = signal_quality.get("top_repair_targets") or []
    for target in targets:
        if not isinstance(target, dict):
            continue
        if spec.get("target_type") and target.get("target_type") != spec.get("target_type"):
            continue
        text = str(spec.get("text") or "").strip().lower()
        if text:
            haystack = json.dumps(target, ensure_ascii=False, sort_keys=True).lower()
            if text not in haystack:
                continue
        return True
    return False
