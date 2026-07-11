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
        token_estimates = [int(sample.get("token_estimate") or 0) for sample in operation_samples]
        scores = [float(sample.get("performance_score") or 0.0) for sample in operation_samples]
        latest = operation_samples[-1]
        avg_score = clamp_score(sum(scores) / len(scores)) if scores else 0.0
        operations[operation] = {
            "sample_count": len(operation_samples),
            "target_p95_ms": TARGET_P95_MS.get(operation, 1500.0),
            "p50_elapsed_ms": percentile(latencies, 0.50),
            "p95_elapsed_ms": percentile(latencies, 0.95),
            "average_token_estimate": int(sum(token_estimates) / len(token_estimates)) if token_estimates else 0,
            "max_token_estimate": max(token_estimates) if token_estimates else 0,
            "token_budget": TOKEN_BUDGET,
            "average_performance_score": avg_score,
            "performance_band": score_band(avg_score),
            "latest_status": latest.get("status", "ok"),
        }
    return {
        "sample_count": len(samples),
        "sample_limit": PERFORMANCE_SAMPLE_LIMIT,
        "operations": operations,
    }


def build_runtime_performance_actions(summary: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for operation, stats in (summary.get("operations") or {}).items():
        target_p95 = float(stats.get("target_p95_ms") or TARGET_P95_MS.get(operation, 1500.0))
        p95_elapsed = float(stats.get("p95_elapsed_ms") or 0.0)
        band = str(stats.get("performance_band") or "unknown")
        latest_status = str(stats.get("latest_status") or "ok")
        max_tokens = int(stats.get("max_token_estimate") or 0)
        token_budget = int(stats.get("token_budget") or TOKEN_BUDGET)
        breach_reasons: list[str] = []
        if p95_elapsed > target_p95:
            breach_reasons.append("p95 latency exceeds local target")
        if max_tokens > token_budget:
            breach_reasons.append("payload token estimate exceeds budget")
        if latest_status != "ok":
            breach_reasons.append("latest operation status is not ok")
        if band in {"poor", "watch"}:
            breach_reasons.append("average performance band requires review")
        if not breach_reasons:
            continue
        actions.append(
            {
                "action": "review_runtime_performance_budget",
                "governance_lane": "runtime_performance",
                "type": "runtime_performance",
                "id": None,
                "operation": operation,
                "reason": "; ".join(breach_reasons),
                "risk": "low",
                "requires_confirmation": False,
                "sample_count": stats.get("sample_count", 0),
                "p95_elapsed_ms": p95_elapsed,
                "target_p95_ms": target_p95,
                "max_token_estimate": max_tokens,
                "token_budget": token_budget,
                "latest_status": latest_status,
                "performance_band": band,
                "suggested_actions": [
                    "tighten_query_limits",
                    "review_noisy_memory_records",
                    "refresh_or_archive_stale_context",
                    "split_expensive_maintenance_work",
                ],
            }
        )
    return actions


def monotonic_ms() -> float:
    return time.perf_counter() * 1000.0
