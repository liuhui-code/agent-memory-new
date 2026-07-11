# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .log_signal_quality import build_log_signal_summary, enrich_log_signal
from .records import output
from .runtime_logs import normalize_runtime_log_line
from .storage import ensure_initialized, resolve_project


DEFAULT_MIN_GOOD_RATE = 0.5
DEFAULT_MAX_LOW_SIGNAL_RATE = 0.5


def eval_log_signal_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    cases = load_log_signal_cases(Path(args.cases))
    data = evaluate_log_signal_cases(cases)
    data["project_id"] = project.project_id
    output(data, args.json)


def load_log_signal_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"log signal eval cases file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid log signal cases JSON: {exc}") from exc
    if not isinstance(data, list):
        raise SystemExit("log signal cases JSON must be a list")
    return [case for case in data if isinstance(case, dict)]


def evaluate_log_signal_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_results = [evaluate_log_signal_case(case) for case in cases]
    event_count = sum(result["event_count"] for result in case_results)
    good_count = sum(result["good_signal_events"] for result in case_results)
    low_count = sum(result["low_signal_events"] for result in case_results)
    good_rate = ratio(good_count, event_count)
    low_rate = ratio(low_count, event_count)
    quality_gate = "pass" if all(result["quality_gate"] == "pass" for result in case_results) else "fail"
    return {
        "quality_gate": quality_gate,
        "summary": {
            "case_count": len(case_results),
            "event_count": event_count,
            "good_signal_events": good_count,
            "low_signal_events": low_count,
            "log_signal_good_rate": good_rate,
            "low_signal_event_rate": low_rate,
        },
        "cases": case_results,
        "thresholds": {
            "default_min_good_rate": DEFAULT_MIN_GOOD_RATE,
            "default_max_low_signal_rate": DEFAULT_MAX_LOW_SIGNAL_RATE,
        },
    }


def evaluate_log_signal_case(case: dict[str, Any]) -> dict[str, Any]:
    logs = case.get("logs") or []
    if not isinstance(logs, list):
        raise SystemExit("log signal case logs must be a list")
    events = [
        enrich_log_signal(normalize_runtime_log_line(str(line), index))
        for index, line in enumerate(logs, start=1)
        if str(line).strip()
    ]
    summary = build_log_signal_summary(events)
    event_count = int(summary["event_count"])
    good_count = int(summary["bands"].get("good") or 0)
    low_count = int(summary["bands"].get("poor") or 0)
    good_rate = ratio(good_count, event_count)
    low_rate = ratio(low_count, event_count)
    min_good = float(case.get("min_good_rate", DEFAULT_MIN_GOOD_RATE))
    max_low = float(case.get("max_low_signal_rate", DEFAULT_MAX_LOW_SIGNAL_RATE))
    return {
        "name": case.get("name") or "log-signal-case",
        "quality_gate": "pass" if good_rate >= min_good and low_rate <= max_low else "fail",
        "event_count": event_count,
        "good_signal_events": good_count,
        "low_signal_events": low_count,
        "log_signal_good_rate": good_rate,
        "low_signal_event_rate": low_rate,
        "min_good_rate": min_good,
        "max_low_signal_rate": max_low,
        "summary": summary,
        "events": events,
    }


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 3)
