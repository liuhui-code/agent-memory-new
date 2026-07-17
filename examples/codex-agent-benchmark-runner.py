#!/usr/bin/env python3
# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Run one Agent benchmark request through Codex CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.agent_memory_runtime.source_exploration import (  # noqa: E402
    ALLOWED_EXPANSION_REASONS,
    EVIDENCE_BASES,
    EXPANSION_ROUND_LIMIT,
    FILES_PER_EXPANSION_LIMIT,
    POLICY_NAME,
    SOURCE_FILE_LIMIT,
    SOURCE_SEARCH_LIMIT,
    STOP_REASONS,
)
from examples.codex_benchmark_telemetry import source_search_metrics  # noqa: E402


RESPONSE_SCHEMA = "agent-benchmark-response/v1"


def main() -> int:
    request = json.load(sys.stdin)
    workspace = Path(required_text(request, "workspace")).resolve()
    if not workspace.is_dir():
        raise SystemExit(f"benchmark workspace not found: {workspace}")
    case_id = required_text(request, "case_id")
    variant = required_text(request, "variant")
    trial_index = int(request.get("trial_index") or 1)
    if variant not in {"baseline", "memory"}:
        raise SystemExit(f"unsupported benchmark variant: {variant}")

    with tempfile.TemporaryDirectory(prefix="codex-benchmark-runner-") as directory:
        temp = Path(directory)
        schema_path = temp / "response-schema.json"
        result_path = temp / "last-message.json"
        codex_home = prepare_codex_home(temp)
        schema_path.write_text(json.dumps(output_schema(), indent=2) + "\n", encoding="utf-8")
        memory_context = load_memory_context(request, workspace)
        prompt = build_prompt(request, memory_context)
        command = codex_command(workspace, schema_path, result_path)
        started = time.monotonic()
        process = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            cwd=workspace,
            env=codex_environment(temp, codex_home),
            check=False,
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        if process.returncode != 0:
            message = failure_output(process.stdout, process.stderr)
            raise SystemExit(f"Codex benchmark execution failed: {message}")
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit("Codex benchmark result is missing or invalid") from exc

    result = normalize_exploration(normalize_file_roles(result))
    result.update({
        "schema_version": RESPONSE_SCHEMA,
        "case_id": case_id,
        "variant": variant,
        "trial_index": trial_index,
        "causal_level": cap_causal_level(result.get("causal_level")),
        "verification_status": "unknown",
        "elapsed_ms": elapsed_ms,
        "token_estimate": extract_token_usage(process.stdout),
        **memory_context_metrics(memory_context),
        **execution_metrics(result, memory_context),
        **source_search_metrics(process.stdout, result),
        "runner_metadata": runner_metadata(),
    })
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def codex_command(workspace: Path, schema_path: Path, result_path: Path) -> list[str]:
    executable = os.environ.get("AGENT_BENCHMARK_CODEX", "codex")
    command = [
        executable,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--disable", "apps",
        "--disable", "browser_use",
        "--disable", "computer_use",
        "--disable", "multi_agent",
        "--disable", "plugins",
        "--skip-git-repo-check",
        "--sandbox", "read-only",
        "--output-schema", str(schema_path),
        "--output-last-message", str(result_path),
        "--color", "never",
        "--json",
        "--cd", str(workspace),
    ]
    model = os.environ.get("AGENT_BENCHMARK_CODEX_MODEL", "").strip()
    if model:
        command.extend(["--model", model])
    reasoning_effort = os.environ.get("AGENT_BENCHMARK_CODEX_REASONING_EFFORT", "").strip()
    if reasoning_effort:
        command.extend(["--config", f'model_reasoning_effort="{reasoning_effort}"'])
    command.append("-")
    return command


def load_memory_context(request: dict[str, Any], workspace: Path) -> dict[str, Any] | None:
    memory = request.get("memory_access")
    if not isinstance(memory, dict):
        return None
    command = substitute_query(
        memory.get("query_command"),
        str((request.get("case") or {}).get("task", {}).get("description") or ""),
    )
    try:
        process = subprocess.run(
            command,
            text=True,
            capture_output=True,
            cwd=workspace,
            env=clean_environment(),
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"Agent Memory query failed: {exc}") from exc
    if process.returncode != 0:
        raise SystemExit(f"Agent Memory query failed: {failure_output(process.stdout, process.stderr)}")
    if len(process.stdout.encode("utf-8")) > 1_000_000:
        raise SystemExit("Agent Memory query output exceeds 1 MB")
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit("Agent Memory query returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise SystemExit("Agent Memory query must return a JSON object")
    return value


def build_prompt(request: dict[str, Any], memory_context: dict[str, Any] | None = None) -> str:
    case = request.get("case") or {}
    task = case.get("task") or {}
    instructions = request.get("instructions") or []
    lines = [
        "Act as the external coding Agent for a controlled benchmark.",
        "Do not modify files. Do not inspect Git history. Do not search the web.",
        f"Task type: {case.get('task_type', 'diagnosis')}",
        f"Task: {task.get('description', '')}",
    ]
    constraints = task.get("constraints") or []
    if constraints:
        lines.append("Constraints:")
        lines.extend(f"- {item}" for item in constraints)
    lines.append("Benchmark rules:")
    lines.extend(f"- {item}" for item in instructions)
    if memory_context is not None:
        lines.extend([
            "Agent Memory context was queried once by the benchmark runner before this session:",
            json.dumps(memory_context, ensure_ascii=False),
            "Treat its output only as context. Verify all conclusions against current source.",
            "Follow query_handoff.source_exploration exactly.",
            source_budget_instruction(memory_context),
            "Count each rg, grep, find, or fd invocation before running it. If the next invocation would exceed the search budget, do not run it; stop with budget_exhausted_report_uncertainty.",
            "Inspect code anchors with role=primary first. Do not inspect role=expansion or non-anchor files without naming one allowed expansion reason.",
            "One expansion round closes one evidence gap and may inspect at most two new files.",
            "Record each expansion round once in expansion_trace with its reason and newly inspected files; the Runner derives round and reason totals.",
            "Every source file actually opened must appear in investigated_files. Every role=expansion or non-anchor file must appear exactly once in expansion_trace in the round that first opened it.",
            "Stop with supported_cause_found only after an inspected causal file shows a concrete operation, branch, state transition, boundary, or API misuse that explains the symptom.",
            "mechanism_evidence_files may include an inspected supporting boundary, but must include at least one predicted causal or repair-owner file.",
            "Use direct_source_mechanism or runtime_verified_mechanism as evidence_basis for a supported stop.",
            "If source only suggests a likely owner or intended behavior, use evidence_basis=inference_only and report no_new_evidence or budget exhaustion instead of supported_cause_found.",
            "If the budget is exhausted, report uncertainty instead of continuing source exploration.",
        ])
    lines.extend([
        "Inspect the smallest useful set of current source files.",
        "Put only root-cause or repair-owner files in predicted_files. Put inspected callers, boundaries, and corroborating files in supporting_files.",
        "Do not repeat a predicted file in supporting_files; include both groups in investigated_files.",
        "Report source_search_count, expansion_trace, and the final stop_reason.",
        "Return only the requested JSON object.",
        "Category precedence is: async concurrency, then the concrete failure domain, then low-level api or state implementation detail.",
        "Use async for parallel in-flight requests, races, ordering, or duplicate async side effects, even when a missing state flag is the guard. Use state only for a wrong stored or derived value without concurrency.",
        "Use media for WebM, video, audio, or image loading, decoding, playback, and local media-resource access, even when the mechanism is API misuse. Describe the API misuse in summary instead of changing the category to api.",
        "Use api only when an external or platform API contract is itself the primary failure domain and no stronger domain category applies. Other categories include route, lifecycle, ui_layout, resource, database_failure, and push.",
        "Do not include private reasoning, thoughts, or chain-of-thought.",
        "Response contract:",
        json.dumps(request.get("response_schema") or {}, ensure_ascii=False),
    ])
    return "\n".join(lines)


def source_budget_instruction(memory_context: dict[str, Any]) -> str:
    handoff = memory_context.get("query_handoff")
    exploration = handoff.get("source_exploration") if isinstance(handoff, dict) else None
    limits = exploration.get("limits") if isinstance(exploration, dict) else None
    values = limits if isinstance(limits, dict) else {}
    searches = int(values.get("searches") or SOURCE_SEARCH_LIMIT)
    files = int(values.get("files") or SOURCE_FILE_LIMIT)
    rounds = int(values.get("rounds") or EXPANSION_ROUND_LIMIT)
    round_files = int(values.get("round_files") or FILES_PER_EXPANSION_LIMIT)
    return (
        "Hard source budget for this Memory run: at most "
        f"{searches} source-search invocations, {files} total investigated source files, "
        f"{rounds} expansion rounds, and {round_files} new files per expansion round."
    )


def substitute_query(value: Any, description: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit("memory_access.query_command must be a string list")
    return [
        description if item in {"<task-description>", "<task-description-or-agent-extracted-term>"} else item
        for item in value
    ]


def output_schema() -> dict[str, Any]:
    properties = {
        "schema_version": {"type": "string"},
        "case_id": {"type": "string"},
        "variant": {"type": "string"},
        "trial_index": {"type": "integer", "minimum": 1},
        "root_cause_category": {"type": "string"},
        "predicted_files": {"type": "array", "items": {"type": "string"}},
        "supporting_files": {"type": "array", "items": {"type": "string"}},
        "investigated_files": {"type": "array", "items": {"type": "string"}},
        "causal_level": {
            "type": "string",
            "enum": ["association", "supported", "verified", "rejected"],
        },
        "verification_status": {
            "type": "string",
            "enum": ["pass", "fail", "unknown"],
        },
        "query_rounds": {"type": "integer", "minimum": 0},
        "source_search_count": {"type": "integer", "minimum": 0},
        "expansion_trace": {
            "type": "array",
            "maxItems": EXPANSION_ROUND_LIMIT,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["reason", "files"],
                "properties": {
                    "reason": {"type": "string", "enum": list(ALLOWED_EXPANSION_REASONS)},
                    "files": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": FILES_PER_EXPANSION_LIMIT,
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "stop_reason": {"type": "string", "enum": list(STOP_REASONS)},
        "evidence_basis": {"type": "string", "enum": list(EVIDENCE_BASES)},
        "mechanism_evidence_files": {
            "type": "array",
            "items": {"type": "string"},
        },
        "token_estimate": {"type": "integer", "minimum": 0},
        "elapsed_ms": {"type": "integer", "minimum": 0},
        "summary": {"type": "string"},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def extract_token_usage(text: str) -> int:
    best = 0
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        best = max(best, token_total(event))
    return best


def failure_output(stdout: str, stderr: str) -> str:
    parts = []
    for label, value in (("stderr", stderr.strip()), ("stdout", stdout.strip())):
        if not value:
            continue
        excerpt = value if len(value) <= 4000 else value[:2000] + "\n...\n" + value[-2000:]
        parts.append(f"{label}:\n{excerpt}")
    return "\n".join(parts) or "no process output"


def token_total(value: Any) -> int:
    if isinstance(value, dict):
        direct = sum(
            int(value.get(key) or 0)
            for key in ("input_tokens", "output_tokens")
            if isinstance(value.get(key), (int, float))
        )
        return max([direct, *(token_total(item) for item in value.values())])
    if isinstance(value, list):
        return max([0, *(token_total(item) for item in value)])
    return 0


def cap_causal_level(value: Any) -> str:
    level = str(value or "association").strip()
    return "supported" if level == "verified" else level


def memory_context_metrics(value: dict[str, Any] | None) -> dict[str, int]:
    if value is None:
        return {"memory_context_bytes": 0, "memory_context_token_estimate": 0}
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "memory_context_bytes": len(encoded),
        "memory_context_token_estimate": max(1, (len(encoded) + 3) // 4),
    }


def execution_metrics(result: dict[str, Any], memory_context: dict[str, Any] | None) -> dict[str, int]:
    investigated = {
        str(item) for item in result.get("investigated_files") or [] if str(item).strip()
    }
    anchors = memory_code_anchor_paths(memory_context)
    primary = memory_code_anchor_paths(memory_context, "primary")
    return {
        "source_file_count": len(investigated),
        "memory_anchor_hit_count": len(investigated & anchors),
        "primary_anchor_hit_count": len(investigated & primary),
        "non_anchor_file_count": len(investigated - anchors),
    }


def normalize_file_roles(result: dict[str, Any]) -> dict[str, Any]:
    predicted = unique_paths(result.get("predicted_files"))
    supporting = [
        path for path in unique_paths(result.get("supporting_files")) if path not in predicted
    ]
    inspected = unique_paths(result.get("investigated_files"))
    investigated = unique_paths([
        *inspected,
        *predicted,
        *supporting,
    ])
    mechanism = unique_paths(result.get("mechanism_evidence_files"))
    return {
        **result,
        "predicted_files": predicted,
        "supporting_files": supporting,
        "investigated_files": investigated,
        "mechanism_evidence_files": mechanism,
    }


def normalize_exploration(result: dict[str, Any]) -> dict[str, Any]:
    trace = []
    for item in result.get("expansion_trace") or []:
        if not isinstance(item, dict):
            continue
        trace.append({
            "reason": str(item.get("reason") or "").strip(),
            "files": unique_paths(item.get("files")),
        })
    return {
        **result,
        "expansion_trace": trace,
        "expansion_rounds": len(trace),
        "expansion_reason_codes": [item["reason"] for item in trace],
    }


def unique_paths(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def memory_code_anchor_paths(
    value: dict[str, Any] | None,
    role: str | None = None,
) -> set[str]:
    if not isinstance(value, dict):
        return set()
    handoff = value.get("query_handoff")
    if not isinstance(handoff, dict):
        return set()
    return {
        str(item.get("file_path"))
        for item in handoff.get("code_anchors") or []
        if (
            isinstance(item, dict)
            and item.get("file_path")
            and (role is None or item.get("role") == role)
        )
    }


def clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("AGENT_MEMORY_HOME", None)
    environment.pop("AGENT_BENCHMARK_VARIANT", None)
    return environment


def prepare_codex_home(temp: Path) -> Path:
    source = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    target = temp / "codex-home"
    target.mkdir()
    for name in ("auth.json", "models_cache.json", "installation_id"):
        path = source / name
        if path.is_file():
            shutil.copy2(path, target / name)
    return target


def codex_environment(temp: Path, codex_home: Path) -> dict[str, str]:
    environment = clean_environment()
    home = temp / "home"
    home.mkdir()
    environment["HOME"] = str(home)
    environment["CODEX_HOME"] = str(codex_home)
    return environment


def runner_metadata() -> dict[str, str]:
    return {
        "runner": "codex_cli",
        "runner_version": os.environ.get("AGENT_BENCHMARK_CODEX_VERSION", "codex-cli 0.142.0"),
        "model": os.environ.get("AGENT_BENCHMARK_CODEX_MODEL", "unreported"),
        "reasoning_effort": os.environ.get(
            "AGENT_BENCHMARK_CODEX_REASONING_EFFORT", "unreported"
        ),
        "sandbox": "read-only",
        "session": "ephemeral",
        "memory_delivery": "runner_preloaded",
        "user_context": "isolated_home",
        "retrieval_policy": POLICY_NAME,
    }


def required_text(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise SystemExit(f"benchmark request requires {key}")
    return item.strip()


if __name__ == "__main__":
    raise SystemExit(main())
