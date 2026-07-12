# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any

from .text import unique_list


SIGNAL_WEIGHTS = {
    "timestamp": 0.07,
    "process": 0.06,
    "level": 0.06,
    "logger": 0.06,
    "event_type": 0.07,
    "stage": 0.08,
    "business_event": 0.08,
    "error_code": 0.08,
    "reason": 0.08,
    "route_or_resource": 0.10,
    "request_or_session_id": 0.12,
    "entity_id_or_key": 0.07,
    "action_result": 0.08,
    "neighbor_context": 0.06,
}

STAGE_PATTERN = re.compile(r"\b(stage|phase|step)=([A-Za-z0-9_-]+)\b", re.IGNORECASE)
RESULT_PATTERN = re.compile(r"\b(result|outcome|status)=([A-Za-z0-9_-]+)\b", re.IGNORECASE)
ENTITY_PATTERN = re.compile(r"\b([A-Za-z_]*(?:id|key))=([A-Za-z0-9_.:/-]+)\b", re.IGNORECASE)


def score_log_signal(event: dict[str, Any]) -> dict[str, Any]:
    text = event_text(event)
    present = signal_presence(event, text)
    present_signals = [name for name in SIGNAL_WEIGHTS if present.get(name)]
    missing_signals = [name for name in SIGNAL_WEIGHTS if not present.get(name)]
    score = sum(weight for name, weight in SIGNAL_WEIGHTS.items() if present.get(name))
    return {
        "log_signal_score": round(max(0.0, min(1.0, score)), 3),
        "log_signal_band": signal_band(score),
        "present_signals": present_signals,
        "missing_signals": missing_signals,
        "suggested_log_fields": suggested_log_fields(missing_signals),
    }


def enrich_log_signal(event: dict[str, Any]) -> dict[str, Any]:
    item = dict(event)
    item.update(score_log_signal(item))
    return item


def build_log_signal_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [event if "log_signal_score" in event else enrich_log_signal(event) for event in events]
    if not scored:
        return {
            "event_count": 0,
            "average_log_signal_score": 0.0,
            "bands": {"good": 0, "watch": 0, "poor": 0},
            "top_missing_signals": [],
        }
    bands = {"good": 0, "watch": 0, "poor": 0}
    missing_counts: dict[str, int] = {}
    for event in scored:
        band = str(event.get("log_signal_band") or "poor")
        bands[band] = bands.get(band, 0) + 1
        for signal in event.get("missing_signals") or []:
            missing_counts[str(signal)] = missing_counts.get(str(signal), 0) + 1
    return {
        "event_count": len(scored),
        "average_log_signal_score": round(sum(float(event.get("log_signal_score") or 0.0) for event in scored) / len(scored), 3),
        "bands": bands,
        "top_missing_signals": [
            {"signal": signal, "count": count}
            for signal, count in sorted(missing_counts.items(), key=lambda item: (-item[1], item[0]))[:8]
        ],
    }


def low_signal_events(events: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    scored = [event if "log_signal_score" in event else enrich_log_signal(event) for event in events]
    low = [event for event in scored if str(event.get("log_signal_band") or "") == "poor"]
    low.sort(key=lambda item: (float(item.get("log_signal_score") or 0.0), int(item.get("line_number") or 0)))
    return [
        {
            "line_number": event.get("line_number"),
            "message": event.get("message") or event.get("message_template") or event.get("raw_line"),
            "log_signal_score": event.get("log_signal_score"),
            "log_signal_band": event.get("log_signal_band"),
            "missing_signals": event.get("missing_signals") or [],
            "suggested_log_fields": event.get("suggested_log_fields") or [],
        }
        for event in low[:limit]
    ]


def signal_presence(event: dict[str, Any], text: str) -> dict[str, bool]:
    event_type = str(event.get("event_type") or "")
    otel = event.get("otel_lite") if isinstance(event.get("otel_lite"), dict) else {}
    otel_attributes = otel.get("attributes", {}) if isinstance(otel.get("attributes"), dict) else {}
    otel_resource = otel.get("resource", {}) if isinstance(otel.get("resource"), dict) else {}
    route_or_resource = any(
        has_value(event.get(key))
        for key in ("route", "resource_key", "resource", "request_path", "file_path", "anchor_key")
    ) or any(has_value(otel_attributes.get(key)) for key in ("app.route", "app.resource", "url.path", "code.file.path"))
    return {
        "timestamp": has_value(event.get("timestamp")) or has_value(otel.get("timestamp")),
        "process": has_value(event.get("process")) or has_value(event.get("process_hint")) or has_value(otel_resource.get("process.name")),
        "level": has_value(event.get("level")) or has_value(otel.get("severity_text")),
        "logger": has_value(event.get("logger")) or has_value(otel_attributes.get("logger.name")),
        "event_type": (has_value(event_type) and event_type != "generic_runtime_event") or has_value(otel_attributes.get("event.name")),
        "stage": has_value(event.get("trigger_stage")) or bool(STAGE_PATTERN.search(text)) or contains_any(text, (" start", " started", " begin", " failed", " success")),
        "business_event": has_value(event.get("business_event")) or bracketed_event(text) or (has_value(event_type) and event_type != "generic_runtime_event") or has_value(otel_attributes.get("event.name")),
        "error_code": has_value(event.get("error_code")) or has_value(otel_attributes.get("error.code")) or " code=" in text.lower(),
        "reason": has_value(event.get("reason")) or has_value(otel_attributes.get("error.reason")) or " reason=" in text.lower(),
        "route_or_resource": route_or_resource,
        "request_or_session_id": has_value(event.get("request_id")) or has_value(event.get("session_id")) or has_value(otel_attributes.get("request.id")) or has_value(otel_attributes.get("session.id")) or "request_id=" in text.lower() or "session_id=" in text.lower(),
        "entity_id_or_key": route_or_resource or bool(ENTITY_PATTERN.search(text)),
        "action_result": bool(RESULT_PATTERN.search(text)) or contains_any(text, (" failed", " success", " succeeded", " started", " completed")),
        "neighbor_context": has_value(event.get("neighbor_terms")) or has_value(event.get("function")) or has_value(event.get("raw_statement")),
    }


def suggested_log_fields(missing_signals: list[str]) -> list[str]:
    suggestions: list[str] = []
    mapping = {
        "timestamp": ["timestamp"],
        "process": ["process"],
        "level": ["level"],
        "logger": ["logger"],
        "event_type": ["event_type"],
        "stage": ["stage"],
        "business_event": ["business_event"],
        "error_code": ["error_code"],
        "reason": ["reason"],
        "route_or_resource": ["route", "resource"],
        "request_or_session_id": ["request_id", "session_id"],
        "entity_id_or_key": ["entity_id"],
        "action_result": ["result"],
        "neighbor_context": ["function", "neighbor_context"],
    }
    for signal in missing_signals:
        suggestions.extend(mapping.get(signal, [signal]))
    return unique_list(suggestions)


def signal_band(score: float) -> str:
    if score >= 0.75:
        return "good"
    if score >= 0.55:
        return "watch"
    return "poor"


def event_text(event: dict[str, Any]) -> str:
    return " ".join(
        str(event.get(key) or "")
        for key in (
            "message",
            "message_template",
            "raw_line",
            "raw_statement",
            "event_type",
            "business_event",
            "trigger_stage",
            "reason",
            "route",
            "resource_key",
            "request_path",
        )
    )


def bracketed_event(text: str) -> bool:
    return bool(re.search(r"\[[^\]]{2,40}\]", text))


def contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = f" {text.lower()} "
    return any(needle in lowered for needle in needles)


def has_value(value: Any) -> bool:
    if isinstance(value, list):
        return bool(value)
    text = str(value or "").strip()
    return bool(text and text not in {"[]", "{}"})
