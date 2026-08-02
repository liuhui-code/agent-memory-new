# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


STAGE_ORDER = ("orientation", "focused")


def investigation_stage_profile(scored: list[dict[str, Any]]) -> dict[str, Any]:
    staged = [item for item in scored if item.get("investigation_stage") in STAGE_ORDER]
    if not staged:
        return {
            "status": "not_declared",
            "scenario_count": 0,
            "complete_scenario_count": 0,
            "stages": {},
            "scenarios": [],
        }
    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for item in staged:
        by_scenario.setdefault(str(item["scenario_id"]), []).append(item)
    scenarios = [scenario_profile(key, values) for key, values in by_scenario.items()]
    complete = sum(item["status"] == "pass" for item in scenarios)
    return {
        "status": "pass" if complete == len(scenarios) else "fail",
        "scenario_count": len(scenarios),
        "complete_scenario_count": complete,
        "stages": {
            stage: stage_profile(staged, stage)
            for stage in STAGE_ORDER
            if any(item.get("investigation_stage") == stage for item in staged)
        },
        "scenarios": scenarios,
    }


def scenario_profile(
    scenario_id: str,
    values: list[dict[str, Any]],
) -> dict[str, Any]:
    stages = {
        stage: scenario_stage_status(values, stage)
        for stage in STAGE_ORDER
    }
    declared = [value for value in stages.values() if value != "not_declared"]
    return {
        "scenario_id": scenario_id,
        "status": "pass" if declared and all(value == "pass" for value in declared) else "fail",
        "stages": stages,
    }


def scenario_stage_status(values: list[dict[str, Any]], stage: str) -> str:
    statuses = [
        item["status"] for item in values if item.get("investigation_stage") == stage
    ]
    if not statuses:
        return "not_declared"
    return "pass" if all(status == "pass" for status in statuses) else "fail"


def stage_profile(values: list[dict[str, Any]], stage: str) -> dict[str, Any]:
    selected = [item for item in values if item.get("investigation_stage") == stage]
    passed = sum(item["status"] == "pass" for item in selected)
    return {
        "status": "pass" if selected and passed == len(selected) else "fail",
        "case_count": len(selected),
        "passed_case_count": passed,
        "pass_rate": round(passed / len(selected), 4) if selected else 0.0,
        "failed_case_ids": [item["case_id"] for item in selected if item["status"] != "pass"],
    }
