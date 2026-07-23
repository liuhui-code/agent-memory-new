# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SYSTEM_CASE_FILES = {"system-capability-cases.json"}
HISTORY_READ_LIMIT = 100


def cross_project_context_summary(runtime_dir: Path) -> dict[str, Any]:
    observations = latest_real_project_observations(
        read_history(runtime_dir / "context_capability_history.jsonl")
    )
    if not observations:
        return empty_cross_project_summary()
    projects = sorted({str(item.get("source_project") or "") for item in observations})
    sealed = [item for item in observations if seal_verified(item)]
    case_count = sum(summary_count(item, "case_count") for item in observations)
    passed_count = sum(summary_count(item, "passed_case_count") for item in observations)
    failed_count = sum(summary_count(item, "failed_case_count") for item in observations)
    return {
        "status": "available" if len(projects) >= 2 else "single_project",
        "source_project_count": len(projects),
        "observation_count": len(observations),
        "sealed_observation_count": len(sealed),
        "sealed_source_project_count": len({
            str(item.get("source_project") or "") for item in sealed
        }),
        "case_observation_count": case_count,
        "passed_case_observation_count": passed_count,
        "failed_case_observation_count": failed_count,
        "gate_pass_count": sum(
            item.get("system_context_gate") == "pass" for item in observations
        ),
        "gate_fail_count": sum(
            item.get("system_context_gate") == "fail" for item in observations
        ),
        "weighted_anchor_recall": weighted_metric(
            observations, "code_locator", "anchor_recall"
        ),
        "weighted_average_context_tokens": weighted_summary_metric(
            observations, "average_context_tokens"
        ),
        "source_projects": project_summaries(observations),
        "interpretation": (
            "Historical real-project observations are immutable; unsealed runs provide "
            "coverage evidence but not sealed promotion evidence."
        ),
    }


def read_history(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-HISTORY_READ_LIMIT:]
    except OSError:
        return []
    values: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            values.append(value)
    return values


def latest_real_project_observations(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for item in observations:
        source = str(item.get("source_project") or "").strip()
        case_file = str(item.get("case_file") or "").strip()
        if not source or not case_file or Path(case_file).name in SYSTEM_CASE_FILES:
            continue
        latest[(source, case_file)] = item
    return list(latest.values())


def project_summaries(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in observations:
        grouped.setdefault(str(item.get("source_project") or ""), []).append(item)
    return [
        {
            "source_project": source,
            "observation_count": len(items),
            "case_observation_count": sum(
                summary_count(item, "case_count") for item in items
            ),
            "gate_pass_count": sum(
                item.get("system_context_gate") == "pass" for item in items
            ),
            "gate_fail_count": sum(
                item.get("system_context_gate") == "fail" for item in items
            ),
            "sealed_observation_count": sum(seal_verified(item) for item in items),
        }
        for source, items in sorted(grouped.items())
    ]


def summary_count(item: dict[str, Any], key: str) -> int:
    summary = item.get("summary") if isinstance(item.get("summary"), dict) else {}
    return int(summary.get(key) or 0)


def weighted_metric(
    observations: list[dict[str, Any]],
    profile_name: str,
    metric_name: str,
) -> float | None:
    weighted = 0.0
    total = 0
    for item in observations:
        profile = item.get("capability_profile")
        profile = profile if isinstance(profile, dict) else {}
        section = profile.get(profile_name)
        section = section if isinstance(section, dict) else {}
        value = section.get(metric_name)
        weight = int(section.get("evaluated_cases") or summary_count(item, "case_count"))
        if isinstance(value, (int, float)) and weight > 0:
            weighted += float(value) * weight
            total += weight
    return round(weighted / total, 4) if total else None


def weighted_summary_metric(
    observations: list[dict[str, Any]],
    metric_name: str,
) -> float | None:
    weighted = 0.0
    total = 0
    for item in observations:
        summary = item.get("summary") if isinstance(item.get("summary"), dict) else {}
        value = summary.get(metric_name)
        weight = summary_count(item, "case_count")
        if isinstance(value, (int, float)) and weight > 0:
            weighted += float(value) * weight
            total += weight
    return round(weighted / total, 4) if total else None


def seal_verified(item: dict[str, Any]) -> bool:
    seal = item.get("case_seal") if isinstance(item.get("case_seal"), dict) else {}
    return seal.get("status") == "verified"


def empty_cross_project_summary() -> dict[str, Any]:
    return {
        "status": "missing",
        "source_project_count": 0,
        "observation_count": 0,
        "sealed_observation_count": 0,
        "sealed_source_project_count": 0,
        "case_observation_count": 0,
        "passed_case_observation_count": 0,
        "failed_case_observation_count": 0,
        "gate_pass_count": 0,
        "gate_fail_count": 0,
        "weighted_anchor_recall": None,
        "weighted_average_context_tokens": None,
        "source_projects": [],
        "interpretation": "No real-project Context observations are available.",
    }
