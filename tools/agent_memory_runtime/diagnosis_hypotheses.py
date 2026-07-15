# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .models import Project
from .text import unique_list


MAX_HYPOTHESES = 5


def build_evidence_hypothesis_ledger(
    query: str,
    chains: list[dict[str, Any]],
    gaps: list[dict[str, str]],
) -> dict[str, Any]:
    hypotheses: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chain in chains:
        nodes = chain.get("nodes") or []
        if not nodes:
            continue
        target = nodes[-1]
        statement = hypothesis_statement(target)
        if statement in seen:
            continue
        seen.add(statement)
        causal = chain.get("causal_evidence") or {}
        level = str(causal.get("level") or "association")
        hypotheses.append({
            "hypothesis_id": f"h{len(hypotheses) + 1}",
            "statement": statement,
            "status": hypothesis_status(level),
            "causal_level": level,
            "supporting_evidence": [node.get("evidence_id") for node in nodes if node.get("evidence_id")],
            "counter_evidence": list(causal.get("counter_evidence") or [])[:5],
            "missing_evidence": missing_evidence(level),
            "next_discriminating_check": next_check(level, target),
        })
        if len(hypotheses) >= MAX_HYPOTHESES:
            break
    if not hypotheses:
        actions = [gap.get("action") for gap in gaps if gap.get("action")]
        hypotheses.append({
            "hypothesis_id": "h1",
            "statement": "No grounded root-cause hypothesis is available yet",
            "status": "open",
            "causal_level": "association",
            "supporting_evidence": [],
            "counter_evidence": [],
            "missing_evidence": unique_list(actions)[:4] or ["current source or runtime evidence"],
            "next_discriminating_check": actions[0] if actions else "collect a narrow runtime log slice",
        })
    return ledger_payload(query, "evidence-context", hypotheses)


def build_runtime_hypothesis_ledger(
    query: str,
    events: list[dict[str, Any]],
    span_graph: dict[str, Any],
) -> dict[str, Any]:
    paths = span_graph.get("causal_paths") or []
    path_supported = any(
        path.get("correlation_verified") and path.get("temporal_order_verified")
        for path in paths
    )
    hypotheses: list[dict[str, Any]] = []
    seen: set[str] = set()
    ordered = sorted(events, key=lambda item: int(item.get("line_number") or 0))
    for event in ordered:
        signal = first_text(event, "error_code", "reason", "event_name", "event_type")
        if not signal or signal in seen:
            continue
        seen.add(signal)
        line = int(event.get("line_number") or 0)
        level = "supported" if path_supported and event.get("trace_id") else "association"
        hypotheses.append({
            "hypothesis_id": f"h{len(hypotheses) + 1}",
            "statement": f"Runtime signal '{signal}' participates in the failure path",
            "status": hypothesis_status(level),
            "causal_level": level,
            "supporting_evidence": [f"runtime:event:{line}"],
            "counter_evidence": [],
            "missing_evidence": missing_evidence(level),
            "next_discriminating_check": (
                "inspect the code-log anchor and parent span for this event"
                if level == "association"
                else "apply one targeted intervention and compare the outcome"
            ),
        })
        if len(hypotheses) >= MAX_HYPOTHESES:
            break
    if not hypotheses:
        hypotheses.append({
            "hypothesis_id": "h1",
            "statement": "The supplied log contains no grounded failure signal",
            "status": "open",
            "causal_level": "association",
            "supporting_evidence": [],
            "counter_evidence": [],
            "missing_evidence": ["error code, event name, reason, or failed result"],
            "next_discriminating_check": "add a structured failure event near the reported symptom",
        })
    return ledger_payload(query, "runtime-log", hypotheses)


def persist_hypothesis_ledger(project: Project, ledger: dict[str, Any]) -> None:
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_hypothesis_ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def ledger_payload(query: str, source: str, hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = {item["status"] for item in hypotheses}
    if "verified" in statuses:
        stop_reason = "verified_hypothesis_available"
    elif statuses == {"rejected"}:
        stop_reason = "all_hypotheses_rejected"
    else:
        stop_reason = "continue_with_discriminating_check"
    return {
        "schema_version": "diagnosis-hypothesis-ledger/v1",
        "query": query,
        "generated_from": source,
        "hypotheses": hypotheses,
        "stop_reason": stop_reason,
        "audit": {"bounded": True, "persisted": False, "hypothesis_limit": MAX_HYPOTHESES},
    }


def hypothesis_statement(node: dict[str, Any]) -> str:
    title = str(node.get("title") or node.get("source") or "retrieved evidence")
    location = str(node.get("location") or "").strip()
    return f"Investigate {title} at {location}" if location else f"Investigate {title}"


def hypothesis_status(level: str) -> str:
    return {
        "verified": "verified",
        "supported": "supported",
        "rejected": "rejected",
    }.get(level, "open")


def missing_evidence(level: str) -> list[str]:
    if level == "verified":
        return []
    if level == "supported":
        return ["targeted intervention", "before/after verification evidence"]
    if level == "rejected":
        return []
    return ["connected mechanism", "shared runtime identity", "verified temporal order"]


def next_check(level: str, target: dict[str, Any]) -> str:
    location = str(target.get("location") or target.get("title") or "the candidate").strip()
    if level == "verified":
        return "preserve the regression test and close the incident"
    if level == "rejected":
        return "exclude this candidate and inspect the next independent path"
    if level == "supported":
        return f"change only {location} and compare the same failure metric"
    return f"inspect {location} and capture its trace/span identity before changing code"


def first_text(item: dict[str, Any], *keys: str) -> str:
    return next((str(item.get(key)).strip() for key in keys if item.get(key)), "")
