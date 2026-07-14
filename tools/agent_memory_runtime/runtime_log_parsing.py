# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any

from .text import tokenize, unique_list

MAX_MATCHED_EVENTS = 20
DEFAULT_SLICE_BEFORE = 2
DEFAULT_SLICE_AFTER = 2
DEFAULT_SLICE_LIMIT = 5
SESSION_EVENT_GAP = 10
MAX_CHAIN_SIGNALS = 8
KEY_VALUE_PATTERN = re.compile(
    r"\b(?P<key>route|resource|request_id|session_id|trace_id|span_id|trace_flags|event_name|"
    r"code|error_code|reason|result|page|module|ability)=(?P<value>[^\s]+)"
)
REQUEST_PATH_PATTERN = re.compile(r"(?P<path>/[A-Za-z0-9_./-]+)")

RUNTIME_LOG_PATTERNS = [
    re.compile(
        r"^(?P<timestamp>\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"
        r"(?P<process>[\w.$:-]+)\s+"
        r"(?P<level>[VDIWEF]|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|EXCEPTION)\s+"
        r"(?P<logger>[^:]+):\s*(?P<message>.*)$"
    ),
    re.compile(
        r"^(?P<timestamp>\S+)\s+"
        r"(?:(?:pid|tid)=[^\s]+\s+)*"
        r"(?P<process>[\w.$:-]+)\s+"
        r"(?P<level>[VDIWEF]|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|EXCEPTION)\s+"
        r"(?P<logger>[^:]+):\s*(?P<message>.*)$"
    ),
    re.compile(
        r"^(?P<timestamp>\S+)\s+"
        r"(?P<process>[\w.$:-]+)\s+"
        r"(?P<level>[VDIWEF]|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|EXCEPTION)\s+"
        r"(?P<logger>[^:]+):\s*(?P<message>.*)$"
    ),
    re.compile(
        r"^(?P<timestamp>\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"
        r"(?P<level>[VDIWEF]|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|EXCEPTION)\s+"
        r"(?P<logger>[^:]+):\s*(?P<message>.*)$"
    ),
]

LEVEL_MAP = {
    "V": "verbose",
    "D": "debug",
    "I": "info",
    "W": "warning",
    "WARNING": "warning",
    "E": "error",
    "F": "fatal",
    "DEBUG": "debug",
    "INFO": "info",
    "WARN": "warning",
    "ERROR": "error",
    "FATAL": "fatal",
    "EXCEPTION": "exception",
}



def normalize_level(raw_level: str) -> str:
    return LEVEL_MAP.get(raw_level.upper(), raw_level.lower())



def extract_runtime_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in KEY_VALUE_PATTERN.finditer(text):
        key = str(match.group("key") or "")
        value = str(match.group("value") or "")
        if key == "code":
            fields["error_code"] = value
        else:
            fields[key] = value
    if "error_code" not in fields:
        code_match = re.search(r"\bcode=(?P<code>[A-Za-z0-9_-]+)\b", text)
        if code_match:
            fields["error_code"] = str(code_match.group("code") or "")
    path_match = REQUEST_PATH_PATTERN.search(text)
    if path_match and "request_path" not in fields:
        fields["request_path"] = str(path_match.group("path") or "")
    return fields



def infer_event_type(message: str, extracted_fields: dict[str, str]) -> str:
    lowered = message.lower()
    if "session invalid" in lowered:
        return "session_invalid"
    if "permission denied" in lowered:
        return "permission_denied"
    if "load profile start" in lowered:
        return "profile_load_started"
    if "load profile failed" in lowered:
        return "profile_load_failed"
    if "navigate" in lowered and extracted_fields.get("route"):
        return "route_navigation"
    if extracted_fields.get("request_path"):
        return "network_request"
    return "generic_runtime_event"



def normalize_runtime_log_line(line: str, line_number: int) -> dict[str, Any]:
    stripped = line.rstrip("\n")
    for pattern in RUNTIME_LOG_PATTERNS:
        match = pattern.match(stripped)
        if match:
            groups = match.groupdict()
            message = (groups.get("message") or "").strip()
            extracted_fields = extract_runtime_fields(stripped)
            return normalized_event(
                line_number,
                groups.get("timestamp"),
                groups.get("process") or "",
                normalize_level(groups.get("level") or "info"),
                (groups.get("logger") or "").strip(),
                message,
                stripped,
                extracted_fields,
            )
    logger = ""
    message = stripped
    if ":" in stripped:
        prefix, suffix = stripped.split(":", 1)
        prefix_tokens = prefix.split()
        logger = prefix_tokens[-1] if prefix_tokens else ""
        message = suffix.strip()
    extracted_fields = extract_runtime_fields(stripped)
    return normalized_event(
        line_number,
        None,
        "",
        "",
        logger,
        message,
        stripped,
        extracted_fields,
    )


def normalized_event(
    line_number: int,
    timestamp: Any,
    process: str,
    level: str,
    logger: str,
    message: str,
    raw_line: str,
    fields: dict[str, str],
) -> dict[str, Any]:
    return {
        "line_number": line_number,
        "timestamp": timestamp,
        "observed_timestamp": timestamp,
        "process": process,
        "level": level,
        "logger": logger,
        "message": message,
        "event_type": fields.get("event_name") or infer_event_type(message, fields),
        "event_name": fields.get("event_name") or infer_event_type(message, fields),
        "trace_id": fields.get("trace_id", ""),
        "span_id": fields.get("span_id", ""),
        "trace_flags": fields.get("trace_flags", ""),
        "error_code": fields.get("error_code", ""),
        "route": fields.get("route", ""),
        "resource_key": fields.get("resource", ""),
        "request_id": fields.get("request_id", ""),
        "session_id": fields.get("session_id", ""),
        "reason": fields.get("reason", ""),
        "result": fields.get("result", ""),
        "module": fields.get("module", ""),
        "ability": fields.get("ability", ""),
        "request_path": fields.get("request_path", ""),
        "raw_line": raw_line,
    }



def runtime_event_search_text(event: dict[str, Any]) -> str:
    return " ".join(
        str(event.get(key) or "")
        for key in (
            "process", "level", "logger", "message", "raw_line", "event_name", "route",
            "resource_key", "request_id", "session_id", "trace_id", "span_id", "error_code",
            "reason", "result", "module", "ability", "request_path",
        )
    ).lower()



def candidate_anchor_terms(log_search_plan: dict[str, Any]) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    search_terms = [str(item) for item in log_search_plan.get("search_terms") or []]
    logger_hints = [str(item) for item in log_search_plan.get("logger_hints") or []]
    function_hints = [str(item) for item in log_search_plan.get("function_hints") or []]
    process_hints = [str(item) for item in log_search_plan.get("process_hints") or []]
    candidate_messages = [
        str(item.get("message_template") or "")
        for item in log_search_plan.get("candidate_log_events") or []
        if str(item.get("message_template") or "").strip()
    ]
    return search_terms, logger_hints, function_hints, process_hints, candidate_messages



def score_runtime_event(event: dict[str, Any], query: str, log_search_plan: dict[str, Any]) -> dict[str, Any]:
    search_text = runtime_event_search_text(event)
    score = 0
    matched_terms: list[str] = []
    search_terms, logger_hints, function_hints, process_hints, candidate_messages = candidate_anchor_terms(log_search_plan)

    for message in candidate_messages:
        lowered = message.lower()
        if lowered and lowered in search_text:
            score += 12
            matched_terms.append(message)
    for term in search_terms:
        lowered = term.lower()
        if len(lowered) > 1 and lowered in search_text:
            score += 5
            matched_terms.append(term)
    for hint in logger_hints:
        lowered = hint.lower()
        if lowered and lowered in search_text:
            score += 4
            matched_terms.append(hint)
    for hint in function_hints:
        lowered = hint.lower()
        if lowered and lowered in search_text:
            score += 2
            matched_terms.append(hint)
    for hint in process_hints:
        lowered = hint.lower()
        if lowered and lowered in search_text:
            score += 3
            matched_terms.append(hint)

    if log_search_plan.get("focus") == "log" and event.get("level") in {"error", "warning", "fatal", "exception"}:
        score += 3
    if any(token in search_text for token in tokenize(query)):
        score += 1
    if event.get("error_code"):
        score += 2
        matched_terms.append(str(event["error_code"]))
    if event.get("reason"):
        score += 2
        matched_terms.append(str(event["reason"]))
    if event.get("route"):
        score += 1
        matched_terms.append(str(event["route"]))

    scored = dict(event)
    scored["score"] = score
    scored["matched_terms"] = unique_list(matched_terms)
    return scored



def merge_slice_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged = [ranges[0]]
    for start, end in ranges[1:]:
        previous_start, previous_end = merged[-1]
        if start <= previous_end + 1:
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))
    return merged



def build_slices(
    lines: list[str],
    matched_events: list[dict[str, Any]],
    before: int = DEFAULT_SLICE_BEFORE,
    after: int = DEFAULT_SLICE_AFTER,
    limit: int = DEFAULT_SLICE_LIMIT,
) -> list[dict[str, Any]]:
    if not matched_events:
        return []
    ranges = [
        (max(1, int(event["line_number"]) - before), min(len(lines), int(event["line_number"]) + after))
        for event in matched_events[:limit]
    ]
    merged_ranges = merge_slice_ranges(ranges)[:limit]
    slices: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(merged_ranges, start=1):
        slice_events = [event for event in matched_events if start <= int(event["line_number"]) <= end]
        excerpt = [lines[line_number - 1].rstrip("\n") for line_number in range(start, end + 1)]
        dominant_terms = unique_list(
            [
                *[term for event in slice_events for term in event.get("matched_terms") or []],
                *[str(event.get("message") or "") for event in slice_events if str(event.get("message") or "").strip()],
            ]
        )[:6]
        timestamps = [str(event.get("timestamp") or "") for event in slice_events if event.get("timestamp")]
        time_range = " -> ".join([timestamps[0], timestamps[-1]]) if timestamps else f"lines {start}-{end}"
        slices.append(
            {
                "slice_id": f"slice_{index:03d}",
                "line_start": start,
                "line_end": end,
                "time_range": time_range,
                "dominant_terms": dominant_terms,
                "excerpt": excerpt,
                "matched_events": slice_events,
                "summary": "; ".join(dominant_terms[:3]) or "matched runtime evidence",
            }
        )
    return slices
