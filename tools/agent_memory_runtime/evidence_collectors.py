# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .evidence_models import EvidenceItem
from .memory_calibration import calibrate_payload
from .models import Project
from .query_collect import collect_matches
from .query_intents import gate_matches_by_intent
from .query_results import SEARCH_RESULT_LIMITS, limited_matches
from .text import json_list, unique_list


GROUP_SOURCE = {
    "semantic_facts": "semantic",
    "reflections": "reflection",
    "episodes": "episode",
    "wiki_matches": "code",
    "code_log_matches": "log",
    "edge_matches": "edge",
    "incident_trace_matches": "incident",
}


def collect_evidence_candidates(
    project: Project,
    query: str,
) -> tuple[list[EvidenceItem], dict[str, Any]]:
    matches = collect_matches(project, query)
    design_corrections = [
        dict(row)
        for row in matches.get("reflections", [])
        if row.get("experience_type") in {"correction_experience", "semantic_patch_experience"}
    ][:4]
    gated = gate_matches_by_intent(project, query, matches)
    bounded = limited_matches(gated["matches"], SEARCH_RESULT_LIMITS, query)
    calibrate_payload(bounded)
    items: list[EvidenceItem] = []
    for group, rows in bounded.items():
        source = GROUP_SOURCE.get(group)
        if not source:
            continue
        items.extend(normalize_evidence(source, row) for row in rows)
    metadata = {
        "memory_intent": gated["memory_intent"],
        "memory_intent_v2": gated["memory_intent_v2"],
        "retrieval_lanes": gated["retrieval_lanes"],
        "memory_brief": gated["memory_brief"],
        "correction_guards": gated["correction_guards"],
        "semantic_patch_notes": gated["semantic_patch_notes"],
        "blocked_memory_notes": gated["blocked_memory_notes"],
        "conflict_notes": gated["conflict_notes"],
        "design_correction_guards": design_corrections,
        "memory_use_policy": bounded.get("memory_use_policy"),
        "candidate_counts": {
            key: len(value)
            for key, value in bounded.items()
            if key in GROUP_SOURCE and isinstance(value, list)
        },
    }
    return items, metadata


def normalize_evidence(source: str, row: dict[str, Any]) -> EvidenceItem:
    record_id = _integer(row.get("id"))
    kind = _kind(source, row)
    title, summary, location = _display_fields(source, row)
    reasons = [str(value) for value in row.get("match_reasons") or []]
    warnings = _warnings(row)
    anchors = _anchors(source, row)
    if record_id is not None:
        anchors = unique_list([f"{kind}:{record_id}", *anchors])
    return EvidenceItem(
        evidence_id=f"{kind}:{record_id}" if record_id is not None else f"{kind}:unknown",
        source=source,
        kind=kind,
        record_id=record_id,
        title=title,
        summary=summary,
        location=location,
        authority=_authority(source, row),
        original_score=float(row.get("rerank_score") or row.get("score") or 0.0),
        reasons=reasons,
        warnings=warnings,
        anchors=anchors,
        raw=row,
    )


def _kind(source: str, row: dict[str, Any]) -> str:
    if source == "code":
        return "code_file" if row.get("kind") == "file" else "code_symbol"
    return {
        "semantic": "semantic_fact",
        "reflection": "reflection",
        "episode": "episode",
        "log": "code_log_statement",
        "edge": "memory_edge",
        "incident": "incident_trace",
    }[source]


def _display_fields(source: str, row: dict[str, Any]) -> tuple[str, str, str | None]:
    if source == "semantic":
        return _text(row.get("fact"), "Semantic fact"), _text(row.get("evidence")), _optional(row.get("scope"))
    if source == "reflection":
        title = _text(row.get("lesson") or row.get("task"), "Reflection")
        summary = _text(row.get("repair_action") or row.get("future_rule") or row.get("summary"))
        return title, summary, _optional(row.get("anchor_key") or row.get("scope"))
    if source == "episode":
        return _text(row.get("task"), "Episode"), _text(row.get("summary")), _optional(row.get("files_touched"))
    if source == "code":
        title = _text(row.get("symbol") or row.get("file_path"), "Code anchor")
        summary = _text(row.get("business_summary") or row.get("summary"))
        return title, summary, _optional(row.get("file_path"))
    if source == "log":
        title = _text(row.get("business_event") or row.get("message_template"), "Code log")
        causes = ", ".join(json_list(row.get("likely_causes")))
        summary = _text(row.get("business_summary") or causes or row.get("message_template"))
        location = _optional(_line_location(row.get("file_path"), row.get("line")))
        return title, summary, location
    if source == "edge":
        title = f"{_text(row.get('source_type'))} {_text(row.get('relation'))} {_text(row.get('target_type'))}"
        return title, _text(row.get("evidence")), None
    title = _text(row.get("symptom"), "Incident trace")
    summary = _text(row.get("diagnosis_summary") or row.get("root_cause_hypothesis") or row.get("normalized_error"))
    return title, summary, _incident_location(row)


def _authority(source: str, row: dict[str, Any]) -> str:
    if source == "code":
        return "learned_code_anchor"
    if source == "log":
        return "code_log_anchor"
    if source == "edge":
        return "graph_relation"
    if source == "incident":
        return "observed_incident"
    if source == "reflection" and row.get("trust_level") in {"verified", "high"}:
        return "verified_experience"
    return "advisory_memory"


def _anchors(source: str, row: dict[str, Any]) -> list[str]:
    anchors: list[str] = []
    if row.get("file_path"):
        anchors.append(f"file:{row['file_path']}")
    if row.get("symbol"):
        anchors.append(f"symbol:{row['symbol']}")
    if row.get("function"):
        anchors.append(f"function:{row['function']}")
    if source == "edge":
        anchors.extend(
            [
                f"{row.get('source_type')}:{row.get('source_id')}",
                f"{row.get('target_type')}:{row.get('target_id')}",
            ]
        )
    for link in row.get("links") or []:
        if isinstance(link, dict):
            anchors.append(f"{link.get('target_type')}:{link.get('target_id')}")
    return unique_list([anchor for anchor in anchors if "None" not in anchor])[:8]


def _warnings(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    warning = row.get("warning")
    if isinstance(warning, str) and warning.strip():
        values.append(warning.strip())
    elif isinstance(warning, dict):
        values.extend(str(value) for value in warning.values() if value)
    values.extend(str(value) for value in row.get("gate_reasons") or [] if value)
    return unique_list(values)


def _incident_location(row: dict[str, Any]) -> str | None:
    for link in row.get("links") or []:
        if isinstance(link, dict) and link.get("evidence"):
            return str(link["evidence"])
    return None


def _line_location(path: Any, line: Any) -> str:
    return f"{path}:{line}" if path and line else _text(path)


def _integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any, fallback: str = "") -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value or fallback).strip()


def _optional(value: Any) -> str | None:
    text = _text(value)
    return text or None
