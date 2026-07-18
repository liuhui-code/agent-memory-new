# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any


SEARCH_COMMAND = re.compile(
    r"(?:^|&&|\|\||[;|\n(])\s*(?:command\s+)?"
    r"(?:\S+/)?(?:rg|grep|egrep|fgrep|find|fd)(?=\s|$)"
)
READ_COMMAND = re.compile(
    r"(?:^|&&|\|\||[;|\n(])\s*(?:command\s+)?"
    r"(?:\S+/)?(?:cat|sed|head|tail|nl|bat)(?=\s|$)"
)
SHELL_NAMES = {"bash", "sh", "zsh"}


def codex_cost_metrics(jsonl: str) -> dict[str, Any]:
    usage = extract_usage_metrics(jsonl)
    commands = extract_command_metrics(jsonl)
    return {
        **usage,
        **commands,
        "token_estimate": usage["model_input_tokens"] + usage["model_output_tokens"],
        "cost_metrics_reported": usage["usage_metrics_reported"],
    }


def source_search_metrics(jsonl: str, result: dict[str, Any]) -> dict[str, Any]:
    measured = extract_source_search_count(jsonl)
    if measured is None:
        return {
            "source_search_count": max(0, int(result.get("source_search_count") or 0)),
            "source_search_count_source": "agent_reported",
        }
    return {
        "source_search_count": measured,
        "source_search_count_source": "runner_telemetry",
    }


def extract_source_search_count(jsonl: str) -> int | None:
    total = 0
    command_events = 0
    seen_ids: set[str] = set()
    for line in jsonl.splitlines():
        item = completed_command_item(line)
        if item is None:
            continue
        item_id = str(item.get("id") or "")
        if item_id and item_id in seen_ids:
            continue
        if item_id:
            seen_ids.add(item_id)
        command_events += 1
        total += search_invocations(item.get("command"))
    return total if command_events or completed_turn_reported(jsonl) else None


def completed_turn_reported(jsonl: str) -> bool:
    for line in jsonl.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(event, dict)
            and event.get("type") == "turn.completed"
            and isinstance(event.get("usage"), dict)
        ):
            return True
    return False


def extract_usage_metrics(jsonl: str) -> dict[str, Any]:
    candidates = []
    for line in jsonl.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidates.extend(usage_candidates(event))
    usage = max(
        candidates,
        key=lambda item: item["model_input_tokens"] + item["model_output_tokens"],
        default=None,
    )
    if usage is not None:
        return {**usage, "usage_metrics_reported": True}
    return {
        "model_input_tokens": 0,
        "model_cached_input_tokens": 0,
        "model_uncached_input_tokens": 0,
        "model_output_tokens": 0,
        "model_reasoning_tokens": 0,
        "usage_metrics_reported": False,
    }


def usage_candidates(value: Any) -> list[dict[str, int]]:
    if isinstance(value, list):
        return [candidate for item in value for candidate in usage_candidates(item)]
    if not isinstance(value, dict):
        return []
    result = [candidate_metrics(value)] if has_token_usage(value) else []
    return result + [
        candidate
        for item in value.values()
        for candidate in usage_candidates(item)
    ]


def has_token_usage(value: dict[str, Any]) -> bool:
    return any(key in value for key in ("input_tokens", "output_tokens"))


def candidate_metrics(value: dict[str, Any]) -> dict[str, int]:
    input_tokens = metric_int(value, "input_tokens")
    cached_tokens = max(
        metric_int(value, "cached_input_tokens"),
        metric_int(value, "cache_read_input_tokens"),
        nested_metric(value, "input_tokens_details", "cached_tokens"),
    )
    output_tokens = metric_int(value, "output_tokens")
    reasoning_tokens = max(
        metric_int(value, "reasoning_output_tokens"),
        nested_metric(value, "output_tokens_details", "reasoning_tokens"),
    )
    return {
        "model_input_tokens": input_tokens,
        "model_cached_input_tokens": cached_tokens,
        "model_uncached_input_tokens": max(0, input_tokens - cached_tokens),
        "model_output_tokens": output_tokens,
        "model_reasoning_tokens": reasoning_tokens,
    }


def extract_command_metrics(jsonl: str) -> dict[str, int]:
    items = unique_completed_command_items(jsonl)
    output_bytes = 0
    read_count = 0
    read_output_bytes = 0
    errors = 0
    search_misses = 0
    search_errors = 0
    read_errors = 0
    other_errors = 0
    for item in items:
        output = str(item.get("aggregated_output") or item.get("output") or "")
        encoded_size = len(output.encode("utf-8"))
        output_bytes += encoded_size
        reads = command_invocations(item.get("command"), READ_COMMAND)
        read_count += reads
        if reads:
            read_output_bytes += encoded_size
        exit_code = item.get("exit_code")
        if exit_code == 1 and search_invocations(item.get("command")):
            search_misses += 1
        elif isinstance(exit_code, int) and exit_code != 0:
            errors += 1
            if search_invocations(item.get("command")):
                search_errors += 1
            elif reads:
                read_errors += 1
            else:
                other_errors += 1
    return {
        "command_count": len(items),
        "command_output_bytes": output_bytes,
        "source_read_count": read_count,
        "source_read_output_bytes": read_output_bytes,
        "tool_error_count": errors,
        "source_search_miss_count": search_misses,
        "source_search_error_count": search_errors,
        "source_read_error_count": read_errors,
        "other_tool_error_count": other_errors,
    }


def unique_completed_command_items(jsonl: str) -> list[dict[str, Any]]:
    result = []
    seen_ids: set[str] = set()
    for line in jsonl.splitlines():
        item = completed_command_item(line)
        if item is None:
            continue
        item_id = str(item.get("id") or "")
        if item_id and item_id in seen_ids:
            continue
        if item_id:
            seen_ids.add(item_id)
        result.append(item)
    return result


def completed_command_item(line: str) -> dict[str, Any] | None:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(event, dict) or event.get("type") != "item.completed":
        return None
    item = event.get("item")
    if not isinstance(item, dict) or item.get("type") != "command_execution":
        return None
    return item


def search_invocations(value: Any) -> int:
    return command_invocations(value, SEARCH_COMMAND)


def command_invocations(value: Any, pattern: re.Pattern[str]) -> int:
    if isinstance(value, list):
        command = " ".join(str(item) for item in value)
    else:
        command = str(value or "")
    shell_payload = unwrap_shell_payload(command)
    if shell_payload is not None and shell_payload != command:
        return command_invocations(shell_payload, pattern)
    return len(pattern.findall(command))


def unwrap_shell_payload(command: str) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    if not parts or Path(parts[0]).name not in SHELL_NAMES:
        return None
    for flag in ("-lc", "-c"):
        if flag in parts:
            index = parts.index(flag)
            return parts[index + 1] if index + 1 < len(parts) else None
    return None


def metric_int(value: dict[str, Any], key: str) -> int:
    item = value.get(key)
    return max(0, int(item)) if isinstance(item, (int, float)) else 0


def nested_metric(value: dict[str, Any], parent: str, key: str) -> int:
    item = value.get(parent)
    return metric_int(item, key) if isinstance(item, dict) else 0
