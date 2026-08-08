# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .agent_benchmark_cases import public_case
from .benchmark_context_setup import apply_context_setup, context_setup_audit
from .benchmark_memory import prepare_isolated_memory
from .paired_replay import prepare_replay_memory
from .benchmark_workspace import materialized_workspace
from .agent_benchmark_schedule import normalize_execution_order
from .agent_benchmark_mechanism import normalize_mechanism_evidence
from .source_exploration import exploration_metrics_reported
from .agent_benchmark_treatment import SELECTIVE_TREATMENT_MODE


REQUEST_SCHEMA = "agent-benchmark-request/v1"
RESPONSE_SCHEMA = "agent-benchmark-response/v1"
RESPONSES_SCHEMA = "agent-benchmark-responses/v1"
MAX_OUTPUT_BYTES = 1_000_000
FORBIDDEN_REASONING_FIELDS = {"thought", "thoughts", "reasoning", "chain_of_thought", "cot"}
FORBIDDEN_MEMORY_TRACE_FIELDS = {
    "memory_query_terms", "memory_query_text", "memory_query_outputs", "memory_tool_output",
}


def run_benchmark_agent(
    root: Path,
    case: dict[str, Any],
    variant: str,
    runner: str,
    timeout: int,
    prepare_memory: bool = True,
    trial_index: int = 1,
    execution_order: dict[str, Any] | None = None,
    treatment_mode: str = "preloaded-context",
    replay_package: dict[str, Any] | None = None,
) -> dict[str, Any]:
    executable = resolve_runner(runner)
    with materialized_workspace(root, case) as workspace:
        setup = case.get("context_setup")
        setup_audit = context_setup_audit(setup)
        request = {
            "schema_version": REQUEST_SCHEMA,
            "case_id": case["id"],
            "variant": variant,
            "trial_index": trial_index,
            "treatment_mode": treatment_mode,
            **({"execution_order": execution_order} if execution_order else {}),
            "workspace": str(workspace),
            "case": public_case(case),
            "instructions": runner_instructions(variant, treatment_mode),
            "response_schema": response_template(case["id"], variant, trial_index),
        }
        if variant == "memory" and prepare_memory:
            memory_home = (
                workspace / ".agent-memory-benchmark"
                if treatment_mode == SELECTIVE_TREATMENT_MODE
                else workspace.parent / "memory-home"
            )
            memory = (
                prepare_replay_memory(workspace, memory_home, replay_package, case["task_type"])
                if replay_package else prepare_isolated_memory(
                    workspace, memory_home, timeout, case["task_type"],
                )
            )
            apply_context_setup(memory, setup, timeout)
            request["memory_access"] = memory
        elif variant == "memory" and setup_audit["reflection_count"]:
            raise SystemExit("context_setup requires benchmark-managed memory preparation")
        try:
            environment = os.environ.copy()
            environment.pop("AGENT_MEMORY_HOME", None)
            environment["AGENT_BENCHMARK_VARIANT"] = variant
            process = subprocess.run(
                [executable],
                input=json.dumps(request, ensure_ascii=False),
                text=True,
                capture_output=True,
                cwd=workspace,
                env=environment,
                timeout=max(5, timeout),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SystemExit(f"benchmark runner timed out for {case['id']}:{variant}") from exc
    if process.returncode != 0:
        message = process.stderr.strip()[:1000] or f"exit {process.returncode}"
        raise SystemExit(f"benchmark runner failed for {case['id']}:{variant}: {message}")
    if len(process.stdout.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise SystemExit(f"benchmark runner output too large for {case['id']}:{variant}")
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"benchmark runner returned invalid JSON for {case['id']}:{variant}") from exc
    observation = validate_observation(value, case["id"], variant, trial_index)
    if execution_order is not None:
        observation["execution_order"] = normalize_execution_order(execution_order)
    observation["memory_setup"] = (
        setup_audit if variant == "memory" else context_setup_audit(None)
    )
    if replay_package:
        observation["paired_replay_package_digest"] = replay_package["package_digest"]
    return observation


def load_observations(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"failed to read benchmark responses: {path}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != RESPONSES_SCHEMA:
        raise SystemExit(f"unsupported benchmark response schema; expected {RESPONSES_SCHEMA}")
    values = data.get("observations")
    if not isinstance(values, list):
        raise SystemExit("benchmark responses require observations")
    return [validate_observation(item) for item in values]


def validate_observation(
    value: Any,
    expected_case_id: str | None = None,
    expected_variant: str | None = None,
    expected_trial_index: int | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != RESPONSE_SCHEMA:
        raise SystemExit(f"benchmark observation must use {RESPONSE_SCHEMA}")
    if FORBIDDEN_REASONING_FIELDS & set(value):
        raise SystemExit("benchmark response must not contain chain-of-thought fields")
    if FORBIDDEN_MEMORY_TRACE_FIELDS & set(value):
        raise SystemExit("benchmark response must not contain Memory query text or output")
    case_id = text_field(value, "case_id")
    variant = text_field(value, "variant")
    if expected_case_id and case_id != expected_case_id:
        raise SystemExit(f"benchmark runner case mismatch: {case_id} != {expected_case_id}")
    if expected_variant and variant != expected_variant:
        raise SystemExit(f"benchmark runner variant mismatch: {variant} != {expected_variant}")
    trial_index = max(1, nonnegative_int(value.get("trial_index") or 1))
    if expected_trial_index and trial_index != expected_trial_index:
        raise SystemExit(
            f"benchmark runner trial mismatch: {trial_index} != {expected_trial_index}"
        )
    if variant not in {"baseline", "memory"}:
        raise SystemExit(f"unsupported benchmark variant: {variant}")
    files = string_list(value.get("predicted_files"), "predicted_files")
    supporting = [
        path
        for path in string_list(value.get("supporting_files") or [], "supporting_files")
        if path not in files
    ]
    mechanism_files = string_list(
        value.get("mechanism_evidence_files") or [], "mechanism_evidence_files"
    )
    mechanism_evidence = normalize_mechanism_evidence(
        value.get("mechanism_evidence") or [], "mechanism_evidence"
    )
    trace_reported = "expansion_trace" in value
    expansion_trace = normalize_expansion_trace(value.get("expansion_trace") or [])
    deterministic_accounting = (
        value.get("expansion_accounting_source") == "runner_investigated_files"
    )
    expansion_rounds = (
        nonnegative_int(value.get("expansion_rounds"))
        if deterministic_accounting
        else (
            len(expansion_trace)
            if trace_reported
            else nonnegative_int(value.get("expansion_rounds"))
        )
    )
    expansion_reasons = (
        [item["reason"] for item in expansion_trace]
        if trace_reported
        else string_list(
            value.get("expansion_reason_codes") or [], "expansion_reason_codes"
        )
    )
    investigated = list(dict.fromkeys([
        *string_list(value.get("investigated_files") or [], "investigated_files"),
        *files,
        *supporting,
    ]))
    memory_metrics_reported = all(
        key in value for key in ("memory_context_bytes", "memory_context_token_estimate")
    )
    exploration_reported = exploration_metrics_reported(value)
    execution_order = normalize_execution_order(value.get("execution_order"))
    return {
        **value,
        "case_id": case_id,
        "variant": variant,
        "trial_index": trial_index,
        **({"execution_order": execution_order} if execution_order else {}),
        "root_cause_category": str(value.get("root_cause_category") or "unknown").strip(),
        "predicted_files": files,
        "supporting_files": supporting,
        "investigated_files": investigated,
        "causal_level": str(value.get("causal_level") or "association").strip(),
        "verification_status": str(value.get("verification_status") or "unknown").strip(),
        "query_rounds": nonnegative_int(value.get("query_rounds")),
        "source_search_count": nonnegative_int(value.get("source_search_count")),
        "source_search_count_source": str(
            value.get("source_search_count_source") or "agent_reported"
        ).strip(),
        "token_estimate": nonnegative_int(value.get("token_estimate")),
        "model_input_tokens": nonnegative_int(value.get("model_input_tokens")),
        "model_cached_input_tokens": nonnegative_int(
            value.get("model_cached_input_tokens")
        ),
        "model_uncached_input_tokens": nonnegative_int(
            value.get("model_uncached_input_tokens")
        ),
        "model_output_tokens": nonnegative_int(value.get("model_output_tokens")),
        "model_reasoning_tokens": nonnegative_int(value.get("model_reasoning_tokens")),
        "command_count": nonnegative_int(value.get("command_count")),
        "command_output_bytes": nonnegative_int(value.get("command_output_bytes")),
        "source_read_count": nonnegative_int(value.get("source_read_count")),
        "source_read_output_bytes": nonnegative_int(
            value.get("source_read_output_bytes")
        ),
        "tool_error_count": nonnegative_int(value.get("tool_error_count")),
        "source_search_miss_count": nonnegative_int(
            value.get("source_search_miss_count")
        ),
        "source_search_error_count": nonnegative_int(
            value.get("source_search_error_count")
        ),
        "source_read_error_count": nonnegative_int(
            value.get("source_read_error_count")
        ),
        "other_tool_error_count": nonnegative_int(
            value.get("other_tool_error_count")
        ),
        "cost_metrics_reported": bool(value.get("cost_metrics_reported")),
        "memory_context_bytes": nonnegative_int(value.get("memory_context_bytes")),
        "memory_context_token_estimate": nonnegative_int(value.get("memory_context_token_estimate")),
        "memory_context_metrics_reported": memory_metrics_reported,
        "memory_query_count": nonnegative_int(value.get("memory_query_count")),
        "memory_query_success_count": nonnegative_int(
            value.get("memory_query_success_count")
        ),
        "memory_query_error_count": nonnegative_int(value.get("memory_query_error_count")),
        "memory_query_total_output_bytes": nonnegative_int(
            value.get("memory_query_total_output_bytes")
        ),
        "memory_query_total_output_token_estimate": nonnegative_int(
            value.get("memory_query_total_output_token_estimate")
        ),
        "memory_query_metrics_reported": bool(value.get("memory_query_metrics_reported")),
        "memory_query_kinds": string_list(
            value.get("memory_query_kinds") or [], "memory_query_kinds"
        ),
        "memory_query_digests": string_list(
            value.get("memory_query_digests") or [], "memory_query_digests"
        ),
        "memory_query_anchor_paths": string_list(
            value.get("memory_query_anchor_paths") or [], "memory_query_anchor_paths"
        ),
        "memory_query_primary_anchor_paths": string_list(
            value.get("memory_query_primary_anchor_paths") or [],
            "memory_query_primary_anchor_paths",
        ),
        "expansion_rounds": expansion_rounds,
        "expansion_file_count": nonnegative_int(value.get("expansion_file_count")),
        "expansion_accounting_source": str(
            value.get("expansion_accounting_source") or "agent_trace"
        ).strip(),
        "expansion_reason_codes": expansion_reasons,
        "stop_reason": str(value.get("stop_reason") or "unreported").strip(),
        "evidence_basis": str(value.get("evidence_basis") or "unreported").strip(),
        "mechanism_evidence_files": list(dict.fromkeys(mechanism_files)),
        "mechanism_evidence": mechanism_evidence,
        "expansion_trace": expansion_trace,
        "expansion_trace_reported": trace_reported,
        "exploration_metrics_reported": exploration_reported,
        "elapsed_ms": nonnegative_int(value.get("elapsed_ms")),
        "end_to_end_elapsed_ms": nonnegative_int(
            value.get("end_to_end_elapsed_ms", value.get("elapsed_ms"))
        ),
        "agent_elapsed_ms": nonnegative_int(value.get("agent_elapsed_ms")),
        "memory_retrieval_elapsed_ms": nonnegative_int(
            value.get("memory_retrieval_elapsed_ms")
        ),
        "latency_metrics_reported": bool(value.get("latency_metrics_reported")),
        "source_file_count": nonnegative_int(
            value.get("source_file_count", len(investigated))
        ),
        "memory_anchor_hit_count": nonnegative_int(value.get("memory_anchor_hit_count")),
        "primary_anchor_hit_count": nonnegative_int(value.get("primary_anchor_hit_count")),
        "non_anchor_file_count": nonnegative_int(value.get("non_anchor_file_count")),
        "summary": str(value.get("summary") or "")[:1000],
    }


def response_template(case_id: str, variant: str, trial_index: int = 1) -> dict[str, Any]:
    return {
        "schema_version": RESPONSE_SCHEMA,
        "case_id": case_id,
        "variant": variant,
        "trial_index": trial_index,
        "root_cause_category": "category only",
        "predicted_files": [],
        "supporting_files": [],
        "investigated_files": [],
        "causal_level": "association|supported|verified|rejected",
        "verification_status": "pass|fail|unknown",
        "query_rounds": 0,
        "source_search_count": 0,
        "expansion_trace": [],
        "stop_reason": "supported_cause_found|direct_verification_settled|budget_exhausted_report_uncertainty|no_new_evidence",
        "evidence_basis": "direct_source_mechanism|runtime_verified_mechanism|inference_only",
        "mechanism_evidence_files": [],
        "mechanism_evidence": [],
        "token_estimate": 0,
        "elapsed_ms": 0,
        "source_file_count": 0,
        "memory_anchor_hit_count": 0,
        "primary_anchor_hit_count": 0,
        "non_anchor_file_count": 0,
        "summary": "brief conclusion without private reasoning",
    }


def runner_instructions(
    variant: str, treatment_mode: str = "preloaded-context",
) -> list[str]:
    if treatment_mode == SELECTIVE_TREATMENT_MODE:
        return [
            "Inspect only the supplied workspace and public case.",
            "Do not access Git history after the supplied revision or hidden benchmark oracle.",
            "No Agent Memory context is preloaded. Use an available Query Skill only when its selective retrieval policy calls for it.",
            "Never inspect Agent Memory databases, generated vault files, or runtime snapshots directly.",
            "Return only the requested JSON; do not return chain-of-thought.",
        ]
    return [
        "Inspect only the supplied workspace and public case.",
        "Do not access Git history after the supplied revision or hidden benchmark oracle.",
        "You are the diagnosing/designing Agent; Agent Memory only supplies retrievable context and does not decide the answer.",
        "Use preloaded Agent Memory context when present; do not invoke Memory, its database, generated vault, or skills from the workspace.",
        "Return only the requested JSON; do not return chain-of-thought.",
    ]


def resolve_runner(value: str) -> str:
    if any(character in value for character in ("\n", "\r", "\0")):
        raise SystemExit("invalid benchmark runner path")
    path = Path(value).expanduser()
    resolved = str(path.resolve()) if path.exists() else shutil.which(value)
    if not resolved:
        raise SystemExit(f"benchmark runner executable not found: {value}")
    return resolved


def text_field(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise SystemExit(f"benchmark response requires {key}")
    return item.strip()


def string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit(f"benchmark response {label} must be a string list")
    return list(dict.fromkeys(item.strip() for item in value if item.strip()))[:100]


def normalize_expansion_trace(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise SystemExit("benchmark response expansion_trace must be a list")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or not isinstance(item.get("reason"), str):
            raise SystemExit(f"benchmark response expansion_trace[{index}] is invalid")
        result.append({
            "reason": item["reason"].strip(),
            "files": string_list(item.get("files"), f"expansion_trace[{index}].files"),
        })
    return result[:10]


def nonnegative_int(value: Any) -> int:
    return max(0, int(value or 0))
