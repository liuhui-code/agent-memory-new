# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import Project
from .query import limited_context
from .text import tokenize, unique_list

MAX_MATCHED_EVENTS = 20
DEFAULT_SLICE_BEFORE = 2
DEFAULT_SLICE_AFTER = 2
DEFAULT_SLICE_LIMIT = 5
SESSION_EVENT_GAP = 10

RUNTIME_LOG_PATTERNS = [
    re.compile(
        r"^(?P<timestamp>\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"
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


def normalize_runtime_log_line(line: str, line_number: int) -> dict[str, Any]:
    stripped = line.rstrip("\n")
    for pattern in RUNTIME_LOG_PATTERNS:
        match = pattern.match(stripped)
        if match:
            groups = match.groupdict()
            return {
                "line_number": line_number,
                "timestamp": groups.get("timestamp"),
                "process": groups.get("process") or "",
                "level": normalize_level(groups.get("level") or "info"),
                "logger": (groups.get("logger") or "").strip(),
                "message": (groups.get("message") or "").strip(),
                "raw_line": stripped,
            }
    logger = ""
    message = stripped
    if ":" in stripped:
        prefix, suffix = stripped.split(":", 1)
        prefix_tokens = prefix.split()
        logger = prefix_tokens[-1] if prefix_tokens else ""
        message = suffix.strip()
    return {
        "line_number": line_number,
        "timestamp": None,
        "process": "",
        "level": "",
        "logger": logger,
        "message": message,
        "raw_line": stripped,
    }


def runtime_event_search_text(event: dict[str, Any]) -> str:
    return " ".join(
        str(event.get(key) or "")
        for key in ("process", "level", "logger", "message", "raw_line")
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


def build_runtime_episode_candidate(query: str, slices: list[dict[str, Any]], matched_events: list[dict[str, Any]]) -> dict[str, Any]:
    top_slice = slices[0] if slices else None
    dominant_signals = unique_list(
        [
            *[term for event in matched_events[:5] for term in event.get("matched_terms") or []],
            *([str(item) for item in (top_slice or {}).get("dominant_terms") or []]),
        ]
    )[:8]
    processes = unique_list([str(event.get("process") or "") for event in matched_events if event.get("process")])[:3]
    summary_parts = [f"Runtime evidence for query: {query}"]
    if dominant_signals:
        summary_parts.append("dominant signals: " + ", ".join(dominant_signals[:4]))
    if processes:
        summary_parts.append("processes: " + ", ".join(processes))
    if top_slice:
        summary_parts.append(f"primary slice {top_slice['time_range']}")
    return {
        "query": query,
        "dominant_signals": dominant_signals,
        "processes": processes,
        "slice_count": len(slices),
        "matched_event_count": len(matched_events),
        "summary": ". ".join(summary_parts),
    }


def build_session_candidates(matched_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not matched_events:
        return []
    ordered = sorted(matched_events, key=lambda item: int(item.get("line_number") or 0))
    sessions: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = [ordered[0]]
    for event in ordered[1:]:
        previous = current[-1]
        same_process = str(event.get("process") or "") == str(previous.get("process") or "")
        close_lines = int(event.get("line_number") or 0) - int(previous.get("line_number") or 0) <= SESSION_EVENT_GAP
        if same_process and close_lines:
            current.append(event)
        else:
            sessions.append(current)
            current = [event]
    sessions.append(current)

    candidates: list[dict[str, Any]] = []
    for index, events in enumerate(sessions[:5], start=1):
        dominant_terms = unique_list([term for event in events for term in event.get("matched_terms") or []])[:8]
        processes = unique_list([str(event.get("process") or "") for event in events if event.get("process")])[:3]
        timestamps = [str(event.get("timestamp") or "") for event in events if event.get("timestamp")]
        candidates.append(
            {
                "session_id": f"session_{index:03d}",
                "event_count": len(events),
                "line_start": int(events[0].get("line_number") or 0),
                "line_end": int(events[-1].get("line_number") or 0),
                "time_range": " -> ".join([timestamps[0], timestamps[-1]]) if timestamps else f"lines {events[0]['line_number']}-{events[-1]['line_number']}",
                "processes": processes,
                "dominant_terms": dominant_terms,
                "summary": "; ".join(dominant_terms[:4]) or "runtime session candidate",
            }
        )
    return candidates


def suggested_experience_type(query: str, matched_events: list[dict[str, Any]]) -> str:
    lowered = query.lower()
    if any(trigger in lowered for trigger in ("误判", "纠正", "不是", "理解错", "修正")):
        return "correction_experience"
    if any(
        phrase in " ".join(str(term).lower() for term in event.get("matched_terms") or [])
        for event in matched_events
        for phrase in ("session invalid", "permission denied")
    ):
        return "procedure_experience"
    return "procedure_experience"


def build_reflect_payload_template(
    query: str,
    context: dict[str, Any],
    log_search_plan: dict[str, Any],
    matched_events: list[dict[str, Any]],
    slices: list[dict[str, Any]],
    runtime_episode_candidate: dict[str, Any],
    session_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    top_slice = slices[0] if slices else {}
    top_session = session_candidates[0] if session_candidates else {}
    followup_focus = str(context.get("followup_focus") or log_search_plan.get("focus") or "log")
    dominant_signals = runtime_episode_candidate.get("dominant_signals") or []
    useful_terms = unique_list(
        [
            *[str(item) for item in dominant_signals],
            *[term for event in matched_events[:3] for term in event.get("matched_terms") or []],
        ]
    )[:10]
    inspection_targets = unique_list(
        [
            *[str(item) for item in log_search_plan.get("file_hints") or []],
            *[str(item) for item in log_search_plan.get("function_hints") or []],
            *[str(item.get("message_template") or "") for item in log_search_plan.get("candidate_log_events") or []],
        ]
    )[:10]
    context_used = [
        f"query: {query}",
        *[f"log_event: {event.get('message')}" for event in matched_events[:3] if str(event.get("message") or "").strip()],
        *[f"slice: {item.get('time_range')}" for item in slices[:2]],
    ]
    return {
        "task_type": "diagnosis",
        "experience_type": suggested_experience_type(query, matched_events),
        "outcome": "partial",
        "problem": query,
        "summary": runtime_episode_candidate.get("summary"),
        "reasoning_summary": "Runtime log evidence was compressed into matched events and bounded slices before diagnosis.",
        "context_used": context_used,
        "what_worked": [
            "Use code-log memory to build a log_search_plan first.",
            "Inspect bounded runtime log slices instead of scanning the full raw log.",
        ],
        "what_failed": [],
        "query_rounds": 1,
        "trajectory_summary": top_session.get("summary") or runtime_episode_candidate.get("summary"),
        "useful_followup_focus": followup_focus,
        "useful_followup_terms": useful_terms,
        "inspection_targets": inspection_targets,
        "final_verification_path": top_slice.get("time_range") or top_session.get("time_range") or runtime_episode_candidate.get("summary"),
        "verification_method": "Confirm the dominant runtime slice against code-log anchors and related source files.",
        "source_cases": [
            f"runtime_log:{runtime_episode_candidate.get('query')}",
            *[f"session:{item.get('session_id')}" for item in session_candidates[:2]],
        ],
    }


def analyze_runtime_log(
    project: Project,
    query: str,
    log_file: Path,
    before: int = DEFAULT_SLICE_BEFORE,
    after: int = DEFAULT_SLICE_AFTER,
    slice_limit: int = DEFAULT_SLICE_LIMIT,
) -> dict[str, Any]:
    raw_lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    normalized_events = [normalize_runtime_log_line(line, index) for index, line in enumerate(raw_lines, start=1) if line.strip()]
    context = limited_context(project, query)
    log_search_plan = context.get("log_search_plan") or {}
    scored_events = [
        score_runtime_event(event, query, log_search_plan)
        for event in normalized_events
    ]
    matched_events = [event for event in scored_events if int(event.get("score") or 0) > 0]
    matched_events.sort(key=lambda item: (int(item.get("score") or 0), -int(item.get("line_number") or 0)), reverse=True)
    bounded_events = matched_events[:MAX_MATCHED_EVENTS]
    slices = build_slices(raw_lines, bounded_events, before=before, after=after, limit=slice_limit)
    session_candidates = build_session_candidates(bounded_events)
    episode_candidate = build_runtime_episode_candidate(query, slices, bounded_events)
    return {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "query": query,
        "log_file": str(log_file),
        "log_search_plan": log_search_plan,
        "normalized_event_count": len(normalized_events),
        "matched_events": bounded_events,
        "slices": slices,
        "session_candidates": session_candidates,
        "runtime_episode_candidate": episode_candidate,
        "reflect_payload_template": build_reflect_payload_template(
            query,
            context,
            log_search_plan,
            bounded_events,
            slices,
            episode_candidate,
            session_candidates,
        ),
    }
