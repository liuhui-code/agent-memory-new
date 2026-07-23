# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any


MAX_QUERY_VARIANTS = 5
MAX_QUERY_LENGTH = 500
VARIANT_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


def expand_context_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for case in cases:
        variants = validated_query_variants(case)
        if variants is None:
            expanded.append({
                **case,
                "scenario_id": case["id"],
                "query_variant": "default",
            })
            continue
        for variant in variants:
            expanded.append({
                **case,
                "id": f"{case['id']}::{variant['id']}",
                "scenario_id": case["id"],
                "query_variant": variant["id"],
                "task": {**case["task"], "description": variant["description"]},
            })
    return expanded


def validated_query_variants(
    case: dict[str, Any],
) -> list[dict[str, str]] | None:
    value = case.get("query_variants")
    if value is None:
        return None
    if not isinstance(value, list) or not value or len(value) > MAX_QUERY_VARIANTS:
        raise SystemExit(
            f"context case {case['id']} query_variants must contain 1..{MAX_QUERY_VARIANTS} items"
        )
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise SystemExit(f"context case {case['id']} query variant must be an object")
        variant_id = str(item.get("id") or "").strip()
        description = str(item.get("description") or "").strip()
        if not VARIANT_ID.fullmatch(variant_id) or variant_id in seen:
            raise SystemExit(f"context case {case['id']} has invalid query variant id: {variant_id}")
        if not description or len(description) > MAX_QUERY_LENGTH:
            raise SystemExit(
                f"context case {case['id']} query variant description must contain 1..{MAX_QUERY_LENGTH} characters"
            )
        seen.add(variant_id)
        result.append({"id": variant_id, "description": description})
    return result
