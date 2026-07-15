# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .agent_benchmark_cases import eligible_cases, load_case_pack
from .agent_benchmark_eval import evaluate_agent_benchmark
from .agent_benchmark_protocol import RESPONSES_SCHEMA, load_observations, run_benchmark_agent
from .records import output
from .storage import ensure_initialized, now_iso, resolve_project


BENCHMARK_HISTORY_LIMIT = 100


def eval_agent_benchmark_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    pack = load_case_pack(Path(args.cases).expanduser())
    cases = eligible_cases(pack, bool(args.allow_drafts))
    cases = cases[: max(1, int(args.limit))]
    if not cases:
        raise SystemExit("no eligible benchmark cases; review drafts or pass --allow-drafts")
    if bool(args.runner) == bool(args.responses):
        raise SystemExit("provide exactly one of --runner or --responses")
    if args.responses:
        observations = load_observations(Path(args.responses).expanduser())
    else:
        source = Path(args.source).expanduser().resolve() if args.source else Path(pack["project_path"]).resolve()
        if not source.is_dir():
            raise SystemExit(f"benchmark source directory not found: {source}")
        observations = run_cases(
            source,
            cases,
            args.runner,
            int(args.runner_timeout),
            not bool(args.skip_memory_prepare),
        )
    selected_ids = {case["id"] for case in cases}
    observations = [item for item in observations if item["case_id"] in selected_ids]
    result = evaluate_agent_benchmark(pack, cases, observations)
    result.update({
        "project_id": project.project_id,
        "project_path": str(project.root),
        "case_file": str(Path(args.cases).expanduser()),
        "runner_mode": "external" if args.runner else "recorded_responses",
    })
    if args.output_responses:
        write_responses(Path(args.output_responses).expanduser(), observations)
    persist_benchmark_result(project, result)
    output(result, args.json)
    if args.fail_on_fail and result["quality_gate"] == "fail":
        raise SystemExit(1)


def run_cases(
    source: Path,
    cases: list[dict[str, Any]],
    runner: str,
    timeout: int,
    prepare_memory: bool,
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for case in cases:
        for variant in ("baseline", "memory"):
            observations.append(
                run_benchmark_agent(source, case, variant, runner, timeout, prepare_memory)
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
            "schema_version", "status", "quality_gate", "summary", "metrics",
            "context_uplift", "gate_checks", "case_file", "runner_mode",
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
