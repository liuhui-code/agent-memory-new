# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .design_protocol import load_json_object, string_list, string_value
from .text import unique_list


def load_test_evidence(path: str | None, legacy_commands: list[str] | None) -> dict[str, Any]:
    legacy = unique_list(legacy_commands or [])
    if not path:
        return {
            "schema_version": "test-evidence/v1",
            "tests": [legacy_test(command) for command in legacy],
            "source": "legacy_commands" if legacy else "none",
        }
    value = load_json_object(path, "test evidence")
    if value.get("schema_version") != "test-evidence/v1":
        raise SystemExit("unsupported test evidence schema")
    tests = value.get("tests")
    if not isinstance(tests, list) or len(tests) > 100:
        raise SystemExit("test evidence tests must be a list of at most 100 items")
    normalized = [normalize_test(item, index) for index, item in enumerate(tests)]
    normalized.extend(legacy_test(command) for command in legacy)
    return {"schema_version": "test-evidence/v1", "tests": normalized, "source": "structured"}


def normalize_test(value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"test evidence tests[{index}] must be an object")
    status = value.get("status")
    if status not in {"passed", "failed", "skipped"}:
        raise SystemExit(f"test evidence tests[{index}].status is invalid")
    exit_code = value.get("exit_code")
    if not isinstance(exit_code, int):
        raise SystemExit(f"test evidence tests[{index}].exit_code must be an integer")
    return {
        "command": string_value(value.get("command"), f"test evidence tests[{index}].command"),
        "status": status,
        "exit_code": exit_code,
        "summary": string_value(value.get("summary", ""), f"test evidence tests[{index}].summary", allow_empty=True),
        "verifies": string_list(value.get("verifies", []), f"test evidence tests[{index}].verifies"),
    }


def legacy_test(command: str) -> dict[str, Any]:
    return {
        "command": command,
        "status": "passed",
        "exit_code": 0,
        "summary": "legacy caller reported execution",
        "verifies": [command],
    }


def verified_refs(evidence: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for test in evidence["tests"]:
        if test["status"] != "passed" or test["exit_code"] != 0:
            continue
        refs.add(test["command"])
        refs.update(test["verifies"])
    return refs


def failed_test_count(evidence: dict[str, Any]) -> int:
    return sum(1 for test in evidence["tests"] if test["status"] == "failed" or test["exit_code"] != 0)


def normalize_symbol_values(values: list[str] | None) -> list[str]:
    candidates = [
        item.strip()
        for value in values or []
        for item in value.split(",")
        if item.strip()
    ]
    seen: set[str] = set()
    result: list[str] = []
    for candidate in candidates:
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result
