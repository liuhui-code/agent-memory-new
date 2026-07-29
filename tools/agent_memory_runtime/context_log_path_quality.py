# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


MAX_PATH_SPECS = 20
MAX_PATH_LOCATIONS = 8


def observe_log_paths(log_anchors: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    evidence_classes = unique_strings(
        item.get("evidence_class") or "direct" for item in log_anchors
    )
    for item in log_anchors:
        locations = unique_strings(item.get("call_path_locations") or [])
        evidence_class = str(item.get("evidence_class") or "direct").strip()
        if not locations or not evidence_class.endswith("_wrapped"):
            continue
        candidates.append({
            "file_path": str(item.get("file_path") or "").strip(),
            "function": str(item.get("function") or "").strip(),
            "evidence_class": evidence_class,
            "locations": locations,
            "truncated": bool(item.get("truncated")),
        })
    return {
        "log_evidence_classes": evidence_classes,
        "log_path_candidates": candidates,
        "wrapped_log_path_count": len(candidates),
        "truncated_log_path_count": sum(item["truncated"] for item in candidates),
    }


def log_path_requirements(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "required_log_evidence_classes": string_list(
            item.get("required_log_evidence_classes"), fold=True
        ),
        "required_log_effect_paths": path_specs(
            item.get("required_log_effect_paths"), "required_log_effect_paths"
        ),
        "allowed_log_effect_paths": path_specs(
            item.get("allowed_log_effect_paths"), "allowed_log_effect_paths"
        ),
        "min_log_path_precision": optional_ratio(item.get("min_log_path_precision")),
        "max_log_path_candidates": nonnegative_int(item.get("max_log_path_candidates")),
        "require_log_truncation_signal": bool(item.get("require_log_truncation_signal")),
    }


def assess_log_path_quality(
    requirements: dict[str, Any], observation: dict[str, Any],
) -> dict[str, Any]:
    observed = records(observation.get("log_path_candidates"))
    required = records(requirements.get("required_log_effect_paths"))
    allowed = records(requirements.get("allowed_log_effect_paths"))
    evidence = set(string_list(observation.get("log_evidence_classes"), fold=True))
    missing_classes = sorted(
        set(requirements["required_log_evidence_classes"]) - evidence
    )
    missing_paths = [item for item in required if not any(path_matches(item, value) for value in observed)]
    matched_observed = sum(
        any(path_matches(item, value) for item in allowed) for value in observed
    ) if allowed else 0
    recall = ratio(len(required) - len(missing_paths), len(required), empty=1.0)
    precision = ratio(matched_observed, len(observed), empty=1.0) if allowed else None
    checks: dict[str, bool] = {}
    if requirements["required_log_evidence_classes"]:
        checks["required_log_evidence_classes_recalled"] = not missing_classes
    if required:
        checks["required_log_effect_paths_recalled"] = not missing_paths
    minimum = requirements["min_log_path_precision"]
    if minimum is not None:
        checks["minimum_log_path_precision_met"] = bool(allowed) and precision is not None and precision >= minimum
    maximum = requirements["max_log_path_candidates"]
    if maximum:
        checks["maximum_log_path_candidates_met"] = len(observed) <= maximum
    if requirements["require_log_truncation_signal"]:
        checks["log_path_truncation_reported"] = (
            nonnegative_int(observation.get("truncated_log_path_count")) > 0
        )
    return {
        "checks": checks,
        "result": {
            "log_path_recall": recall,
            "log_path_precision": precision,
            "missing_required_log_evidence_classes": missing_classes,
            "missing_required_log_effect_paths": missing_paths,
            "observed_log_path_count": len(observed),
            "truncated_log_path_count": nonnegative_int(
                observation.get("truncated_log_path_count")
            ),
        },
    }


def log_path_profile(scored: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "required_log_evidence_classes", "required_log_effect_paths",
        "allowed_log_effect_paths", "min_log_path_precision",
        "max_log_path_candidates", "require_log_truncation_signal",
    )
    evaluated = [item for item in scored if any(item["requirements"].get(key) for key in keys)]
    return {
        "status": (
            "pass" if evaluated and all(item["status"] == "pass" for item in evaluated)
            else "fail" if evaluated else "informational"
        ),
        "evaluated_cases": len(evaluated),
        "average_path_recall": average(evaluated, "log_path_recall"),
        "average_path_precision": average(evaluated, "log_path_precision"),
        "truncated_case_count": sum(item["truncated_log_path_count"] > 0 for item in evaluated),
    }


def path_specs(value: Any, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_PATH_SPECS:
        raise SystemExit(f"{label} must contain at most {MAX_PATH_SPECS} log effect paths")
    result = []
    for item in value:
        if not isinstance(item, dict):
            raise SystemExit(f"{label} log effect path must be an object")
        raw_locations = item.get("locations")
        if not isinstance(raw_locations, list) or not raw_locations or len(raw_locations) > MAX_PATH_LOCATIONS:
            raise SystemExit(
                f"{label} log effect path locations must contain 1..{MAX_PATH_LOCATIONS} items"
            )
        locations = string_list(raw_locations)
        if not locations:
            raise SystemExit(f"{label} log effect path requires non-empty locations")
        result.append({
            "evidence_class": str(item.get("evidence_class") or "").strip().casefold(),
            "locations": locations,
        })
    return result


def path_matches(expected: dict[str, Any], observed: dict[str, Any]) -> bool:
    expected_class = str(expected.get("evidence_class") or "").casefold()
    observed_class = str(observed.get("evidence_class") or "").casefold()
    if expected_class and expected_class != observed_class:
        return False
    return ordered_subsequence(
        string_list(expected.get("locations")), string_list(observed.get("locations"))
    )


def ordered_subsequence(expected: list[str], observed: list[str]) -> bool:
    cursor = iter(observed)
    return all(any(candidate == value for candidate in cursor) for value in expected)


def records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def string_list(value: Any, fold: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    items = [str(item).strip() for item in value if str(item).strip()]
    if fold:
        items = [item.casefold() for item in items]
    return list(dict.fromkeys(items))


def unique_strings(value: Any) -> list[str]:
    return string_list(list(value))


def optional_ratio(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit("min_log_path_precision must be numeric") from exc
    if not 0.0 <= result <= 1.0:
        raise SystemExit("min_log_path_precision must be between 0 and 1")
    return result


def nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def ratio(numerator: int, denominator: int, empty: float) -> float:
    return round(numerator / denominator, 4) if denominator else empty


def average(values: list[dict[str, Any]], key: str) -> float | None:
    numbers = [float(item[key]) for item in values if item.get(key) is not None]
    return round(sum(numbers) / len(numbers), 4) if numbers else None
