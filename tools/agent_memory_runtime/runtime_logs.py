# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from pathlib import Path
from typing import Any

from .diagnosis_hypotheses import build_runtime_hypothesis_ledger
from .log_signal_quality import build_log_signal_summary, enrich_log_signal, low_signal_events
from .models import Project
from .otel_lite import attach_otel_lite
from .query import limited_context
from .runtime_log_parsing import (
    DEFAULT_SLICE_AFTER,
    DEFAULT_SLICE_BEFORE,
    DEFAULT_SLICE_LIMIT,
    MAX_MATCHED_EVENTS,
    build_slices,
    normalize_runtime_log_line,
    score_runtime_event,
)
from .runtime_log_reflection import (
    build_log_improvement_suggestions,
    build_reflect_payload_template,
    build_runtime_episode_candidate,
    build_session_candidates,
)
from .runtime_span_graph import build_runtime_span_graph, select_related_span_events

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
    signal_events = [enrich_log_signal(event) for event in normalized_events]
    scored_events = [
        attach_otel_lite(score_runtime_event(event, query, log_search_plan))
        for event in signal_events
    ]
    matched_events = [event for event in scored_events if int(event.get("score") or 0) > 0]
    matched_events.sort(key=lambda item: (int(item.get("score") or 0), -int(item.get("line_number") or 0)), reverse=True)
    bounded_events = matched_events[:MAX_MATCHED_EVENTS]
    slices = build_slices(raw_lines, bounded_events, before=before, after=after, limit=slice_limit)
    session_candidates = build_session_candidates(bounded_events)
    episode_candidate = build_runtime_episode_candidate(query, slices, bounded_events)
    span_graph_events = select_related_span_events(signal_events, bounded_events)
    span_graph = build_runtime_span_graph(span_graph_events)
    hypothesis_ledger = build_runtime_hypothesis_ledger(query, bounded_events, span_graph)
    log_improvement_suggestions = build_log_improvement_suggestions(
        bounded_events,
        session_candidates,
        log_search_plan,
    )
    return {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "query": query,
        "log_file": str(log_file),
        "log_search_plan": log_search_plan,
        "normalized_event_count": len(normalized_events),
        "log_signal_summary": build_log_signal_summary(signal_events),
        "low_signal_events": low_signal_events(signal_events),
        "matched_events": bounded_events,
        "slices": slices,
        "session_candidates": session_candidates,
        "runtime_episode_candidate": episode_candidate,
        "span_graph": span_graph,
        "hypothesis_ledger": hypothesis_ledger,
        "log_improvement_suggestions": log_improvement_suggestions,
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
