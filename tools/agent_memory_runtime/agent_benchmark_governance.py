# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .models import Project


def agent_benchmark_summary(project: Project) -> dict[str, Any]:
    path = project.runtime_dir / "last_agent_benchmark.json"
    if not path.exists():
        return empty_summary()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**empty_summary(), "status": "unreadable"}
    summary = data.get("summary") or {}
    uplift = data.get("context_uplift") or {}
    per_case = (data.get("efficiency_metrics") or {}).get("per_case") or []
    failed_cases = [
        str(item.get("case_id"))
        for item in per_case
        if isinstance(item, dict)
        and not all((item.get("checks") or {}).values())
    ]
    return {
        "status": "available",
        "quality_gate": data.get("quality_gate"),
        "efficiency_gate": data.get("efficiency_gate"),
        "promotion_gate": data.get("promotion_gate"),
        "case_count": int(summary.get("case_count") or 0),
        "suite": summary.get("suite"),
        "context_agent_outcome_delta": uplift.get("agent_outcome_score_delta"),
        "context_agent_root_cause_delta": uplift.get("agent_root_cause_accuracy_delta"),
        "token_savings": uplift.get("token_savings"),
        "token_overhead_ratio": (data.get("efficiency_metrics") or {}).get(
            "token_overhead_ratio"
        ),
        "elapsed_overhead_ratio": (data.get("efficiency_metrics") or {}).get(
            "elapsed_overhead_ratio"
        ),
        "source_read_amplification": (data.get("efficiency_metrics") or {}).get(
            "memory_source_read_amplification"
        ),
        "failed_case_efficiency_count": len(failed_cases),
        "failed_case_efficiency_ids": failed_cases,
        "recorded_at": data.get("recorded_at"),
    }


def empty_summary() -> dict[str, Any]:
    return {
        "status": "missing",
        "quality_gate": None,
        "efficiency_gate": None,
        "promotion_gate": None,
        "case_count": 0,
        "suite": None,
        "context_agent_outcome_delta": None,
        "context_agent_root_cause_delta": None,
        "token_savings": None,
        "token_overhead_ratio": None,
        "elapsed_overhead_ratio": None,
        "source_read_amplification": None,
        "failed_case_efficiency_count": 0,
        "failed_case_efficiency_ids": [],
        "recorded_at": None,
    }
