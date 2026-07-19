# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from .agent_benchmark_cases import eligible_cases, load_case_pack
from .benchmark_context_setup import apply_context_setup
from .benchmark_memory import prepare_isolated_memory
from .benchmark_workspace import materialized_workspace
from .context_capability_cases import expand_context_cases
from .context_capability_eval import OBSERVATION_SCHEMA, evaluate_context_capability
from .benchmark_case_seal import case_pack_seal_audit
from .benchmark_failure_analysis import analyze_context_failures
from .performance_scoring import estimate_payload_tokens
from .records import output
from .storage import ensure_initialized, now_iso, resolve_project


MAX_CONTEXT_BYTES = 1_000_000
HISTORY_LIMIT = 100


def eval_context_capability_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    case_path = Path(args.cases).expanduser()
    pack = load_case_pack(case_path)
    cases = eligible_cases(pack, bool(args.allow_drafts))
    cases = select_cases(cases, list(args.case_id or []))
    scenario_cases = limit_scenario_cases(cases, args.limit)
    if not scenario_cases:
        raise SystemExit("no eligible context capability cases")
    unsupported = [
        case["id"] for case in scenario_cases if case["task_type"] != "diagnosis"
    ]
    if unsupported:
        raise SystemExit(
            "context capability currently requires diagnosis cases: " + ", ".join(unsupported)
        )
    source = (
        Path(args.source).expanduser().resolve()
        if args.source else Path(pack["project_path"]).expanduser().resolve()
    )
    if not source.is_dir():
        raise SystemExit(f"context capability source directory not found: {source}")
    cases = expand_context_cases(scenario_cases)
    observations = collect_context_capabilities(source, cases, int(args.runner_timeout))
    result = evaluate_context_capability(cases, observations)
    result["failure_analysis"] = analyze_context_failures(result)
    result["case_seal"] = case_pack_seal_audit(pack)
    result.update({
        "project_id": project.project_id,
        "project_path": str(project.root),
        "case_file": str(case_path),
        "selected_scenario_ids": [case["id"] for case in scenario_cases],
        "selected_case_ids": [case["id"] for case in cases],
        "source_project": str(source),
        "recorded_at": now_iso(),
    })
    persist_context_capability(project, result)
    output(result, args.json)
    if args.fail_on_fail and result["system_context_gate"] == "fail":
        raise SystemExit(1)


def limit_scenario_cases(
    cases: list[dict[str, Any]],
    limit: Optional[int],
) -> list[dict[str, Any]]:
    if limit is None:
        return cases
    return cases[: max(1, int(limit))]


def collect_context_capabilities(
    source: Path,
    cases: list[dict[str, Any]],
    timeout: int,
) -> list[dict[str, Any]]:
    return [collect_context_capability(source, case, timeout) for case in cases]


def collect_context_capability(
    source: Path,
    case: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    with materialized_workspace(source, case) as workspace:
        started = time.monotonic()
        memory = prepare_isolated_memory(
            workspace,
            workspace.parent / "memory-home",
            timeout,
            case["task_type"],
        )
        fixture_counts = apply_context_setup(memory, case.get("context_setup"), timeout)
        prepare_ms = elapsed_ms(started)
        query_started = time.monotonic()
        context = run_context_query(
            memory.get("query_command"),
            str(case.get("task", {}).get("description") or ""),
            workspace,
            timeout,
        )
        query_ms = elapsed_ms(query_started)
        return {
            **summarize_context(case["id"], context, prepare_ms, query_ms),
            "fixture_counts": fixture_counts,
        }


def run_context_query(
    command: Any,
    query: str,
    workspace: Path,
    timeout: int,
) -> dict[str, Any]:
    if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
        raise SystemExit("context capability query command must be a string list")
    arguments = [
        query if item in {"<task-description>", "<task-description-or-agent-extracted-term>"}
        else item
        for item in command
    ]
    environment = os.environ.copy()
    environment.pop("AGENT_MEMORY_HOME", None)
    try:
        process = subprocess.run(
            arguments,
            text=True,
            capture_output=True,
            cwd=workspace,
            env=environment,
            timeout=max(30, timeout),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"context capability query failed: {exc}") from exc
    if process.returncode != 0:
        message = process.stderr.strip()[:1000] or process.stdout.strip()[:1000]
        raise SystemExit(f"context capability query failed: {message}")
    if len(process.stdout.encode("utf-8")) > MAX_CONTEXT_BYTES:
        raise SystemExit("context capability query output exceeds 1 MB")
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit("context capability query returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise SystemExit("context capability query must return a JSON object")
    return value


def summarize_context(
    case_id: str,
    context: dict[str, Any],
    prepare_ms: int,
    query_ms: int,
) -> dict[str, Any]:
    handoff = context.get("query_handoff")
    handoff = handoff if isinstance(handoff, dict) else {}
    anchors = records(handoff.get("code_anchors"))
    paths = handoff.get("path_context")
    paths = paths if isinstance(paths, dict) else {}
    path_candidates = records(paths.get("path_candidates"))
    main_experience = records(handoff.get("experience_refs"))
    guard_experience = [
        *records(context.get("correction_guards")),
        *records(context.get("semantic_patch_notes")),
        *records(context.get("blocked_memory_notes")),
    ]
    budget = context.get("output_budget")
    budget = budget if isinstance(budget, dict) else {}
    log_anchors = records(handoff.get("log_anchors"))
    return {
        "schema_version": OBSERVATION_SCHEMA,
        "case_id": case_id,
        "context_schema_version": str(context.get("schema_version") or ""),
        "anchor_paths": unique_paths(item.get("file_path") for item in anchors),
        "ordered_anchor_paths": unique_paths(item.get("file_path") for item in anchors),
        "anchor_count": len(anchors),
        "primary_anchor_paths": unique_paths(
            item.get("file_path") for item in anchors if item.get("role") == "primary"
        ),
        "excerpt_paths": unique_paths(
            item.get("file_path") for item in anchors if records(item.get("source_excerpts"))
        ),
        "excerpt_spans": excerpt_spans(anchors),
        "log_anchor_paths": unique_paths(
            item.get("file_path") for item in log_anchors
        ),
        "log_anchor_count": len(log_anchors),
        "log_evidence_texts": [
            " ".join(
                str(item.get(key) or "").strip()
                for key in (
                    "message_template", "logger", "business_event",
                    "trigger_stage", "function", "process_hint",
                )
                if str(item.get(key) or "").strip()
            )
            for item in log_anchors
        ],
        "log_keywords": string_values(handoff.get("log_keywords")),
        "experience_types": unique_values(
            item.get("experience_type") for item in [*main_experience, *guard_experience]
        ),
        "main_experience_texts": experience_texts(main_experience),
        "guard_experience_texts": experience_texts(guard_experience),
        "experience_ref_count": len(main_experience) + len(guard_experience),
        "main_experience_ref_count": len(main_experience),
        "guard_experience_ref_count": len(guard_experience),
        "semantic_ref_count": len(records(handoff.get("semantic_refs"))),
        "path_files": path_files(path_candidates),
        "path_relations": path_relations(path_candidates),
        "path_candidate_count": len(path_candidates),
        "relation_hint_count": len(records(handoff.get("relation_hints"))),
        "evidence_gaps": string_values(context.get("evidence_gaps")),
        "context_token_estimate": positive_int(
            budget.get("estimated_tokens"), estimate_payload_tokens(context)
        ),
        "memory_prepare_ms": prepare_ms,
        "query_elapsed_ms": query_ms,
    }


def path_files(candidates: list[dict[str, Any]]) -> list[str]:
    values: list[Any] = []
    for candidate in candidates:
        for endpoint in (candidate.get("entry"), candidate.get("emitter")):
            if isinstance(endpoint, dict):
                values.append(endpoint.get("file_path"))
        values.extend(item.get("file_path") for item in records(candidate.get("nodes")))
    return unique_paths(values)


def excerpt_spans(anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "file_path": str(anchor.get("file_path") or ""),
            **{
                key: excerpt[key]
                for key in ("symbol", "start_line", "end_line", "selection_reason", "truncated")
                if excerpt.get(key) not in (None, "")
            },
        }
        for anchor in anchors
        for excerpt in records(anchor.get("source_excerpts"))
        if anchor.get("file_path")
    ]


def path_relations(candidates: list[dict[str, Any]]) -> list[str]:
    return unique_values(
        relation.get("relation")
        for candidate in candidates
        for relation in records(candidate.get("relations"))
    )


def experience_texts(values: list[dict[str, Any]]) -> list[str]:
    fields = (
        "task", "problem", "summary", "lesson", "trigger_condition",
        "repair_action", "anti_pattern", "fact", "reason",
    )
    return [
        " ".join(
            str(item.get(field) or "").strip()
            for field in fields
            if str(item.get(field) or "").strip()
        )
        for item in values
    ]


def select_cases(cases: list[dict[str, Any]], case_ids: list[str]) -> list[dict[str, Any]]:
    requested = list(dict.fromkeys(item.strip() for item in case_ids if item.strip()))
    if not requested:
        return cases
    by_id = {case["id"]: case for case in cases}
    missing = [case_id for case_id in requested if case_id not in by_id]
    if missing:
        raise SystemExit(f"requested context cases are not eligible: {', '.join(missing)}")
    return [by_id[case_id] for case_id in requested]


def persist_context_capability(project: Any, result: dict[str, Any]) -> None:
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    snapshot = project.runtime_dir / "last_context_capability.json"
    history = project.runtime_dir / "context_capability_history.jsonl"
    snapshot.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    trim_history(history)


def trim_history(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    if len(lines) > HISTORY_LIMIT:
        path.write_text("\n".join(lines[-HISTORY_LIMIT:]) + "\n", encoding="utf-8")


def records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def string_values(value: Any) -> list[str]:
    return unique_values(value if isinstance(value, list) else [])


def unique_paths(values: Any) -> list[str]:
    return unique_values(values)


def unique_values(values: Any) -> list[str]:
    return list(dict.fromkeys(str(item).strip() for item in values if str(item or "").strip()))


def positive_int(value: Any, fallback: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return max(0, fallback)
    return result if result > 0 else max(0, fallback)


def elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))
