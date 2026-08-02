# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any


MAX_QUERY_VARIANTS = 5
MAX_QUERY_LENGTH = 500
VARIANT_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
INVESTIGATION_STAGES = {"orientation", "focused"}
ORACLE_OVERRIDE_FIELDS = {"expected_files", "forbidden_files", "context_requirements"}


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
                "investigation_stage": variant.get("investigation_stage"),
                "task": {**case["task"], "description": variant["description"]},
                "oracle": variant_oracle(case["oracle"], variant.get("oracle_override")),
            })
    return expanded


def validated_query_variants(
    case: dict[str, Any],
) -> list[dict[str, Any]] | None:
    value = case.get("query_variants")
    if value is None:
        return None
    if not isinstance(value, list) or not value or len(value) > MAX_QUERY_VARIANTS:
        raise SystemExit(
            f"context case {case['id']} query_variants must contain 1..{MAX_QUERY_VARIANTS} items"
        )
    result: list[dict[str, Any]] = []
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
        stage = str(item.get("investigation_stage") or "").strip()
        override = item.get("oracle_override")
        if stage and stage not in INVESTIGATION_STAGES:
            raise SystemExit(
                f"context case {case['id']} has unsupported investigation_stage: {stage}"
            )
        if override is not None and not stage:
            raise SystemExit(
                f"context case {case['id']} oracle_override requires investigation_stage"
            )
        normalized_override = validated_oracle_override(case["id"], override)
        seen.add(variant_id)
        result.append({
            "id": variant_id,
            "description": description,
            **({"investigation_stage": stage} if stage else {}),
            **({"oracle_override": normalized_override} if normalized_override else {}),
        })
    return result


def validated_oracle_override(case_id: str, value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SystemExit(f"context case {case_id} oracle_override must be an object")
    unsupported = sorted(set(value) - ORACLE_OVERRIDE_FIELDS)
    if unsupported:
        raise SystemExit(
            f"context case {case_id} oracle_override has unsupported fields: "
            + ", ".join(unsupported)
        )
    result: dict[str, Any] = {}
    for key in ("expected_files", "forbidden_files"):
        if key not in value:
            continue
        items = value[key]
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise SystemExit(f"context case {case_id} oracle_override.{key} must be a string list")
        normalized = list(dict.fromkeys(item.strip() for item in items if item.strip()))
        if key == "expected_files" and not normalized:
            raise SystemExit(
                f"context case {case_id} oracle_override.expected_files cannot be empty"
            )
        result[key] = normalized
    requirements = value.get("context_requirements")
    if requirements is not None:
        if not isinstance(requirements, dict):
            raise SystemExit(
                f"context case {case_id} oracle_override.context_requirements must be an object"
            )
        result["context_requirements"] = dict(requirements)
    return result


def variant_oracle(base: dict[str, Any], override: Any) -> dict[str, Any]:
    if not isinstance(override, dict) or not override:
        return base
    merged = {**base, **override}
    if "context_requirements" in override:
        base_requirements = base.get("context_requirements")
        merged["context_requirements"] = {
            **(base_requirements if isinstance(base_requirements, dict) else {}),
            **override["context_requirements"],
        }
    return merged
