# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from heapq import nsmallest
from typing import Any

from .text import unique_list


MAX_SPANS = 64
MAX_EDGES = 96
MAX_EVENTS = 80
MAX_PATHS = 8


def build_runtime_span_graph(events: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = bounded_ordered_events(events)
    span_events: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    unbound: list[dict[str, Any]] = []
    for event in ordered:
        trace_id = text_value(event.get("trace_id"))
        span_id = text_value(event.get("span_id"))
        if trace_id and span_id:
            span_events[(trace_id, span_id)].append(event)
        elif trace_id or correlation_id(event):
            unbound.append(compact_event(event))

    keys = list(span_events)[:MAX_SPANS]
    key_set = set(keys)
    spans = [span_node(key, span_events[key]) for key in keys]
    edges: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    for node in spans:
        parent_id = text_value(node.get("parent_span_id"))
        if not parent_id:
            continue
        parent_key = (node["trace_id"], parent_id)
        if parent_key in key_set:
            edges.append({
                "source": span_key(*parent_key),
                "relation": "parent_of",
                "target": node["id"],
                "evidence": "propagated_parent_span_id",
            })
        else:
            gaps.append({
                "kind": "missing_parent_span",
                "action": f"collect parent span {parent_id} for trace {node['trace_id']}",
            })
    paths = build_trace_paths(ordered, key_set)
    trace_ids = sorted({node["trace_id"] for node in spans})
    return {
        "schema_version": "runtime-span-graph/v1",
        "trace_ids": trace_ids[:12],
        "spans": spans,
        "edges": edges[:MAX_EDGES],
        "unbound_events": unbound[:12],
        "causal_paths": paths,
        "gaps": unique_gaps(gaps),
        "quality": graph_quality(ordered, spans, edges, gaps),
        "audit": {
            "bounded": True,
            "persisted": False,
            "input_event_count": len(events),
            "span_limit": MAX_SPANS,
            "event_limit": MAX_EVENTS,
            "truncated": len(events) > MAX_EVENTS or len(span_events) > MAX_SPANS,
        },
    }


def select_related_span_events(
    events: list[dict[str, Any]],
    seeds: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    identities = {
        field: {
            text_value(seed.get(field))
            for seed in seeds
            if text_value(seed.get(field))
        }
        for field in ("trace_id", "request_id", "session_id")
    }
    if not any(identities.values()):
        return seeds
    selected = [
        event for event in events
        if any(text_value(event.get(field)) in identities[field] for field in identities)
    ]
    return selected or seeds


def bounded_ordered_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(events) <= MAX_EVENTS:
        return sorted(events, key=event_order_key)
    return nsmallest(MAX_EVENTS, events, key=event_order_key)


def span_node(key: tuple[str, str], events: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(events, key=event_order_key)
    first = ordered[0]
    parent_ids = unique_list([text_value(event.get("parent_span_id")) for event in ordered if event.get("parent_span_id")])
    return {
        "id": span_key(*key),
        "trace_id": key[0],
        "span_id": key[1],
        "parent_span_id": parent_ids[0] if parent_ids else "",
        "service_name": first_nonempty(ordered, "service_name"),
        "service_version": first_nonempty(ordered, "service_version"),
        "service_instance_id": first_nonempty(ordered, "service_instance_id"),
        "deployment_environment": first_nonempty(ordered, "deployment_environment"),
        "process": first_nonempty(ordered, "process"),
        "span_kind": first_nonempty(ordered, "span_kind"),
        "line_start": int(first.get("line_number") or 0),
        "line_end": int(ordered[-1].get("line_number") or 0),
        "time_start": first.get("timestamp"),
        "time_end": ordered[-1].get("timestamp"),
        "event_names": unique_list([text_value(event.get("event_name") or event.get("event_type")) for event in ordered])[:8],
        "error_codes": unique_list([text_value(event.get("error_code")) for event in ordered if event.get("error_code")])[:4],
        "results": unique_list([text_value(event.get("result")) for event in ordered if event.get("result")])[:4],
    }


def build_trace_paths(
    ordered: list[dict[str, Any]],
    span_keys: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in ordered:
        trace_id = text_value(event.get("trace_id"))
        if trace_id:
            grouped[trace_id].append(event)
    paths: list[dict[str, Any]] = []
    for trace_id, trace_events in list(grouped.items())[:MAX_PATHS]:
        steps = [compact_event(event) for event in trace_events[:16]]
        timestamps = [timestamp_value(event.get("timestamp")) for event in trace_events]
        valid_times = [value for value in timestamps if value is not None]
        temporal_valid = len(valid_times) >= 2 and valid_times == sorted(valid_times)
        correlated = all(text_value(event.get("trace_id")) == trace_id for event in trace_events)
        paths.append({
            "trace_id": trace_id,
            "steps": steps,
            "temporal_order_verified": temporal_valid,
            "correlation_verified": correlated,
            "span_coverage": round(
                sum((trace_id, text_value(event.get("span_id"))) in span_keys for event in trace_events) / len(trace_events),
                3,
            ),
        })
    return paths


def compact_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "line_number": int(event.get("line_number") or 0),
        "timestamp": event.get("timestamp"),
        "event_name": event.get("event_name") or event.get("event_type"),
        "trace_id": text_value(event.get("trace_id")),
        "span_id": text_value(event.get("span_id")),
        "request_id": text_value(event.get("request_id")),
        "session_id": text_value(event.get("session_id")),
        "reason": text_value(event.get("reason")),
        "error_code": text_value(event.get("error_code")),
        "result": text_value(event.get("result")),
    }


def graph_quality(
    events: list[dict[str, Any]],
    spans: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    gaps: list[dict[str, str]],
) -> dict[str, Any]:
    correlated = sum(bool(correlation_id(event)) for event in events)
    span_bound = sum(bool(event.get("trace_id") and event.get("span_id")) for event in events)
    return {
        "status": "good" if spans and not gaps else "partial" if correlated else "insufficient",
        "correlated_event_rate": round(correlated / len(events), 3) if events else 0.0,
        "span_bound_event_rate": round(span_bound / len(events), 3) if events else 0.0,
        "parent_edge_count": len(edges),
        "gap_count": len(gaps),
    }


def event_order_key(event: dict[str, Any]) -> tuple[int, Any, int]:
    parsed = timestamp_value(event.get("timestamp"))
    line = int(event.get("line_number") or 0)
    return (0, parsed, line) if parsed is not None else (1, line, line)


def timestamp_value(value: Any) -> float | None:
    parsed = parse_timestamp(value)
    return parsed.timestamp() if parsed is not None else None


def parse_timestamp(value: Any) -> datetime | None:
    text = text_value(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    for pattern in ("%m-%d %H:%M:%S.%f", "%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def correlation_id(event: dict[str, Any]) -> str:
    for field in ("trace_id", "request_id", "session_id"):
        value = text_value(event.get(field))
        if value:
            return f"{field}:{value}"
    return ""


def span_key(trace_id: str, span_id: str) -> str:
    return f"span:{trace_id}:{span_id}"


def first_nonempty(events: list[dict[str, Any]], field: str) -> str:
    return next((text_value(event.get(field)) for event in events if text_value(event.get(field))), "")


def unique_gaps(gaps: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for gap in gaps:
        key = (gap["kind"], gap["action"])
        if key not in seen:
            seen.add(key)
            result.append(gap)
    return result[:12]


def text_value(value: Any) -> str:
    return str(value or "").strip()
