# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import shlex
from pathlib import Path
from typing import Any

from examples.codex_benchmark_telemetry import (
    completed_turn_reported,
    unique_completed_command_items,
    unwrap_shell_payload,
)


QUERY_COMMANDS = {"context", "design-context", "search", "wiki-search"}


def memory_query_metrics(jsonl: str) -> dict[str, Any]:
    calls: list[dict[str, str]] = []
    success_count = 0
    error_count = 0
    total_output_bytes = 0
    max_output_bytes = 0
    anchors: set[str] = set()
    primary: set[str] = set()
    command_events = unique_completed_command_items(jsonl)
    for item in command_events:
        invocations = memory_invocations(item.get("command"))
        if not invocations:
            continue
        calls.extend(invocations)
        output = str(item.get("aggregated_output") or item.get("output") or "")
        output_bytes = len(output.encode("utf-8"))
        total_output_bytes += output_bytes
        succeeded = item.get("exit_code") in (None, 0)
        if succeeded:
            success_count += len(invocations)
            max_output_bytes = max(max_output_bytes, output_bytes)
            found, found_primary = context_anchor_paths(output)
            anchors.update(found)
            primary.update(found_primary)
        else:
            error_count += len(invocations)
    return {
        "memory_query_count": len(calls),
        "memory_query_success_count": success_count,
        "memory_query_error_count": error_count,
        "memory_query_total_output_bytes": total_output_bytes,
        "memory_query_total_output_token_estimate": token_estimate(total_output_bytes),
        "memory_context_bytes": max_output_bytes,
        "memory_context_token_estimate": token_estimate(max_output_bytes),
        "memory_context_metrics_reported": bool(calls) or completed_turn_reported(jsonl),
        "memory_query_metrics_reported": bool(command_events) or completed_turn_reported(jsonl),
        "memory_query_kinds": sorted({item["kind"] for item in calls}),
        "memory_query_digests": [item["query_digest"] for item in calls],
        "memory_query_anchor_paths": sorted(anchors),
        "memory_query_primary_anchor_paths": sorted(primary),
    }


def memory_invocations(value: Any) -> list[dict[str, str]]:
    command = " ".join(str(item) for item in value) if isinstance(value, list) else str(value or "")
    payload = unwrap_shell_payload(command)
    if payload is not None and payload != command:
        command = payload
    try:
        parts = shlex.split(command)
    except ValueError:
        return []
    result = []
    for index, item in enumerate(parts[:-1]):
        if Path(item.rstrip(";,|")).name != "agent_memory.py":
            continue
        kind = parts[index + 1].strip(";,|")
        if kind not in QUERY_COMMANDS:
            continue
        query = argument_after(parts[index + 2 :], "--query")
        result.append({
            "kind": kind,
            "query_digest": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        })
    return result


def argument_after(parts: list[str], flag: str) -> str:
    try:
        index = parts.index(flag)
    except ValueError:
        return ""
    return parts[index + 1] if index + 1 < len(parts) else ""


def context_anchor_paths(output: str) -> tuple[set[str], set[str]]:
    try:
        value = json.loads(output)
    except json.JSONDecodeError:
        return set(), set()
    handoff = value.get("query_handoff") if isinstance(value, dict) else None
    values = handoff.get("code_anchors") if isinstance(handoff, dict) else None
    anchors: set[str] = set()
    primary: set[str] = set()
    for item in values or []:
        if not isinstance(item, dict) or not item.get("file_path"):
            continue
        path = str(item["file_path"])
        anchors.add(path)
        if item.get("role") == "primary":
            primary.add(path)
    return anchors, primary


def token_estimate(byte_count: int) -> int:
    return max(1, (byte_count + 3) // 4) if byte_count else 0
