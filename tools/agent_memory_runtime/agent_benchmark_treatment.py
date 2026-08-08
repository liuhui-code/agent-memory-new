# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
from typing import Any

from .context_source_excerpt import redact_source_excerpt_bodies
from .source_exploration import exploration_contract


TREATMENT_SCHEMA = "agent-benchmark-treatment/v2"
SELECTIVE_TREATMENT_SCHEMA = "agent-benchmark-treatment/v3"
PRELOADED_TREATMENT_MODE = "preloaded-context"
SELECTIVE_TREATMENT_MODE = "selective-query-skill"
TREATMENT_MODES = (PRELOADED_TREATMENT_MODE, SELECTIVE_TREATMENT_MODE)
EXPOSURE_SCHEMA = "context-exposure/v1"
INVESTIGATION_SCHEMA = "shared-investigation/v1"


def investigation_contract() -> dict[str, Any]:
    contract = exploration_contract()
    return {
        "schema_version": INVESTIGATION_SCHEMA,
        "policy": contract["policy"],
        "limits": dict(contract["limits"]),
    }


def external_context_projection(value: dict[str, Any] | None) -> dict[str, Any] | None:
    return redact_source_excerpt_bodies(value) if isinstance(value, dict) else None


def context_exposure_manifest(value: Any, delivery: str) -> dict[str, Any]:
    encoded = canonical_json(value)
    shape = canonical_json(value_shape(value))
    return {
        "schema_version": EXPOSURE_SCHEMA,
        "delivery": delivery,
        "context_present": isinstance(value, dict),
        "payload_bytes": len(encoded),
        "payload_digest": hashlib.sha256(encoded).hexdigest(),
        "shape_digest": hashlib.sha256(shape).hexdigest(),
    }


def treatment_metadata(variant: str, context: dict[str, Any] | None) -> dict[str, Any]:
    contract = investigation_contract()
    return {
        "schema_version": TREATMENT_SCHEMA,
        "variant": variant,
        "context_present": isinstance(context, dict),
        "investigation_contract_digest": hashlib.sha256(
            canonical_json(contract)
        ).hexdigest(),
        "context_exposure": context_exposure_manifest(
            context, "external_metadata_only" if context is not None else "absent"
        ),
    }


def selective_treatment_metadata(
    variant: str,
    skill_digest: str | None,
    query_limit: int,
) -> dict[str, Any]:
    contract = investigation_contract()
    available = variant == "memory" and bool(skill_digest)
    return {
        "schema_version": SELECTIVE_TREATMENT_SCHEMA,
        "variant": variant,
        "context_present": False,
        "preloaded_context": False,
        "memory_delivery": "agent_selected_query_skill",
        "query_skill_available": available,
        "query_skill_digest": skill_digest if available else None,
        "query_limit": max(0, int(query_limit)),
        "investigation_contract_digest": hashlib.sha256(
            canonical_json(contract)
        ).hexdigest(),
    }


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def value_shape(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: value_shape(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [value_shape(item) for item in value]
    if value is None:
        return "null"
    return type(value).__name__
