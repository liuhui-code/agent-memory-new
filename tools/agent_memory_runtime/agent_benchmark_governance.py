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
    return {
        "status": "available",
        "quality_gate": data.get("quality_gate"),
        "case_count": int(summary.get("case_count") or 0),
        "suite": summary.get("suite"),
        "context_agent_outcome_delta": uplift.get("agent_outcome_score_delta"),
        "context_agent_root_cause_delta": uplift.get("agent_root_cause_accuracy_delta"),
        "token_savings": uplift.get("token_savings"),
        "recorded_at": data.get("recorded_at"),
    }


def empty_summary() -> dict[str, Any]:
    return {
        "status": "missing",
        "quality_gate": None,
        "case_count": 0,
        "suite": None,
        "context_agent_outcome_delta": None,
        "context_agent_root_cause_delta": None,
        "token_savings": None,
        "recorded_at": None,
    }
