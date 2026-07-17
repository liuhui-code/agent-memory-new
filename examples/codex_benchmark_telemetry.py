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
SHELL_NAMES = {"bash", "sh", "zsh"}


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
    return total if command_events else None


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
    if isinstance(value, list):
        command = " ".join(str(item) for item in value)
    else:
        command = str(value or "")
    shell_payload = unwrap_shell_payload(command)
    if shell_payload is not None and shell_payload != command:
        return search_invocations(shell_payload)
    return len(SEARCH_COMMAND.findall(command))


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
