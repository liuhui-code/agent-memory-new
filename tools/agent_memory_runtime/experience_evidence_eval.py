# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .models import Project
from .quality_scoring import experience_evidence_profile
from .records import output, row_dict
from .storage import connect, ensure_initialized, resolve_project


DEFAULT_MIN_PROFILE_SCORE = 0.75


def eval_experience_evidence_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    cases = load_experience_evidence_cases(Path(args.cases))
    data = evaluate_experience_evidence_cases(project, cases)
    output(data, args.json)


def load_experience_evidence_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"experience evidence eval cases file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid experience evidence cases JSON: {exc}") from exc
    if not isinstance(data, list):
        raise SystemExit("experience evidence cases JSON must be a list")
    return [case for case in data if isinstance(case, dict)]


def evaluate_experience_evidence_cases(project: Project, cases: list[dict[str, Any]]) -> dict[str, Any]:
    reflections = fetch_active_reflections(project)
    case_results = [evaluate_experience_evidence_case(case, reflections) for case in cases]
    passed = sum(1 for result in case_results if result["quality_gate"] == "pass")
    failed = len(case_results) - passed
    return {
        "project_id": project.project_id,
        "quality_gate": "pass" if failed == 0 else "fail",
        "summary": {
            "case_count": len(case_results),
            "passed_cases": passed,
            "failed_cases": failed,
            "average_profile_score": average_profile_score(case_results),
        },
        "cases": case_results,
        "thresholds": {
            "default_min_profile_score": DEFAULT_MIN_PROFILE_SCORE,
        },
    }


def fetch_active_reflections(project: Project) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM reflections
            WHERE project_id = ?
              AND COALESCE(status, 'active') = 'active'
              AND COALESCE(is_stale, 0) = 0
            ORDER BY id DESC
            LIMIT 500
            """,
            (project.project_id,),
        ).fetchall()
    return [row_dict(row) for row in rows]


def evaluate_experience_evidence_case(case: dict[str, Any], reflections: list[dict[str, Any]]) -> dict[str, Any]:
    matched = find_reflection(case, reflections)
    min_score = float(case.get("min_profile_score", DEFAULT_MIN_PROFILE_SCORE))
    required_true = [str(item) for item in case.get("required_true") or [] if str(item).strip()]
    expected_status = str(case.get("expected_verification_status") or "").strip()
    if not matched:
        return {
            "name": case.get("name") or "experience-evidence-case",
            "quality_gate": "fail",
            "matched_reflection_id": None,
            "profile_score": 0.0,
            "missing_required_true": required_true,
            "failure_reason": "reflection not found",
        }
    profile = experience_evidence_profile(matched)
    score = profile_score(profile)
    missing_required_true = [key for key in required_true if not bool(profile.get(key))]
    status_ok = not expected_status or profile.get("verification_status") == expected_status
    passed = score >= min_score and not missing_required_true and status_ok
    return {
        "name": case.get("name") or matched.get("task") or "experience-evidence-case",
        "quality_gate": "pass" if passed else "fail",
        "matched_reflection_id": matched.get("id"),
        "experience_type": matched.get("experience_type"),
        "profile_score": score,
        "min_profile_score": min_score,
        "expected_verification_status": expected_status or None,
        "verification_status": profile.get("verification_status"),
        "missing_required_true": missing_required_true,
        "experience_evidence_profile": profile,
    }


def find_reflection(case: dict[str, Any], reflections: list[dict[str, Any]]) -> dict[str, Any] | None:
    match = case.get("match") if isinstance(case.get("match"), dict) else {}
    wanted_id = int_or_none(match.get("id") if match else case.get("id"))
    text = str(match.get("text") if match else case.get("text") or "").strip().lower()
    for row in reflections:
        if wanted_id is not None and int_or_none(row.get("id")) != wanted_id:
            continue
        if text and text not in json.dumps(row, ensure_ascii=False, sort_keys=True).lower():
            continue
        return row
    return None


def profile_score(profile: dict[str, Any]) -> float:
    parts = [
        bool(profile.get("has_evidence")),
        bool(profile.get("has_applicability")),
        bool(profile.get("has_counter_evidence")),
        profile.get("verification_status") == "verified",
    ]
    return round(sum(1 for part in parts if part) / len(parts), 3)


def average_profile_score(case_results: list[dict[str, Any]]) -> float:
    if not case_results:
        return 0.0
    return round(sum(float(item.get("profile_score") or 0.0) for item in case_results) / len(case_results), 3)


def int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
