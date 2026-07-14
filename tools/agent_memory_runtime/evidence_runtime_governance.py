# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from .models import Project


def evidence_runtime_summary(project: Project) -> dict[str, Any]:
    path = project.runtime_dir / "last_evidence_context.json"
    if not path.exists():
        return empty_summary()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**empty_summary(), "status": "unreadable"}
    chains = payload.get("evidence_chains") or []
    levels = Counter(
        str(chain.get("causal_evidence", {}).get("level") or "association")
        for chain in chains
        if isinstance(chain, dict)
    )
    execution = payload.get("retrieval_metadata", {}).get("query_execution") or {}
    gaps = payload.get("evidence_gaps") or []
    return {
        "status": "available",
        "query_scope": payload.get("goal_plan", {}).get("query_scope"),
        "round_count": int(execution.get("round_count") or 0),
        "stop_reason": execution.get("stop_reason"),
        "unique_evidence_count": int(execution.get("unique_evidence_count") or 0),
        "causal_levels": dict(levels),
        "weak_causal_chain_count": int(levels.get("association", 0)),
        "rejected_chain_count": int(levels.get("rejected", 0)),
        "evidence_gap_count": len(gaps),
        "evidence_gap_kinds": [str(gap.get("kind") or "unknown") for gap in gaps[:8] if isinstance(gap, dict)],
    }


def empty_summary() -> dict[str, Any]:
    return {
        "status": "missing",
        "query_scope": None,
        "round_count": 0,
        "stop_reason": None,
        "unique_evidence_count": 0,
        "causal_levels": {},
        "weak_causal_chain_count": 0,
        "rejected_chain_count": 0,
        "evidence_gap_count": 0,
        "evidence_gap_kinds": [],
    }
