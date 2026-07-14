# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from .design_protocol import load_json_object, string_list, string_value
from .text import unique_list


MAX_REPORTS = 20
MAX_REPORT_BYTES = 5_000_000
MAX_TESTS = 100
MAX_SUMMARY_LENGTH = 300
MAX_VERIFY_REFS = 20


def load_test_evidence(
    path: str | None,
    legacy_commands: list[str] | None,
    report_paths: list[str] | None = None,
) -> dict[str, Any]:
    legacy = unique_list(legacy_commands or [])
    normalized = load_structured_evidence(path) if path else []
    reports = unique_list(report_paths or [])
    if len(reports) > MAX_REPORTS:
        raise SystemExit(f"test reports must contain at most {MAX_REPORTS} paths")
    report_tests = [test for report in reports for test in load_test_report(report)]
    normalized.extend(report_tests)
    normalized.extend(legacy_test(command) for command in legacy)
    if len(normalized) > MAX_TESTS:
        raise SystemExit(f"merged test evidence must contain at most {MAX_TESTS} tests")
    return {
        "schema_version": "test-evidence/v1",
        "tests": dedupe_tests(normalized),
        "source": evidence_source(bool(path), bool(reports), bool(legacy)),
    }


def load_structured_evidence(path: str) -> list[dict[str, Any]]:
    value = load_json_object(path, "test evidence")
    if value.get("schema_version") != "test-evidence/v1":
        raise SystemExit("unsupported test evidence schema")
    tests = value.get("tests")
    if not isinstance(tests, list) or len(tests) > MAX_TESTS:
        raise SystemExit(f"test evidence tests must be a list of at most {MAX_TESTS} items")
    return [normalize_test(item, index) for index, item in enumerate(tests)]


def load_test_report(path: str) -> list[dict[str, Any]]:
    report = Path(path)
    try:
        raw = report.read_bytes()
        if len(raw) > MAX_REPORT_BYTES:
            raise SystemExit(f"test report {path} exceeds {MAX_REPORT_BYTES} bytes")
        if report.suffix.lower() == ".xml":
            return load_junit(raw, path)
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ElementTree.ParseError) as exc:
        raise SystemExit(f"invalid test report {path}: {exc}") from exc
    return load_json_report(value, path)


def load_junit(raw: bytes, path: str) -> list[dict[str, Any]]:
    root = ElementTree.fromstring(raw)
    tests = []
    for case in (item for item in root.iter() if local_name(item) == "testcase"):
        name = case.get("name") or "unnamed"
        command = ".".join(item for item in (case.get("classname"), name) if item)
        failure = first_child(case, "failure")
        error = first_child(case, "error")
        skipped_element = first_child(case, "skipped")
        failed = failure is not None or error is not None
        skipped = skipped_element is not None
        status = "failed" if failed else "skipped" if skipped else "passed"
        details = next(
            (item for item in (failure, error, skipped_element) if item is not None),
            None,
        )
        tests.append(report_test(command, status, summary_text(details), junit_refs(case, command)))
        if len(tests) > MAX_TESTS:
            raise SystemExit(f"test report {path} exceeds {MAX_TESTS} tests")
    return tests


def junit_refs(case: ElementTree.Element, command: str) -> list[str]:
    refs = [command]
    for prop in (item for item in case.iter() if local_name(item) == "property"):
        if prop.get("name") == "verifies":
            refs.extend(item.strip() for item in (prop.get("value") or "").split(",") if item.strip())
    return unique_list(refs)[:MAX_VERIFY_REFS]


def local_name(element: ElementTree.Element) -> str:
    return str(element.tag).rsplit("}", 1)[-1]


def first_child(element: ElementTree.Element, name: str) -> ElementTree.Element | None:
    return next((item for item in element if local_name(item) == name), None)


def load_json_report(value: Any, path: str) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        raise SystemExit(f"test report {path} must be an object")
    if value.get("schema_version") == "test-report/v1":
        tests = value.get("tests", [])
        validate_report_tests(tests, path)
        return [normalize_test(item, index) for index, item in enumerate(tests)]
    if isinstance(value.get("tests"), list):
        validate_report_tests(value["tests"], path)
        return [pytest_test(item, index, path) for index, item in enumerate(value["tests"])]
    if isinstance(value.get("testResults"), list):
        return jest_tests(value["testResults"], path)
    raise SystemExit(f"unsupported test report schema: {path}")


def pytest_test(value: Any, index: int, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"test report {path} tests[{index}] must be an object")
    command = str(value.get("nodeid") or value.get("name") or f"test-{index}")
    status = normalize_report_status(value.get("outcome") or value.get("status"))
    summary = value.get("longrepr") or value.get("summary") or ""
    return report_test(command, status, summary, [command])


def jest_tests(results: list[Any], path: str) -> list[dict[str, Any]]:
    tests = []
    for result_index, result in enumerate(results):
        if not isinstance(result, dict):
            raise SystemExit(f"test report {path} testResults[{result_index}] must be an object")
        assertions = result.get("assertionResults", [])
        if not isinstance(assertions, list):
            raise SystemExit(f"test report {path} assertionResults must be a list")
        for index, assertion in enumerate(assertions):
            if not isinstance(assertion, dict):
                raise SystemExit(f"test report {path} assertionResults[{index}] must be an object")
            command = str(assertion.get("fullName") or assertion.get("title") or f"test-{index}")
            status = normalize_report_status(assertion.get("status"))
            messages = assertion.get("failureMessages", [])
            summary = "\n".join(str(item) for item in messages) if isinstance(messages, list) else ""
            tests.append(report_test(command, status, summary, [command]))
            if len(tests) > MAX_TESTS:
                raise SystemExit(f"test report {path} exceeds {MAX_TESTS} tests")
    return tests


def validate_report_tests(tests: Any, path: str) -> None:
    if not isinstance(tests, list) or len(tests) > MAX_TESTS:
        raise SystemExit(f"test report {path} tests must be a list of at most {MAX_TESTS} items")


def normalize_report_status(value: Any) -> str:
    status = str(value or "failed").lower()
    if status in {"passed", "pass"}:
        return "passed"
    if status in {"skipped", "skip", "pending", "todo", "disabled"}:
        return "skipped"
    return "failed"


def report_test(command: str, status: str, summary: Any, verifies: list[str]) -> dict[str, Any]:
    return {
        "command": command[:500],
        "status": status,
        "exit_code": 0 if status in {"passed", "skipped"} else 1,
        "summary": str(summary or "")[:MAX_SUMMARY_LENGTH],
        "verifies": unique_list(verifies)[:MAX_VERIFY_REFS],
    }


def summary_text(element: ElementTree.Element | None) -> str:
    if element is None:
        return ""
    return (element.get("message") or element.text or "").strip()


def evidence_source(structured: bool, reports: bool, legacy: bool) -> str:
    if structured and reports:
        return "structured_and_reports"
    if structured:
        return "structured"
    if reports:
        return "reports"
    return "legacy_commands" if legacy else "none"


def dedupe_tests(tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for test in tests:
        key = (test["command"], test["status"], test["exit_code"])
        if key not in seen:
            seen.add(key)
            result.append(test)
    return result


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
        "summary": string_value(value.get("summary", ""), f"test evidence tests[{index}].summary", allow_empty=True)[:MAX_SUMMARY_LENGTH],
        "verifies": string_list(value.get("verifies", []), f"test evidence tests[{index}].verifies")[:MAX_VERIFY_REFS],
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
