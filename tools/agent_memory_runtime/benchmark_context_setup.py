# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .benchmark_memory import run_runtime


MAX_FIXTURE_REFLECTIONS = 8
MAX_FIXTURE_PAYLOAD_BYTES = 32_000


def apply_context_setup(
    memory: dict[str, Any],
    setup: Any,
    timeout: int,
) -> dict[str, int]:
    reflections = validated_reflections(setup)
    if not reflections:
        return {"reflection_count": 0}
    runtime = required_path(memory, "runtime")
    project = required_text(memory, "project")
    memory_home = required_text(memory, "memory_home")
    common = ["--project", project, "--memory-home", memory_home]
    for payload in reflections:
        run_runtime(
            runtime,
            [
                "reflect",
                *common,
                "--payload",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            ],
            timeout,
        )
    return {"reflection_count": len(reflections)}


def validated_reflections(setup: Any) -> list[dict[str, Any]]:
    if setup in (None, {}):
        return []
    if not isinstance(setup, dict):
        raise SystemExit("context_setup must be an object")
    unknown = set(setup) - {"reflections"}
    if unknown:
        raise SystemExit(f"unsupported context_setup fields: {', '.join(sorted(unknown))}")
    values = setup.get("reflections") or []
    if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
        raise SystemExit("context_setup.reflections must be an object list")
    if len(values) > MAX_FIXTURE_REFLECTIONS:
        raise SystemExit(
            f"context_setup.reflections exceeds {MAX_FIXTURE_REFLECTIONS} records"
        )
    encoded = json.dumps(values, ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_FIXTURE_PAYLOAD_BYTES:
        raise SystemExit(
            f"context_setup.reflections exceeds {MAX_FIXTURE_PAYLOAD_BYTES} bytes"
        )
    return [dict(item) for item in values]


def required_text(memory: dict[str, Any], key: str) -> str:
    value = memory.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"context setup requires memory {key}")
    return value.strip()


def required_path(memory: dict[str, Any], key: str) -> Path:
    path = Path(required_text(memory, key)).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"context setup runtime not found: {path}")
    return path
