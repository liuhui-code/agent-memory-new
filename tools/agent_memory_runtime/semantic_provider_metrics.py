# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import Project
from .semantic_provider_protocol import provider_env_name
from .storage import now_iso


METRIC_FILE = "semantic_provider_runs.jsonl"
METRIC_LIMIT = 200


def append_provider_metric(project: Project, telemetry: dict[str, Any]) -> None:
    if not telemetry.get("provider_configured"):
        return
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    rows = read_provider_metrics(project)
    rows.append(compact_metric(telemetry))
    rows = rows[-METRIC_LIMIT:]
    provider_metric_path(project).write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in rows),
        encoding="utf-8",
    )


def read_provider_metrics(project: Project) -> list[dict[str, Any]]:
    path = provider_metric_path(project)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-METRIC_LIMIT:]:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def semantic_provider_health(project: Project) -> dict[str, Any]:
    rows = read_provider_metrics(project)
    exact = sum(item.get("status") == "exact" for item in rows)
    fallback = sum(item.get("status") == "fallback" for item in rows)
    failures = [item for item in rows if item.get("fallback_reason")]
    count = len(rows)
    configured_languages = [
        language for language in ("ArkTS", "TypeScript")
        if os.environ.get(provider_env_name(language))
    ]
    return {
        "sample_count": count,
        "configured_languages": configured_languages,
        "exact_successes": exact,
        "fallbacks": fallback,
        "exact_success_rate": round(exact / count, 4) if count else None,
        "fallback_rate": round(fallback / count, 4) if count else None,
        "recent_failure_reasons": [str(item.get("fallback_reason")) for item in failures[-5:]],
        "retention_limit": METRIC_LIMIT,
        "recent_runs": rows[-5:],
    }


def build_semantic_provider_actions(summary: dict[str, Any]) -> list[dict[str, Any]]:
    if int(summary.get("sample_count") or 0) < 2 or int(summary.get("fallbacks") or 0) < 2:
        return []
    return [{
        "action": "review_semantic_provider_failures",
        "governance_lane": "graph_quality",
        "type": "semantic_provider",
        "reason": "configured semantic provider repeatedly fell back to static analysis",
        "risk": "medium",
        "requires_confirmation": True,
        "failure_reasons": summary.get("recent_failure_reasons") or [],
        "command": None,
    }]


def compact_metric(telemetry: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": now_iso(),
        "language": telemetry.get("language"),
        "mode": telemetry.get("mode"),
        "status": telemetry.get("status"),
        "selected": telemetry.get("selected"),
        "provider_id": telemetry.get("provider_id"),
        "provider_version": telemetry.get("provider_version"),
        "toolchain": telemetry.get("toolchain"),
        "duration_ms": telemetry.get("duration_ms"),
        "output_bytes": telemetry.get("output_bytes"),
        "fallback_reason": telemetry.get("fallback_reason"),
    }


def provider_metric_path(project: Project) -> Path:
    return project.runtime_dir / METRIC_FILE
