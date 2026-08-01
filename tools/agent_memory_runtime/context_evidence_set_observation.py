# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


def compact_callable_evidence_set(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "schema_version": str(value.get("schema_version") or ""),
        "mode": str(value.get("mode") or ""),
        "serving_projection_changed": bool(value.get("serving_projection_changed")),
        "target_scope": value.get("target_scope")
        if isinstance(value.get("target_scope"), dict) else {},
        "members": [compact_member(item) for item in records(value.get("members"))[:3]],
        "competition": value.get("competition")
        if isinstance(value.get("competition"), dict) else {},
        "calibration": value.get("calibration")
        if isinstance(value.get("calibration"), dict) else {},
        "boundary": str(value.get("boundary") or ""),
    }


def compact_member(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item[key]
        for key in (
            "position", "file_path", "symbol", "owner_kind", "source_locatable",
            "support_kinds", "excluded_by_query",
        )
        if item.get(key) not in (None, "", [])
    }


def records(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
