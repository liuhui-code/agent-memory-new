# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


CAUSAL_LEVELS = {"association": 0, "supported": 1, "verified": 2}


def normalize_mechanism_assertions(value: Any, label: str) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a list")
    return [normalize_span(item, f"{label}[{index}]", require_claim=False)
            for index, item in enumerate(value)]


def normalize_mechanism_evidence(value: Any, label: str) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a list")
    return [normalize_span(item, f"{label}[{index}]", require_claim=True)
            for index, item in enumerate(value)]


def score_mechanism(
    oracle: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any]:
    assertions = normalize_mechanism_assertions(
        oracle.get("mechanism_assertions"), "oracle.mechanism_assertions"
    )
    evidence = normalize_mechanism_evidence(
        observation.get("mechanism_evidence"), "mechanism_evidence"
    )
    if not assertions:
        return {
            "mechanism_evidence_eligible": False,
            "mechanism_evidence_score": None,
            "mechanism_grounded": None,
            "matched_mechanism_assertions": 0,
            "expected_mechanism_assertions": 0,
        }
    matched = sum(any(span_matches(expected, item) for item in evidence)
                  for expected in assertions)
    score = round(matched / len(assertions), 4)
    return {
        "mechanism_evidence_eligible": True,
        "mechanism_evidence_score": score,
        "mechanism_grounded": matched == len(assertions),
        "matched_mechanism_assertions": matched,
        "expected_mechanism_assertions": len(assertions),
    }


def normalize_span(value: Any, label: str, require_claim: bool) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be an object")
    path = required_text(value, "file_path", label)
    start = positive_int(value.get("start_line"), f"{label}.start_line")
    end = positive_int(value.get("end_line"), f"{label}.end_line")
    if end < start:
        raise SystemExit(f"{label}.end_line must be >= start_line")
    result = {"file_path": path, "start_line": start, "end_line": end}
    symbol = str(value.get("symbol") or "").strip()
    if symbol:
        result["symbol"] = symbol
    claim = str(value.get("claim") or "").strip()
    if require_claim and not claim:
        raise SystemExit(f"{label}.claim is required")
    if claim:
        result["claim"] = claim[:1000]
    return result


def span_matches(expected: dict[str, Any], observed: dict[str, Any]) -> bool:
    if expected["file_path"] != observed["file_path"]:
        return False
    expected_symbol = str(expected.get("symbol") or "").casefold()
    observed_symbol = str(observed.get("symbol") or "").casefold()
    if expected_symbol and expected_symbol != observed_symbol:
        return False
    return (
        observed["start_line"] <= expected["end_line"]
        and observed["end_line"] >= expected["start_line"]
    )


def causal_level_satisfies(observed: str, expected: str) -> bool:
    if not expected:
        return True
    observed_level = str(observed or "").casefold()
    expected_level = str(expected or "").casefold()
    if observed_level == "rejected" or expected_level == "rejected":
        return observed_level == expected_level
    if observed_level not in CAUSAL_LEVELS or expected_level not in CAUSAL_LEVELS:
        return observed_level == expected_level
    return CAUSAL_LEVELS[observed_level] >= CAUSAL_LEVELS[expected_level]


def required_text(value: dict[str, Any], key: str, label: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise SystemExit(f"{label}.{key} is required")
    return item.strip()


def positive_int(value: Any, label: str) -> int:
    number = int(value or 0)
    if number < 1:
        raise SystemExit(f"{label} must be positive")
    return number
