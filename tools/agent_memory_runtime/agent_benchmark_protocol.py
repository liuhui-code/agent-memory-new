# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .agent_benchmark_cases import public_case
from .benchmark_memory import prepare_isolated_memory
from .benchmark_workspace import materialized_workspace


REQUEST_SCHEMA = "agent-benchmark-request/v1"
RESPONSE_SCHEMA = "agent-benchmark-response/v1"
RESPONSES_SCHEMA = "agent-benchmark-responses/v1"
MAX_OUTPUT_BYTES = 1_000_000
FORBIDDEN_REASONING_FIELDS = {"thought", "thoughts", "reasoning", "chain_of_thought", "cot"}


def run_benchmark_agent(
    root: Path,
    case: dict[str, Any],
    variant: str,
    runner: str,
    timeout: int,
    prepare_memory: bool = True,
) -> dict[str, Any]:
    executable = resolve_runner(runner)
    with materialized_workspace(root, case) as workspace:
        request = {
            "schema_version": REQUEST_SCHEMA,
            "case_id": case["id"],
            "variant": variant,
            "workspace": str(workspace),
            "case": public_case(case),
            "instructions": runner_instructions(variant),
            "response_schema": response_template(case["id"], variant),
        }
        if variant == "memory" and prepare_memory:
            request["memory_access"] = prepare_isolated_memory(
                workspace,
                workspace.parent / "memory-home",
                timeout,
                case["task_type"],
            )
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
    return validate_observation(value, case["id"], variant)


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
) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != RESPONSE_SCHEMA:
        raise SystemExit(f"benchmark observation must use {RESPONSE_SCHEMA}")
    if FORBIDDEN_REASONING_FIELDS & set(value):
        raise SystemExit("benchmark response must not contain chain-of-thought fields")
    case_id = text_field(value, "case_id")
    variant = text_field(value, "variant")
    if expected_case_id and case_id != expected_case_id:
        raise SystemExit(f"benchmark runner case mismatch: {case_id} != {expected_case_id}")
    if expected_variant and variant != expected_variant:
        raise SystemExit(f"benchmark runner variant mismatch: {variant} != {expected_variant}")
    if variant not in {"baseline", "memory"}:
        raise SystemExit(f"unsupported benchmark variant: {variant}")
    files = string_list(value.get("predicted_files"), "predicted_files")
    investigated = string_list(value.get("investigated_files") or [], "investigated_files")
    return {
        **value,
        "case_id": case_id,
        "variant": variant,
        "root_cause_category": str(value.get("root_cause_category") or "unknown").strip(),
        "predicted_files": files,
        "investigated_files": investigated,
        "causal_level": str(value.get("causal_level") or "association").strip(),
        "verification_status": str(value.get("verification_status") or "unknown").strip(),
        "query_rounds": nonnegative_int(value.get("query_rounds")),
        "token_estimate": nonnegative_int(value.get("token_estimate")),
        "elapsed_ms": nonnegative_int(value.get("elapsed_ms")),
        "summary": str(value.get("summary") or "")[:1000],
    }


def response_template(case_id: str, variant: str) -> dict[str, Any]:
    return {
        "schema_version": RESPONSE_SCHEMA,
        "case_id": case_id,
        "variant": variant,
        "root_cause_category": "category only",
        "predicted_files": [],
        "investigated_files": [],
        "causal_level": "association|supported|verified|rejected",
        "verification_status": "pass|fail|unknown",
        "query_rounds": 0,
        "token_estimate": 0,
        "elapsed_ms": 0,
        "summary": "brief conclusion without private reasoning",
    }


def runner_instructions(variant: str) -> list[str]:
    instructions = [
        "Inspect only the supplied workspace and public case.",
        "Do not access Git history after the supplied revision or hidden benchmark oracle.",
        "You are the diagnosing/designing Agent; Agent Memory only supplies retrievable context and does not decide the answer.",
        "Return only the requested JSON; do not return chain-of-thought.",
    ]
    if variant == "memory":
        instructions.append(
            "Use the supplied isolated memory_access command as evidence context before doing your own source inspection and reasoning."
        )
    else:
        instructions.append("Do not use Agent Memory, its database, generated vault, or memory skills.")
    return instructions


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


def nonnegative_int(value: Any) -> int:
    return max(0, int(value or 0))
