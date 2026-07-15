# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .evidence_models import EvidenceItem, GoalPlan
from .text import unique_list


AUTHORITY_SCORE = {
    "changed_source": 1.0,
    "current_source": 1.0,
    "learned_code_anchor": 0.92,
    "code_log_anchor": 0.88,
    "graph_relation": 0.9,
    "observed_incident": 0.85,
    "aggregate_evidence": 0.7,
    "verified_experience": 0.75,
    "advisory_memory": 0.45,
}


def fuse_evidence(items: list[EvidenceItem], plan: GoalPlan) -> list[EvidenceItem]:
    maxima: dict[str, float] = defaultdict(float)
    for item in items:
        maxima[item.source] = max(maxima[item.source], max(item.original_score, 0.0))
    anchor_counts = _anchor_counts(items)
    for item in items:
        relevance = item.original_score / maxima[item.source] if maxima[item.source] else 0.0
        goal_fit = plan.source_weights.get(item.source, 0.25)
        authority = AUTHORITY_SCORE.get(item.authority, 0.4)
        trust = _trust(item)
        graph = _graph_support(item, anchor_counts)
        completeness = _completeness(item)
        freshness = _freshness(item)
        item.score_components = {
            "relevance": relevance * 32.0,
            "goal_fit": goal_fit * 18.0,
            "authority": authority * 18.0,
            "trust": trust * 12.0,
            "graph_support": graph * 10.0,
            "completeness": completeness * 5.0,
            "freshness": freshness * 5.0,
        }
        item.penalties = _penalties(item)
        item.final_score = min(100.0, max(
            0.0,
            sum(item.score_components.values()) - sum(item.penalties.values()),
        ))
        item.reasons = unique_list(item.reasons + _score_reasons(item))
    items.sort(
        key=lambda item: (item.final_score, AUTHORITY_SCORE.get(item.authority, 0), item.record_id or 0),
        reverse=True,
    )
    return select_diverse_evidence(items, plan.max_items)


def select_diverse_evidence(items: list[EvidenceItem], limit: int) -> list[EvidenceItem]:
    source_caps = {"reflection": 3, "semantic": 3, "episode": 2, "code": 7, "log": 5, "edge": 5, "incident": 4}
    source_counts: dict[str, int] = defaultdict(int)
    location_counts: dict[str, int] = defaultdict(int)
    pattern_counts: dict[str, int] = defaultdict(int)
    selected: list[EvidenceItem] = []
    for item in items:
        location = (item.location or "").casefold()
        pattern = " ".join(item.title.casefold().split())[:100]
        if source_counts[item.source] >= source_caps.get(item.source, 3):
            continue
        if location and location_counts[location] >= 3:
            continue
        if pattern and pattern_counts[pattern] >= 1:
            continue
        selected.append(item)
        source_counts[item.source] += 1
        if location:
            location_counts[location] += 1
        if pattern:
            pattern_counts[pattern] += 1
        if len(selected) >= limit:
            break
    return selected


def evidence_tiers(items: list[EvidenceItem]) -> dict[str, list[dict[str, Any]]]:
    tiers: dict[str, list[dict[str, Any]]] = {"direct": [], "supporting": [], "advisory": []}
    for item in items:
        if item.authority in {"changed_source", "current_source", "learned_code_anchor", "code_log_anchor", "graph_relation"} and item.final_score >= 55:
            tier = "direct"
        elif item.authority in {"observed_incident", "verified_experience"} or item.final_score >= 60:
            tier = "supporting"
        else:
            tier = "advisory"
        tiers[tier].append(item.to_dict())
    return tiers


def build_evidence_chains(items: list[EvidenceItem], limit: int = 5) -> list[dict[str, Any]]:
    direct = [
        item for item in items
        if item.authority in {"changed_source", "current_source", "learned_code_anchor", "code_log_anchor"}
    ]
    edges = [item for item in items if item.source == "edge"]
    incidents = [item for item in items if item.source == "incident"]
    experiences = [item for item in items if item.source in {"reflection", "semantic"}]
    chains: list[dict[str, Any]] = []
    for anchor in direct[:limit]:
        linked = [item for item in edges + incidents + experiences if _shares_anchor(anchor, item)]
        chain_items = [anchor, *linked[:2]]
        nodes = [compact_chain_node(item) for item in chain_items]
        causal = classify_causal_evidence(chain_items)
        chains.append(
            {
                "chain_id": f"chain:{len(chains) + 1}",
                "confidence": causal_confidence(nodes, causal["level"]),
                "nodes": nodes,
                "reason": "shared code, symbol, function, or graph anchor",
                "causal_evidence": causal,
            }
        )
    if not chains:
        for incident in incidents[:limit]:
            causal = classify_causal_evidence([incident])
            chains.append(
                {
                    "chain_id": f"chain:{len(chains) + 1}",
                    "confidence": causal_confidence([compact_chain_node(incident)], causal["level"]),
                    "nodes": [compact_chain_node(incident)],
                    "reason": "incident evidence without a retrieved current-code anchor",
                    "causal_evidence": causal,
                }
            )
    return chains[:limit]


def evidence_gaps(items: list[EvidenceItem], plan: GoalPlan) -> list[dict[str, str]]:
    sources = {item.source for item in items}
    gaps: list[dict[str, str]] = []
    if "code" not in sources:
        gaps.append({"kind": "missing_code_anchor", "action": "learn or inspect the narrow current source scope"})
    if plan.goal == "diagnosis" and not ({"log", "incident"} & sources):
        gaps.append({"kind": "missing_runtime_evidence", "action": "collect a temporary log slice or incident trace"})
    if plan.goal == "change_impact" and "edge" not in sources:
        gaps.append({"kind": "missing_dependency_edge", "action": "refresh the learned code graph for changed files"})
    if not ({"reflection", "semantic"} & sources):
        gaps.append({"kind": "missing_memory_support", "action": "continue with source evidence; reflect after verification"})
    return gaps


def compact_chain_node(item: EvidenceItem) -> dict[str, Any]:
    return {
        "evidence_id": item.evidence_id,
        "source": item.source,
        "title": item.title,
        "location": item.location,
        "score": round(item.final_score, 3),
    }


def classify_causal_evidence(items: list[EvidenceItem]) -> dict[str, Any]:
    signals: list[str] = []
    counter_evidence: list[str] = []
    has_direct = any(item.authority in {"changed_source", "current_source", "learned_code_anchor", "code_log_anchor"} for item in items)
    mechanism_connected = connected_mechanism(items)
    correlation_connected = shared_runtime_correlation(items)
    temporal_verified = any(temporal_evidence(item) for item in items)
    resolution_observed = any(resolution_evidence(item) for item in items)
    if mechanism_connected:
        signals.append("structural_mechanism")
    if any(item.source in {"log", "incident"} for item in items):
        signals.append("runtime_observation")
    if correlation_connected:
        signals.append("runtime_correlation")
    if temporal_verified:
        signals.append("temporal_precedence")
    if resolution_observed:
        signals.append("resolution_observed")
    verified = any(verified_evidence(item) for item in items)
    rejected = any(rejected_evidence(item) for item in items)
    for item in items:
        counter_evidence.extend(item.warnings)
        for key in ("negative_preconditions", "does_not_apply_to"):
            value = item.raw.get(key)
            if value:
                counter_evidence.append(str(value))
    if rejected:
        level = "rejected"
        signals.append("contradicted")
    elif verified:
        level = "verified"
        signals.append("intervention_and_outcome_verified")
    elif resolution_observed or (
        has_direct and mechanism_connected and correlation_connected and temporal_verified
    ):
        level = "supported"
    else:
        level = "association"
    return {
        "level": level,
        "signals": unique_list(signals),
        "counter_evidence": unique_list(counter_evidence)[:5],
        "notice": (
            "Association is only a lead. Supported requires a connected mechanism with explicit "
            "runtime identity and temporal order, or an observed resolution. Verified additionally "
            "requires an intervention and before/after verification evidence."
        ),
    }


def causal_confidence(nodes: list[dict[str, Any]], level: str) -> float:
    base = min((float(node.get("score") or 0.0) for node in nodes), default=0.0) / 100.0
    cap = {"association": 0.35, "supported": 0.7, "verified": 0.95, "rejected": 0.0}[level]
    return round(min(base, cap), 3)


def runtime_correlation(item: EvidenceItem) -> bool:
    raw = item.raw
    if verified_span_paths(raw, "correlation_verified"):
        return True
    return any(raw.get(key) for key in ("trace_id", "request_id", "session_id"))


def shared_runtime_correlation(items: list[EvidenceItem]) -> bool:
    if any(verified_span_paths(item.raw, "correlation_verified") for item in items):
        return True
    seen: set[tuple[str, str]] = set()
    for item in items:
        for key in ("trace_id", "request_id", "session_id"):
            value = str(item.raw.get(key) or "").strip()
            identity = (key, value)
            if value and identity in seen:
                return True
            if value:
                seen.add(identity)
    return False


def temporal_evidence(item: EvidenceItem) -> bool:
    raw = item.raw
    return bool(raw.get("temporal_order_verified")) or verified_span_paths(
        raw, "temporal_order_verified"
    )


def verified_evidence(item: EvidenceItem) -> bool:
    raw = item.raw
    if item.source == "incident":
        return resolution_evidence(item) and all(
            str(raw.get(key) or "").strip()
            for key in ("intervention", "verification_evidence")
        )
    if item.source == "reflection":
        return bool(raw.get("verification_method")) and raw.get("last_outcome") in {"helped", "success"}
    return False


def resolution_evidence(item: EvidenceItem) -> bool:
    raw = item.raw
    return (
        item.source == "incident"
        and raw.get("status") == "resolved"
        and bool(str(raw.get("resolution") or "").strip())
    )


def connected_mechanism(items: list[EvidenceItem]) -> bool:
    direct = [
        item for item in items
        if item.authority in {"changed_source", "current_source", "learned_code_anchor", "code_log_anchor"}
    ]
    edges = [item for item in items if item.source == "edge"]
    return any(_shares_anchor(anchor, edge) for anchor in direct for edge in edges)


def verified_span_paths(raw: dict[str, Any], field: str) -> bool:
    graph = raw.get("span_graph") or {}
    if isinstance(graph, str):
        return False
    paths = graph.get("relation_paths") or graph.get("causal_paths") or []
    return any(bool(path.get(field)) for path in paths)


def rejected_evidence(item: EvidenceItem) -> bool:
    raw = item.raw
    return raw.get("status") in {"stale", "ignored", "rejected"} or raw.get("last_outcome") in {"misleading", "superseded"}


def _anchor_counts(items: list[EvidenceItem]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        for anchor in item.anchors:
            counts[anchor] += 1
    return counts


def _graph_support(item: EvidenceItem, counts: dict[str, int]) -> float:
    if item.source == "edge":
        return 1.0
    return min(1.0, sum(max(0, counts[anchor] - 1) for anchor in item.anchors) / 2.0)


def _trust(item: EvidenceItem) -> float:
    raw = item.raw
    for key in ("trust_score", "confidence", "quality_score", "maturity_score"):
        value = raw.get(key)
        if isinstance(value, (int, float)):
            return min(1.0, max(0.0, float(value)))
    return {
        "changed_source": 0.95,
        "current_source": 0.95,
        "learned_code_anchor": 0.85,
        "code_log_anchor": 0.85,
        "graph_relation": 0.8,
        "observed_incident": 0.75,
        "verified_experience": 0.8,
    }.get(item.authority, 0.5)


def _completeness(item: EvidenceItem) -> float:
    values = [item.title, item.summary, item.location, item.reasons, item.anchors]
    return sum(bool(value) for value in values) / len(values)


def _freshness(item: EvidenceItem) -> float:
    if item.authority == "changed_source":
        return 1.0
    raw_value = item.raw.get("last_verified_at") or item.raw.get("updated_at") or item.raw.get("created_at")
    if not raw_value:
        return 0.6 if item.source in {"code", "log", "edge"} else 0.4
    try:
        parsed = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age_days = max(0, (datetime.now(timezone.utc) - parsed).days)
    except (TypeError, ValueError):
        return 0.4
    if age_days <= 30:
        return 1.0
    if age_days <= 180:
        return 0.75
    if age_days <= 365:
        return 0.5
    return 0.25


def _penalties(item: EvidenceItem) -> dict[str, float]:
    text = " ".join(item.warnings).lower()
    raw = item.raw
    return {
        "stale": 30.0 if raw.get("is_stale") or raw.get("status") == "stale" else 0.0,
        "misleading": min(30.0, float(raw.get("misleading_score") or 0.0) * 30.0),
        "feedback": min(25.0, float(raw.get("feedback_penalty") or 0.0)),
        "conflict": 18.0 if "conflict" in text or "冲突" in text else 0.0,
        "unsupported": 10.0 if item.authority == "advisory_memory" and not item.summary and not item.anchors else 0.0,
        "warning": 8.0 if item.warnings else 0.0,
    }


def _score_reasons(item: EvidenceItem) -> list[str]:
    factors = sorted(item.score_components.items(), key=lambda pair: pair[1], reverse=True)
    reasons = [f"{name}:{value:.1f}" for name, value in factors[:3]]
    reasons.extend(f"penalty:{name}:{value:.1f}" for name, value in item.penalties.items() if value)
    return reasons


def _shares_anchor(left: EvidenceItem, right: EvidenceItem) -> bool:
    return bool(set(left.anchors) & set(right.anchors))
