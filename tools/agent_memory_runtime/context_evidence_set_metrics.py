# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


def assess_evidence_set(
    expected_files: set[str],
    observation: dict[str, Any],
    oracle: object = None,
) -> dict[str, Any]:
    requirements = evidence_set_oracle(expected_files, oracle)
    value = observation.get("callable_evidence_set")
    evidence_set = value if isinstance(value, dict) else {}
    members = records(evidence_set.get("members"))
    member_files = {
        str(item.get("file_path") or "") for item in members if item.get("file_path")
    }
    active_member_files = {
        str(item.get("file_path") or "") for item in members
        if item.get("file_path") and not item.get("excluded_by_query")
    }
    target_scope = evidence_set.get("target_scope")
    target_scope = target_scope if isinstance(target_scope, dict) else {}
    observed_scope = str(target_scope.get("kind") or "unknown")
    expected_scope = requirements["target_scope"]
    calibration = evidence_set.get("calibration")
    calibration = calibration if isinstance(calibration, dict) else {}
    primary = str(members[0].get("file_path") or "") if members else ""
    primary_support = (
        [str(item) for item in members[0].get("support_kinds") or []]
        if members else []
    )
    expected_members = requirements["expected_member_files"]
    expected_primary = requirements["expected_primary_files"]
    allowed_states = requirements["allowed_states"]
    forbidden_hits = sorted(
        active_member_files & requirements["forbidden_member_files"]
    )
    return {
        "observed": evidence_set.get("mode") == "shadow",
        "target_scope_expected": expected_scope,
        "target_scope_observed": observed_scope,
        "target_scope_match": observed_scope == expected_scope,
        "member_recall": recall(expected_members, active_member_files),
        "primary_precision": (
            1.0 if primary and primary in expected_primary else 0.0
        ) if expected_primary else None,
        "calibration_state": str(calibration.get("state") or "unavailable"),
        "primary_support_kinds": primary_support,
        "calibration_state_match": (
            str(calibration.get("state") or "unavailable") in allowed_states
            if allowed_states else None
        ),
        "forbidden_member_hits": forbidden_hits,
        "guarded_exclusion_count": len(member_files - active_member_files),
    }


def evidence_set_profile(scored: list[dict[str, Any]]) -> dict[str, Any]:
    values = [
        item.get("evidence_set", {}) for item in scored
        if isinstance(item.get("evidence_set"), dict)
        and item["evidence_set"].get("observed")
    ]
    states = [str(item.get("calibration_state") or "unavailable") for item in values]
    return {
        "status": "informational",
        "evaluated_cases": len(scored),
        "observed_case_count": len(values),
        "target_scope_accuracy": average_booleans(values, "target_scope_match"),
        "member_recall": average_numbers(values, "member_recall"),
        "primary_precision": average_numbers(values, "primary_precision"),
        "calibration_state_accuracy": average_booleans(
            values, "calibration_state_match",
        ),
        "forbidden_member_hit_count": sum(
            len(item.get("forbidden_member_hits") or []) for item in values
        ),
        "guarded_exclusion_count": sum(
            int(item.get("guarded_exclusion_count") or 0) for item in values
        ),
        "calibration_state_counts": {
            state: states.count(state) for state in sorted(set(states))
        },
        "serving_projection_changed": False,
    }


def expected_target_scope(expected_files: set[str]) -> str:
    if len(expected_files) > 1:
        return "multiple"
    if len(expected_files) == 1:
        return "single"
    return "unknown"


def evidence_set_oracle(
    expected_files: set[str], value: object,
) -> dict[str, Any]:
    oracle = value if isinstance(value, dict) else {}
    expected_members = (
        string_set(oracle.get("expected_member_files"))
        if "expected_member_files" in oracle else set(expected_files)
    )
    expected_primary = (
        string_set(oracle.get("expected_primary_files"))
        if "expected_primary_files" in oracle else set(expected_files)
    )
    return {
        "target_scope": str(
            oracle.get("target_scope") or expected_target_scope(expected_files)
        ),
        "expected_member_files": expected_members,
        "expected_primary_files": expected_primary,
        "forbidden_member_files": string_set(oracle.get("forbidden_member_files")),
        "allowed_states": string_set(oracle.get("allowed_states")),
    }


def recall(expected: set[str], observed: set[str]) -> float | None:
    return round(len(expected & observed) / len(expected), 4) if expected else None


def average_booleans(values: list[dict[str, Any]], key: str) -> float | None:
    measured = [item.get(key) for item in values if isinstance(item.get(key), bool)]
    return round(sum(measured) / len(measured), 4) if measured else None


def average_numbers(values: list[dict[str, Any]], key: str) -> float | None:
    measured = [
        float(item[key]) for item in values
        if isinstance(item.get(key), (int, float))
    ]
    return round(sum(measured) / len(measured), 4) if measured else None


def records(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def string_set(value: object) -> set[str]:
    return {str(item) for item in value if str(item)} if isinstance(value, list) else set()
