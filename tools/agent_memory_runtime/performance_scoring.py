# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .models import Project
from .scoring_models import clamp_score, score_band
from .storage import now_iso


PERFORMANCE_SAMPLE_LIMIT = 200
TARGET_P95_MS = {
    "maintain-health": 1500.0,
    "maintain-plan": 2500.0,
    "context": 800.0,
    "search": 1000.0,
}
TOKEN_BUDGET = 1500


def performance_sample_path(project: Project) -> Path:
    return project.runtime_dir / "performance_samples.jsonl"


def estimate_payload_tokens(payload: Any) -> int:
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return max(1, len(text) // 4)


def build_performance_sample(
    project: Project,
    operation: str,
    elapsed_ms: float,
    result_counts: dict[str, int] | None = None,
    token_estimate: int | None = None,
    status: str = "ok",
) -> dict[str, Any]:
    db_size = project.db_path.stat().st_size if project.db_path.exists() else 0
    token_value = int(token_estimate or 0)
    target_ms = TARGET_P95_MS.get(operation, 1500.0)
    latency_score = clamp_score(1.0 - max(0.0, elapsed_ms - target_ms) / max(target_ms, 1.0))
    token_score = clamp_score(1.0 - max(0, token_value - TOKEN_BUDGET) / TOKEN_BUDGET)
    status_score = 1.0 if status == "ok" else 0.2
    storage_score = 1.0 if db_size < 50_000_000 else 0.75 if db_size < 250_000_000 else 0.45
    score = clamp_score(latency_score * 0.45 + token_score * 0.25 + storage_score * 0.15 + status_score * 0.15)
    return {
        "timestamp": now_iso(),
        "project_id": project.project_id,
        "operation": operation,
        "elapsed_ms": round(elapsed_ms, 3),
        "result_counts": result_counts or {},
        "token_estimate": token_value,
        "db_size_bytes": db_size,
        "status": status,
        "performance_score": score,
        "performance_band": score_band(score),
    }


def append_performance_sample(project: Project, sample: dict[str, Any]) -> None:
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    path = performance_sample_path(project)
    samples = read_performance_samples(project)
    samples.append(sample)
    samples = samples[-PERFORMANCE_SAMPLE_LIMIT:]
    path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in samples) + "\n", encoding="utf-8")


def read_performance_samples(project: Project) -> list[dict[str, Any]]:
    path = performance_sample_path(project)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-PERFORMANCE_SAMPLE_LIMIT:]


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percent))
    return round(ordered[index], 3)


def build_runtime_performance_summary(project: Project) -> dict[str, Any]:
    samples = read_performance_samples(project)
    operations: dict[str, dict[str, Any]] = {}
    for operation in sorted({str(sample.get("operation")) for sample in samples if sample.get("operation")}):
        operation_samples = [sample for sample in samples if sample.get("operation") == operation]
        latencies = [float(sample.get("elapsed_ms") or 0.0) for sample in operation_samples]
        scores = [float(sample.get("performance_score") or 0.0) for sample in operation_samples]
        latest = operation_samples[-1]
        avg_score = clamp_score(sum(scores) / len(scores)) if scores else 0.0
        operations[operation] = {
            "sample_count": len(operation_samples),
            "p50_elapsed_ms": percentile(latencies, 0.50),
            "p95_elapsed_ms": percentile(latencies, 0.95),
            "average_performance_score": avg_score,
            "performance_band": score_band(avg_score),
            "latest_status": latest.get("status", "ok"),
        }
    return {
        "sample_count": len(samples),
        "sample_limit": PERFORMANCE_SAMPLE_LIMIT,
        "operations": operations,
    }


def monotonic_ms() -> float:
    return time.perf_counter() * 1000.0
