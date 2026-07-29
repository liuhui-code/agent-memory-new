# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import defaultdict
from typing import Any


PROFILE_KEY = "evaluation_profile"
CONTRACT_KEY = "calibration"
TARGET_DOMAIN = "native_arkts"
TARGET_LEVELS = {"file", "callable", "expression"}
ARTIFACT_ROLES = {
    "page", "service", "store", "utility", "component", "adapter", "viewmodel",
}
MECHANISM_KINDS = {
    "resource_io", "ui_state", "navigation", "platform_api", "async_control",
    "persistence", "event_binding", "error_contract",
}


def normalize_evaluation_profile(value: Any, case_id: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SystemExit(f"benchmark case {case_id} evaluation_profile must be an object")
    domain = required_choice(value, "target_domain", {TARGET_DOMAIN}, case_id)
    levels = choices(value, "target_levels", TARGET_LEVELS, case_id)
    roles = choices(value, "artifact_roles", ARTIFACT_ROLES, case_id)
    mechanisms = choices(value, "mechanism_kinds", MECHANISM_KINDS, case_id)
    return {
        "target_domain": domain,
        "target_levels": levels,
        "artifact_roles": roles,
        "mechanism_kinds": mechanisms,
    }


def normalize_calibration_contract(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SystemExit("benchmark calibration contract must be an object")
    domain = required_choice(value, "target_domain", {TARGET_DOMAIN}, "calibration")
    return {
        "target_domain": domain,
        "minimum_case_count": positive_int(value, "minimum_case_count"),
        "required_target_levels": choices(value, "required_target_levels", TARGET_LEVELS, "calibration"),
        "required_artifact_roles": choices(value, "required_artifact_roles", ARTIFACT_ROLES, "calibration"),
        "required_mechanism_kinds": choices(value, "required_mechanism_kinds", MECHANISM_KINDS, "calibration"),
    }


def calibration_contract(pack: dict[str, Any]) -> dict[str, Any] | None:
    governance = pack.get("governance") if isinstance(pack.get("governance"), dict) else {}
    return normalize_calibration_contract(governance.get(CONTRACT_KEY))


def validate_calibrated_holdout(pack: dict[str, Any]) -> None:
    contract = calibration_contract(pack)
    if contract is None:
        return
    if pack.get("suite") != "holdout":
        raise SystemExit("ArkTS calibration contract requires a holdout case pack")
    cases = pack.get("cases") if isinstance(pack.get("cases"), list) else []
    if len(cases) < contract["minimum_case_count"]:
        raise SystemExit("ArkTS calibration contract has too few cases")
    profiles = [
        normalize_evaluation_profile(case.get(PROFILE_KEY), str(case.get("id") or "<unknown>"))
        for case in cases if isinstance(case, dict)
    ]
    if not all(isinstance(profile, dict) for profile in profiles):
        raise SystemExit("ArkTS calibration holdout requires evaluation_profile on every case")
    domains = {profile["target_domain"] for profile in profiles}
    if domains != {contract["target_domain"]}:
        raise SystemExit("ArkTS calibration profiles must match the target domain")
    expected_files = {
        path for case in cases for path in case.get("oracle", {}).get("expected_files", [])
    }
    if not expected_files or not all(path.endswith(".ets") for path in expected_files):
        raise SystemExit("ArkTS calibration expected files must use the .ets suffix")
    coverage = profile_coverage([profile for profile in profiles if isinstance(profile, dict)])
    missing = contract_gaps(contract, coverage)
    if missing:
        raise SystemExit("ArkTS calibration contract missing coverage: " + ", ".join(missing))


def assess_calibration(
    cases: list[dict[str, Any]],
    scored: list[dict[str, Any]],
    contract: dict[str, Any] | None,
) -> dict[str, Any]:
    profiles = {
        str(case.get("id") or ""): case.get(PROFILE_KEY)
        for case in cases if isinstance(case.get(PROFILE_KEY), dict)
    }
    observed = [item for item in scored if str(item.get("case_id") or "") in profiles]
    coverage = profile_coverage([profiles[str(item["case_id"])] for item in observed])
    dimensions = {
        key: stratified_metrics(observed, profiles, key)
        for key in ("artifact_roles", "target_levels", "mechanism_kinds")
    }
    gaps = contract_gaps(contract, coverage) if contract else []
    domains = {
        profile["target_domain"] for profile in profiles.values()
        if isinstance(profile, dict)
    }
    return {
        "schema_version": "agent-context-calibration/v1",
        "status": "pass" if observed and not gaps else "fail" if contract else "informational",
        "target_domain": contract.get("target_domain") if contract else next(iter(domains), None),
        "profiled_case_count": len(observed),
        "coverage": coverage,
        "contract_gaps": gaps,
        "macro_metrics": macro_metrics(dimensions),
        "strata": dimensions,
        "scope": "evaluation_only_not_injected_into_agent_context",
    }


def profile_coverage(profiles: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        "target_levels": sorted({item for profile in profiles for item in profile["target_levels"]}),
        "artifact_roles": sorted({item for profile in profiles for item in profile["artifact_roles"]}),
        "mechanism_kinds": sorted({item for profile in profiles for item in profile["mechanism_kinds"]}),
    }


def contract_gaps(contract: dict[str, Any] | None, coverage: dict[str, list[str]]) -> list[str]:
    if contract is None:
        return []
    return [
        f"{key}:{item}"
        for key in ("target_levels", "artifact_roles", "mechanism_kinds")
        for item in contract[f"required_{key}"]
        if item not in coverage[key]
    ]


def stratified_metrics(
    scored: list[dict[str, Any]], profiles: dict[str, dict[str, Any]], key: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in scored:
        for label in profiles[str(item["case_id"])][key]:
            grouped[label].append(item)
    return [metric_group(label, items) for label, items in sorted(grouped.items())]


def metric_group(label: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "label": label,
        "case_count": len(items),
        "pass_rate": average(items, "status", passed=True),
        "anchor_recall": average(items, "anchor_recall"),
        "anchor_precision": average(items, "oracle_anchor_precision"),
        "source_span_recall": average(items, "source_span_recall"),
    }


def macro_metrics(dimensions: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, float | None]]:
    return {
        key: {
            metric: average(groups, metric)
            for metric in ("pass_rate", "anchor_recall", "anchor_precision", "source_span_recall")
        }
        for key, groups in dimensions.items()
    }


def average(items: list[dict[str, Any]], key: str, passed: bool = False) -> float | None:
    values = [1.0 if item.get(key) == "pass" else 0.0 for item in items] if passed else [
        item.get(key) for item in items
    ]
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    return round(sum(numeric) / len(numeric), 4) if numeric else None


def required_choice(value: dict[str, Any], key: str, allowed: set[str], owner: str) -> str:
    item = str(value.get(key) or "").strip()
    if item not in allowed:
        raise SystemExit(f"{owner} requires {key}: one of {', '.join(sorted(allowed))}")
    return item


def choices(value: dict[str, Any], key: str, allowed: set[str], owner: str) -> list[str]:
    items = value.get(key)
    if not isinstance(items, list) or not items:
        raise SystemExit(f"{owner} requires a non-empty {key} list")
    normalized = list(dict.fromkeys(str(item).strip() for item in items if str(item).strip()))
    invalid = sorted(set(normalized) - allowed)
    if invalid:
        raise SystemExit(f"{owner} has unsupported {key}: {', '.join(invalid)}")
    return normalized


def positive_int(value: dict[str, Any], key: str) -> int:
    item = int(value.get(key) or 0)
    if item < 1:
        raise SystemExit(f"calibration requires positive {key}")
    return item
