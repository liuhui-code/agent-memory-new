# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .models import ACTIVE_STATUS, NON_QUERY_STATUSES


def row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def memory_warning(item: dict[str, Any]) -> str | None:
    status = item.get("status") or ACTIVE_STATUS
    if status in NON_QUERY_STATUSES:
        return "This memory is not active. Verify before use."
    confidence = item.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < 0.6:
        return "This memory has low confidence. Verify against current source files."
    if item.get("is_stale"):
        return "This memory is stale. Verify against current source files."
    return None


def output(data: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        if isinstance(data, dict):
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(data)


def table_for_type(kind: str) -> str:
    tables = {
        "semantic": "semantic_facts",
        "reflection": "reflections",
        "episode": "episodes",
        "code-file": "code_files",
        "code-symbol": "code_symbols",
        "code-log": "code_log_statements",
        "memory-edge": "memory_edges",
        "reflection-reuse": "reflection_reuse_events",
        "semantic-conflict": "semantic_conflicts",
    }
    if kind not in tables:
        raise SystemExit(f"unsupported type: {kind}")
    return tables[kind]


def parse_ids(raw: str) -> list[int]:
    ids = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not ids:
        raise SystemExit("--ids must contain at least one id")
    return ids
