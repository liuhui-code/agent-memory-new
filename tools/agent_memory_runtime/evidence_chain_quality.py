# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any

from .models import Project
from .records import row_dict
from .storage import connect
from .text import json_list


INCIDENT_TRACE_CASE_RE = re.compile(r"^incident_trace:(\d+)$")


def enrich_reflections_with_evidence_chains(project: Project, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    trace_ids = sorted({trace_id for row in rows for trace_id in incident_trace_source_ids(row)})
    trace_map, link_counts = fetch_trace_evidence(project, trace_ids)
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        evidence = score_reflection_evidence_chain(item, trace_map, link_counts)
        item.update(evidence)
        enriched.append(item)
    return enriched


def incident_trace_source_ids(row: dict[str, Any]) -> list[int]:
    ids: list[int] = []
    for source_case in json_list(row.get("source_cases")):
        match = INCIDENT_TRACE_CASE_RE.match(str(source_case).strip())
        if match:
            ids.append(int(match.group(1)))
    return ids


def fetch_trace_evidence(project: Project, trace_ids: list[int]) -> tuple[dict[int, dict[str, Any]], dict[int, int]]:
    if not trace_ids:
        return {}, {}
    placeholders = ",".join("?" for _ in trace_ids)
    with connect(project) as conn:
        trace_rows = conn.execute(
            f"""
            SELECT *
            FROM incident_traces
            WHERE project_id = ?
              AND id IN ({placeholders})
            """,
            (project.project_id, *trace_ids),
        ).fetchall()
        link_rows = conn.execute(
            f"""
            SELECT trace_id, COUNT(*) AS count
            FROM incident_trace_links
            WHERE project_id = ?
              AND trace_id IN ({placeholders})
            GROUP BY trace_id
            """,
            (project.project_id, *trace_ids),
        ).fetchall()
    return {int(row["id"]): row_dict(row) for row in trace_rows}, {int(row["trace_id"]): int(row["count"]) for row in link_rows}


def score_reflection_evidence_chain(
    row: dict[str, Any],
    trace_map: dict[int, dict[str, Any]],
    link_counts: dict[int, int],
) -> dict[str, Any]:
    source_ids = incident_trace_source_ids(row)
    if not json_list(row.get("source_cases")):
        return evidence_payload(0.0, ["missing source_cases"], [], 0)
    if not source_ids:
        return evidence_payload(0.35, ["source_cases without incident_trace anchor"], [], 0)

    resolved_trace_ids: list[int] = []
    linked_anchor_count = 0
    found_trace_ids: list[int] = []
    for trace_id in source_ids:
        trace = trace_map.get(trace_id)
        if not trace:
            continue
        found_trace_ids.append(trace_id)
        anchor_count = link_counts.get(trace_id, 0)
        linked_anchor_count += anchor_count
        if str(trace.get("status") or "") in {"resolved", "diagnosed"}:
            resolved_trace_ids.append(trace_id)

    if not found_trace_ids:
        return evidence_payload(0.35, ["incident_trace source case not found"], source_ids, 0)
    if linked_anchor_count and resolved_trace_ids:
        return evidence_payload(1.0, ["resolved incident trace with linked anchors"], found_trace_ids, linked_anchor_count)
    if linked_anchor_count:
        return evidence_payload(0.8, ["incident trace with linked anchors"], found_trace_ids, linked_anchor_count)
    return evidence_payload(0.6, ["incident trace source case found"], found_trace_ids, 0)


def evidence_payload(score: float, reasons: list[str], trace_ids: list[int], anchor_count: int) -> dict[str, Any]:
    return {
        "evidence_chain_score": score,
        "evidence_chain_reasons": reasons,
        "evidence_chain_trace_ids": trace_ids,
        "evidence_chain_anchor_count": anchor_count,
    }


def build_evidence_chain_summary(reflection_rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [row for row in reflection_rows if row.get("evidence_chain_score") is not None]
    strong = [row for row in scored if float(row.get("evidence_chain_score") or 0.0) >= 0.8]
    weak = [row for row in scored if float(row.get("evidence_chain_score") or 0.0) < 0.6]
    return {
        "scored_reflections": len(scored),
        "strong_reflections": len(strong),
        "weak_reflections": len(weak),
    }
