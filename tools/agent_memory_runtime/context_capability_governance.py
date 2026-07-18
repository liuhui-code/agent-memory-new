# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .models import Project


def context_capability_summary(project: Project) -> dict[str, Any]:
    path = project.runtime_dir / "last_context_capability.json"
    if not path.exists():
        return empty_summary()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**empty_summary(), "status": "unreadable"}
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    profile = (
        data.get("capability_profile")
        if isinstance(data.get("capability_profile"), dict) else {}
    )
    code = profile.get("code_locator") if isinstance(profile.get("code_locator"), dict) else {}
    source = (
        profile.get("source_evidence")
        if isinstance(profile.get("source_evidence"), dict) else {}
    )
    robustness = (
        profile.get("query_robustness")
        if isinstance(profile.get("query_robustness"), dict) else {}
    )
    abstention = (
        profile.get("abstention")
        if isinstance(profile.get("abstention"), dict) else {}
    )
    failed_ids = [
        str(item.get("case_id"))
        for item in data.get("cases") or []
        if isinstance(item, dict) and item.get("status") == "fail"
    ]
    return {
        "status": "available",
        "system_context_gate": data.get("system_context_gate"),
        "case_count": int(summary.get("case_count") or 0),
        "failed_case_count": int(summary.get("failed_case_count") or 0),
        "failed_case_ids": failed_ids,
        "scenario_count": int(summary.get("scenario_count") or 0),
        "stable_scenario_count": int(summary.get("stable_scenario_count") or 0),
        "query_robustness_status": robustness.get("status"),
        "query_variant_pass_rate": summary.get("query_variant_pass_rate"),
        "anchor_recall": code.get("anchor_recall"),
        "primary_anchor_recall": code.get("primary_anchor_recall"),
        "expected_anchor_mrr": code.get("expected_anchor_mrr"),
        "source_evidence_status": source.get("status"),
        "source_excerpt_recall": source.get("source_excerpt_recall"),
        "source_span_recall": source.get("source_span_recall"),
        "abstention_status": abstention.get("status"),
        "average_context_tokens": summary.get("average_context_tokens"),
        "recorded_at": data.get("recorded_at"),
    }


def empty_summary() -> dict[str, Any]:
    return {
        "status": "missing",
        "system_context_gate": None,
        "case_count": 0,
        "failed_case_count": 0,
        "failed_case_ids": [],
        "scenario_count": 0,
        "stable_scenario_count": 0,
        "query_robustness_status": None,
        "query_variant_pass_rate": None,
        "anchor_recall": None,
        "primary_anchor_recall": None,
        "expected_anchor_mrr": None,
        "source_evidence_status": None,
        "source_excerpt_recall": None,
        "source_span_recall": None,
        "abstention_status": None,
        "average_context_tokens": None,
        "recorded_at": None,
    }
