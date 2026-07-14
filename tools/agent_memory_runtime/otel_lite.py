# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


SEVERITY_TEXT = {
    "verbose": "TRACE",
    "debug": "DEBUG",
    "info": "INFO",
    "warning": "WARN",
    "warn": "WARN",
    "error": "ERROR",
    "fatal": "FATAL",
    "exception": "ERROR",
}


def runtime_event_to_otel_lite(event: dict[str, Any]) -> dict[str, Any]:
    attributes = compact_dict(
        {
            "logger.name": event.get("logger"),
            "event.name": event.get("event_type"),
            "log.line_number": event.get("line_number"),
            "request.id": event.get("request_id"),
            "session.id": event.get("session_id"),
            "error.code": event.get("error_code"),
            "error.reason": event.get("reason"),
            "url.path": event.get("request_path"),
            "app.route": event.get("route"),
            "app.resource": event.get("resource_key"),
            "app.result": event.get("result"),
            "app.module": event.get("module"),
            "app.ability": event.get("ability"),
        }
    )
    return {
        "time_unix_nano": None,
        "timestamp": event.get("timestamp"),
        "observed_timestamp": event.get("observed_timestamp"),
        "event_name": event.get("event_name") or event.get("event_type"),
        "trace_id": event.get("trace_id"),
        "span_id": event.get("span_id"),
        "trace_flags": event.get("trace_flags"),
        "severity_text": severity_text(event.get("level")),
        "severity_number": severity_number(event.get("level")),
        "body": event.get("message") or event.get("raw_line") or "",
        "resource": compact_dict({"process.name": event.get("process")}),
        "attributes": attributes,
    }


def code_log_to_otel_lite(row: dict[str, Any]) -> dict[str, Any]:
    attributes = compact_dict(
        {
            "code.file.path": row.get("file_path"),
            "code.function": row.get("function"),
            "logger.name": row.get("logger"),
            "event.name": row.get("business_event"),
            "app.stage": row.get("trigger_stage"),
            "app.symptom_terms": row.get("symptom_terms"),
            "app.likely_causes": row.get("likely_causes"),
            "app.process_hint": row.get("process_hint"),
        }
    )
    return {
        "time_unix_nano": None,
        "timestamp": None,
        "severity_text": severity_text(row.get("level")),
        "severity_number": severity_number(row.get("level")),
        "body": row.get("message_template") or row.get("raw_statement") or "",
        "resource": compact_dict({"process.name": row.get("process_hint")}),
        "attributes": attributes,
    }


def attach_otel_lite(event: dict[str, Any]) -> dict[str, Any]:
    item = dict(event)
    item["otel_lite"] = runtime_event_to_otel_lite(item)
    return item


def severity_text(level: Any) -> str:
    return SEVERITY_TEXT.get(str(level or "").lower(), str(level or "").upper() or "UNSPECIFIED")


def severity_number(level: Any) -> int:
    normalized = str(level or "").lower()
    if normalized in {"verbose"}:
        return 1
    if normalized == "debug":
        return 5
    if normalized == "info":
        return 9
    if normalized in {"warning", "warn"}:
        return 13
    if normalized in {"error", "exception"}:
        return 17
    if normalized == "fatal":
        return 21
    return 0


def compact_dict(values: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        result[key] = value
    return result
