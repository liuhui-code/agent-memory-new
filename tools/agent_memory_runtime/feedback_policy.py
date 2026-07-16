# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
from typing import Any


STABLE_REPEAT_COUNT = 2


def derived_event_key(prefix: str, task_id: str | None, parts: list[Any]) -> str | None:
    task = str(task_id or "").strip()
    if not task:
        return None
    material = "\n".join([prefix, task, *(str(part or "").strip() for part in parts)])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def stable_signal(rows: list[dict[str, Any]], intrinsic: bool = False) -> bool:
    if intrinsic or any(bool(row.get("verified")) for row in rows):
        return True
    identities = {
        str(row.get("task_id") or f"legacy-event:{row.get('id')}")
        for row in rows
    }
    return len(identities) >= STABLE_REPEAT_COUNT


def candidate_ids(rows: list[Any]) -> set[int]:
    return {int(row["id"]) for row in rows if row["id"] is not None}
