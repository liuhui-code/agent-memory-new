# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .agent_benchmark_cases import eligible_cases, load_case_pack
from .agent_benchmark_eval import evaluate_agent_benchmark
from .agent_benchmark_protocol import RESPONSES_SCHEMA, load_observations, run_benchmark_agent
from .benchmark_case_seal import case_pack_seal_audit
from .benchmark_failure_analysis import analyze_agent_failures
from .records import output
from .storage import ensure_initialized, now_iso, resolve_project


BENCHMARK_HISTORY_LIMIT = 100


def eval_agent_benchmark_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    pack = load_case_pack(Path(args.cases).expanduser())
    cases = eligible_cases(pack, bool(args.allow_drafts))
    cases = select_cases(cases, list(args.case_id or []))
    cases = cases[: max(1, int(args.limit))]
    if not cases:
        raise SystemExit("no eligible benchmark cases; review drafts or pass --allow-drafts")
    if bool(args.runner) == bool(args.responses):
        raise SystemExit("provide exactly one of --runner or --responses")
    if args.responses:
        observations = load_observations(Path(args.responses).expanduser())
    else:
        trials = bounded_trials(args.trials)
        source = Path(args.source).expanduser().resolve() if args.source else Path(pack["project_path"]).resolve()
        if not source.is_dir():
            raise SystemExit(f"benchmark source directory not found: {source}")
        observations = run_cases(
            source,
            cases,
            args.runner,
            int(args.runner_timeout),
            not bool(args.skip_memory_prepare),
            trials,
        )
    selected_ids = {case["id"] for case in cases}
    observations = [item for item in observations if item["case_id"] in selected_ids]
    result = evaluate_agent_benchmark(pack, cases, observations)
    result["failure_analysis"] = analyze_agent_failures(result)
    result["case_seal"] = case_pack_seal_audit(pack)
    result.update({
        "project_id": project.project_id,
        "project_path": str(project.root),
        "case_file": str(Path(args.cases).expanduser()),
        "runner_mode": "external" if args.runner else "recorded_responses",
        "selected_case_ids": [case["id"] for case in cases],
        "requested_trials": (
            bounded_trials(args.trials)
            if args.runner else int(result["summary"].get("trial_count") or 1)
        ),
        "runner_configuration": runner_configuration(observations),
    })
    if args.output_responses:
        write_responses(Path(args.output_responses).expanduser(), observations)
    persist_benchmark_result(project, result)
    output(result, args.json)
    if args.fail_on_fail and result["quality_gate"] == "fail":
        raise SystemExit(1)
    if args.fail_on_efficiency_fail and result["efficiency_gate"] == "fail":
        raise SystemExit(1)


def select_cases(cases: list[dict[str, Any]], case_ids: list[str]) -> list[dict[str, Any]]:
    requested = list(dict.fromkeys(item.strip() for item in case_ids if item.strip()))
    if not requested:
        return cases
    by_id = {case["id"]: case for case in cases}
    missing = [case_id for case_id in requested if case_id not in by_id]
    if missing:
        raise SystemExit(f"requested benchmark cases are not eligible: {', '.join(missing)}")
    return [by_id[case_id] for case_id in requested]


def bounded_trials(value: Any) -> int:
    trials = 1 if value is None else int(value)
    if trials < 1 or trials > 10:
        raise SystemExit("--trials must be between 1 and 10")
    return trials


def runner_configuration(observations: list[dict[str, Any]]) -> dict[str, Any]:
    values = [
        item.get("runner_metadata")
        for item in observations
        if isinstance(item.get("runner_metadata"), dict)
    ]
    normalized = {
        json.dumps(value, ensure_ascii=False, sort_keys=True)
        for value in values
    }
    return {
        "reported": len(values) == len(observations) and bool(observations),
        "consistent": len(normalized) == 1 and len(values) == len(observations),
        "value": values[0] if len(normalized) == 1 and values else {},
    }


def run_cases(
    source: Path,
    cases: list[dict[str, Any]],
    runner: str,
    timeout: int,
    prepare_memory: bool,
    trials: int = 1,
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for case in cases:
        for trial_index in range(1, trials + 1):
            for variant in ("baseline", "memory"):
                observations.append(
                    run_benchmark_agent(
                        source, case, variant, runner, timeout, prepare_memory, trial_index
                    )
                )
    return observations


def write_responses(path: Path, observations: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": RESPONSES_SCHEMA,
        "generated_at": now_iso(),
        "observations": observations,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def persist_benchmark_result(project: Any, result: dict[str, Any]) -> None:
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    compact = {
        key: result.get(key)
        for key in (
            "schema_version", "status", "quality_gate", "efficiency_gate",
            "promotion_gate", "summary", "metrics", "efficiency_metrics",
            "efficiency_gate_checks", "efficiency_limits",
            "context_uplift", "gate_checks", "case_file", "runner_mode",
            "selected_case_ids", "runner_configuration",
            "requested_trials", "failure_analysis", "case_seal",
        )
    }
    compact["recorded_at"] = now_iso()
    snapshot = project.runtime_dir / "last_agent_benchmark.json"
    history = project.runtime_dir / "agent_benchmark_history.jsonl"
    snapshot.write_text(json.dumps(compact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(compact, ensure_ascii=False, sort_keys=True) + "\n")
    trim_history(history)


def trim_history(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    if len(lines) > BENCHMARK_HISTORY_LIMIT:
        path.write_text("\n".join(lines[-BENCHMARK_HISTORY_LIMIT:]) + "\n", encoding="utf-8")
