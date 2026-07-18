# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Trusted loopback Ollama runner for controlled Agent benchmarks."""

from __future__ import annotations

import ipaddress
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from examples.codex_benchmark_prompt import benchmark_response_schema, build_prompt
from examples.ollama_benchmark_tools import SourceToolExecutor, source_tool_definitions
from tools.agent_memory_runtime.source_exploration import (
    FILES_PER_EXPANSION_LIMIT,
    POLICY_NAME,
)


RESPONSE_SCHEMA = "agent-benchmark-response/v1"
MAX_HTTP_RESPONSE_BYTES = 10_000_000
MAX_AGENT_ROUNDS = 6
MAX_TOOL_CALLS = 12
TOOL_CALL_NUM_PREDICT = 256
FINAL_NUM_PREDICT = 512


class OllamaClient:
    def __init__(self, host: str, model: str, timeout: int) -> None:
        self.host = validate_ollama_host(host)
        self.model = model.strip()
        self.timeout = max(1, int(timeout))
        self.version = "unreported"
        self.model_input_tokens = 0
        self.model_output_tokens = 0
        self.usage_metrics_reported = False

    def verify(self) -> None:
        version = self._request("GET", "/api/version")
        self.version = str(version.get("version") or "unreported")
        tags = self._request("GET", "/api/tags")
        installed = {
            str(item.get("name") or item.get("model") or "")
            for item in tags.get("models") or []
            if isinstance(item, dict)
        }
        if self.model not in installed:
            raise SystemExit(
                f"Ollama model is not installed: {self.model}; installed={sorted(installed)}"
            )

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        format_schema: dict[str, Any] | None = None,
        num_predict: int = TOOL_CALL_NUM_PREDICT,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_predict": num_predict},
        }
        if tools is not None:
            payload["tools"] = tools
        if format_schema is not None:
            payload["format"] = format_schema
        response = self._request("POST", "/api/chat", payload)
        if "prompt_eval_count" in response or "eval_count" in response:
            self.usage_metrics_reported = True
        self.model_input_tokens += metric_int(response.get("prompt_eval_count"))
        self.model_output_tokens += metric_int(response.get("eval_count"))
        message = response.get("message")
        if not isinstance(message, dict):
            raise SystemExit("Ollama chat response is missing message")
        return message

    def _request(
        self,
        method: str,
        path: str,
        value: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if value is not None:
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.host + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read(MAX_HTTP_RESPONSE_BYTES + 1)
        except (OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
            raise SystemExit(f"Ollama request failed for {path}: {exc}") from exc
        if len(body) > MAX_HTTP_RESPONSE_BYTES:
            raise SystemExit(f"Ollama response exceeds {MAX_HTTP_RESPONSE_BYTES} bytes")
        try:
            result = json.loads(body)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Ollama returned invalid JSON for {path}") from exc
        if not isinstance(result, dict):
            raise SystemExit(f"Ollama returned a non-object response for {path}")
        return result


def run_request(
    request: dict[str, Any],
    *,
    host: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    workspace = Path(required_text(request, "workspace")).resolve()
    if not workspace.is_dir():
        raise SystemExit(f"benchmark workspace not found: {workspace}")
    case_id = required_text(request, "case_id")
    variant = required_text(request, "variant")
    if variant not in {"baseline", "memory"}:
        raise SystemExit(f"unsupported benchmark variant: {variant}")
    trial_index = int(request.get("trial_index") or 1)
    memory_context = load_memory_context(request, workspace, timeout)
    executor = SourceToolExecutor(workspace)
    client = OllamaClient(host, model, timeout)
    client.verify()

    started = time.monotonic()
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": build_prompt(request, memory_context)}
    ]
    run_agent_loop(client, messages, executor)
    messages.append({
        "role": "user",
        "content": (
            "Return the final benchmark response now. Use only gathered evidence, "
            "return JSON matching the required schema, and include no private reasoning."
        ),
    })
    final = client.chat(
        messages,
        format_schema=benchmark_response_schema(),
        num_predict=FINAL_NUM_PREDICT,
    )
    result = parse_final_result(final)
    elapsed_ms = int((time.monotonic() - started) * 1000)

    result = normalize_result(result, executor, memory_context)
    result.update({
        "schema_version": RESPONSE_SCHEMA,
        "case_id": case_id,
        "variant": variant,
        "trial_index": trial_index,
        "causal_level": cap_causal_level(result.get("causal_level")),
        "verification_status": "unknown",
        "elapsed_ms": elapsed_ms,
        **cost_metrics(client),
        **memory_context_metrics(memory_context),
        **executor.telemetry(),
        **execution_metrics(
            executor.investigated_files,
            source_excerpt_paths(memory_context),
            memory_context,
        ),
        "runner_metadata": runner_metadata(client),
    })
    return result


def run_agent_loop(
    client: OllamaClient,
    messages: list[dict[str, Any]],
    executor: SourceToolExecutor,
) -> None:
    calls = 0
    for _round in range(MAX_AGENT_ROUNDS):
        message = client.chat(messages, tools=source_tool_definitions())
        messages.append(agent_message(message))
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return
        for item in tool_calls:
            calls += 1
            if calls > MAX_TOOL_CALLS:
                raise SystemExit(f"Ollama Agent exceeded {MAX_TOOL_CALLS} tool calls")
            name, arguments = parse_tool_call(item)
            messages.append({
                "role": "tool",
                "tool_name": name,
                "content": executor.execute(name, arguments),
            })
    raise SystemExit(f"Ollama Agent exceeded {MAX_AGENT_ROUNDS} tool rounds")


def agent_message(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "role": "assistant",
        "content": str(value.get("content") or ""),
    }
    if isinstance(value.get("tool_calls"), list):
        result["tool_calls"] = value["tool_calls"]
    return result


def parse_tool_call(value: Any) -> tuple[str, dict[str, Any]]:
    function = value.get("function") if isinstance(value, dict) else None
    if not isinstance(function, dict):
        return "", {}
    name = str(function.get("name") or "").strip()
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    return name, arguments if isinstance(arguments, dict) else {}


def parse_final_result(message: dict[str, Any]) -> dict[str, Any]:
    content = str(message.get("content") or "").strip()
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise SystemExit("Ollama final response is not valid JSON") from exc
    if not isinstance(result, dict):
        raise SystemExit("Ollama final response must be a JSON object")
    return result


def load_memory_context(
    request: dict[str, Any], workspace: Path, timeout: int
) -> dict[str, Any] | None:
    memory = request.get("memory_access")
    if not isinstance(memory, dict):
        return None
    task = (request.get("case") or {}).get("task") or {}
    description = str(task.get("description") or "")
    command = substitute_query(memory.get("query_command"), description)
    environment = os.environ.copy()
    environment.pop("AGENT_MEMORY_HOME", None)
    environment.pop("AGENT_BENCHMARK_VARIANT", None)
    try:
        process = subprocess.run(
            command,
            text=True,
            capture_output=True,
            cwd=workspace,
            env=environment,
            timeout=max(5, timeout),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"Agent Memory query failed: {exc}") from exc
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()
        raise SystemExit(f"Agent Memory query failed: {detail[:4000]}")
    if len(process.stdout.encode("utf-8")) > 1_000_000:
        raise SystemExit("Agent Memory query output exceeds 1 MB")
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit("Agent Memory query returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise SystemExit("Agent Memory query must return a JSON object")
    return value


def substitute_query(value: Any, description: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit("memory_access.query_command must be a string list")
    placeholders = {"<task-description>", "<task-description-or-agent-extracted-term>"}
    return [description if item in placeholders else item for item in value]


def normalize_result(
    value: dict[str, Any],
    executor: SourceToolExecutor,
    memory_context: dict[str, Any] | None,
) -> dict[str, Any]:
    predicted = unique_paths(value.get("predicted_files"))
    supporting = [
        path for path in unique_paths(value.get("supporting_files")) if path not in predicted
    ]
    investigated = unique_paths([
        *executor.investigated_files,
        *source_excerpt_paths(memory_context),
        *unique_paths(value.get("investigated_files")),
        *predicted,
        *supporting,
    ])
    trace = []
    for item in value.get("expansion_trace") or []:
        if isinstance(item, dict):
            trace.append({
                "reason": str(item.get("reason") or "").strip(),
                "files": unique_paths(item.get("files")),
            })
    return {
        **value,
        "predicted_files": predicted,
        "supporting_files": supporting,
        "investigated_files": investigated,
        "mechanism_evidence_files": unique_paths(value.get("mechanism_evidence_files")),
        "expansion_trace": trace,
        "expansion_rounds": len(trace),
        "expansion_reason_codes": [item["reason"] for item in trace],
    }


def source_excerpt_paths(value: dict[str, Any] | None) -> list[str]:
    if not isinstance(value, dict):
        return []
    handoff = value.get("query_handoff")
    anchors = handoff.get("code_anchors") if isinstance(handoff, dict) else []
    return unique_paths([
        item.get("file_path")
        for item in anchors or []
        if isinstance(item, dict) and item.get("source_excerpts")
    ])


def execution_metrics(
    source_reads: list[str],
    excerpt_paths: list[str],
    memory_context: dict[str, Any] | None,
) -> dict[str, Any]:
    investigated = set(source_reads) | set(excerpt_paths)
    anchors = anchor_paths(memory_context)
    primary = anchor_paths(memory_context, "primary")
    expanded = len(investigated - primary)
    return {
        "source_file_count": len(investigated),
        "memory_anchor_hit_count": len(investigated & anchors),
        "primary_anchor_hit_count": len(investigated & primary),
        "non_anchor_file_count": len(investigated - anchors),
        "expansion_file_count": expanded,
        "expansion_rounds": (
            expanded + FILES_PER_EXPANSION_LIMIT - 1
        ) // FILES_PER_EXPANSION_LIMIT,
        "expansion_accounting_source": "runner_investigated_files",
    }


def anchor_paths(value: dict[str, Any] | None, role: str | None = None) -> set[str]:
    if not isinstance(value, dict):
        return set()
    handoff = value.get("query_handoff")
    anchors = handoff.get("code_anchors") if isinstance(handoff, dict) else []
    return {
        str(item.get("file_path"))
        for item in anchors or []
        if isinstance(item, dict)
        and item.get("file_path")
        and (role is None or item.get("role") == role)
    }


def memory_context_metrics(value: dict[str, Any] | None) -> dict[str, int]:
    if value is None:
        return {"memory_context_bytes": 0, "memory_context_token_estimate": 0}
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "memory_context_bytes": len(encoded),
        "memory_context_token_estimate": max(1, (len(encoded) + 3) // 4),
    }


def cost_metrics(client: OllamaClient) -> dict[str, Any]:
    return {
        "model_input_tokens": client.model_input_tokens,
        "model_cached_input_tokens": 0,
        "model_uncached_input_tokens": client.model_input_tokens,
        "model_output_tokens": client.model_output_tokens,
        "model_reasoning_tokens": 0,
        "token_estimate": client.model_input_tokens + client.model_output_tokens,
        "cost_metrics_reported": client.usage_metrics_reported,
    }


def runner_metadata(client: OllamaClient) -> dict[str, str]:
    return {
        "runner": "ollama_local",
        "runner_version": client.version,
        "model": client.model,
        "host": client.host,
        "sandbox": "workspace_read_tools",
        "session": "ephemeral",
        "memory_delivery": "runner_preloaded",
        "source_boundary": "local_process",
        "source_excerpt_delivery": "full",
        "thinking": "disabled",
        "tool_num_predict": str(TOOL_CALL_NUM_PREDICT),
        "final_num_predict": str(FINAL_NUM_PREDICT),
        "retrieval_policy": POLICY_NAME,
    }


def validate_ollama_host(value: str) -> str:
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme != "http" or not parsed.hostname:
        raise SystemExit("Ollama host must be an http loopback URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SystemExit("Ollama host must be an http loopback URL without credentials")
    hostname = parsed.hostname.casefold()
    try:
        loopback = hostname == "localhost" or ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        loopback = False
    if not loopback:
        raise SystemExit("Ollama host must use a loopback address")
    if parsed.path not in {"", "/"}:
        raise SystemExit("Ollama host must not include an API path")
    return value.rstrip("/")


def unique_paths(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def cap_causal_level(value: Any) -> str:
    level = str(value or "association").strip()
    return "supported" if level == "verified" else level


def metric_int(value: Any) -> int:
    return max(0, int(value)) if isinstance(value, (int, float)) else 0


def required_text(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise SystemExit(f"benchmark request requires {key}")
    return item.strip()
