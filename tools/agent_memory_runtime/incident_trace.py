# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from typing import Any

from .incident_trace_builder import (
    build_agent_incident,
    capped_confidence,
    evidence_state,
)
from .incident_trace_models import INCIDENT_CAPTURE_AGENT, INCIDENT_TRACE_STATUSES
from .models import Project
from .records import output, row_dict
from .storage import connect, ensure_initialized, now_iso, resolve_project


def resolve_agent_anchors(project: Project, values: list[str]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    with connect(project) as conn:
        for value in unique_strings(values, 12):
            path, symbol = anchor_parts(value)
            row = None
            target_type = "code_file"
            if symbol:
                target_type = "code_symbol"
                row = conn.execute(
                    """
                    SELECT id, file_path, symbol
                    FROM code_symbols
                    WHERE project_id = ? AND file_path = ? AND symbol = ?
                    ORDER BY index_generation DESC, id DESC LIMIT 1
                    """,
                    (project.project_id, path, symbol),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT id, file_path, NULL AS symbol
                    FROM code_files
                    WHERE project_id = ? AND file_path = ?
                    ORDER BY index_generation DESC, id DESC LIMIT 1
                    """,
                    (project.project_id, path),
                ).fetchone()
            if row:
                key = f"{row['file_path']}::{row['symbol']}" if row["symbol"] else row["file_path"]
                links.append({
                    "target_type": target_type,
                    "target_id": int(row["id"]),
                    "target_key": key,
                    "relation": "agent_confirmed_anchor",
                    "score": 1.0,
                    "evidence": "agent supplied anchor matched the current learned index",
                })
            else:
                links.append({
                    "target_type": "code_anchor",
                    "target_id": None,
                    "target_key": value,
                    "relation": "unresolved_agent_anchor",
                    "score": 0.0,
                    "evidence": "agent supplied anchor is absent from the current learned index",
                })
    return links


def write_incident_record(
    project: Project,
    draft: dict[str, Any],
    links: list[dict[str, Any]],
) -> dict[str, Any]:
    ts = now_iso()
    events = json.dumps(draft["observed_events"], ensure_ascii=False)
    steps = json.dumps(draft["agent_causal_steps"], ensure_ascii=False)
    with connect(project) as conn:
        existing = conn.execute(
            "SELECT id FROM incident_traces WHERE project_id = ? AND trace_key = ?",
            (project.project_id, draft["trace_key"]),
        ).fetchone()
        values = (
            draft["status"], draft["symptom"], draft["arkts_scene"], events,
            draft["diagnosis_summary"], steps, draft["intervention"],
            draft["verification_evidence"], draft["resolution"], draft["confidence"],
            draft["source"], draft["capture_mode"], draft["evidence_state"], ts,
        )
        if existing:
            trace_id = int(existing["id"])
            conn.execute(
                """
                UPDATE incident_traces
                SET status = ?, symptom = ?, arkts_scene = ?, entry_log_text = NULL,
                    normalized_error = NULL, dominant_log_events = ?, diagnosis_summary = ?,
                    suspected_chain = NULL, causal_chain = ?, span_graph = NULL,
                    root_cause_hypothesis = NULL, intervention = ?, verification_evidence = ?,
                    resolution = ?, confidence = ?, source = ?, capture_mode = ?,
                    evidence_state = ?, updated_at = ?
                WHERE project_id = ? AND id = ?
                """,
                (*values, project.project_id, trace_id),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO incident_traces(
                  project_id, trace_key, status, symptom, arkts_scene, dominant_log_events,
                  diagnosis_summary, causal_chain, intervention, verification_evidence,
                  resolution, confidence, source, capture_mode, evidence_state,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (project.project_id, draft["trace_key"], *values[:-1], ts, ts),
            )
            trace_id = int(cursor.lastrowid)
        replace_links(conn, project, trace_id, links, ts)
        row = conn.execute(
            "SELECT * FROM incident_traces WHERE project_id = ? AND id = ?",
            (project.project_id, trace_id),
        ).fetchone()
        conn.commit()
    return shape_incident(row_dict(row), links)


def replace_links(
    conn: Any,
    project: Project,
    trace_id: int,
    links: list[dict[str, Any]],
    ts: str,
) -> None:
    conn.execute(
        "DELETE FROM incident_trace_links WHERE project_id = ? AND trace_id = ?",
        (project.project_id, trace_id),
    )
    for link in links:
        conn.execute(
            """
            INSERT INTO incident_trace_links(
              project_id, trace_id, target_type, target_id, target_key,
              relation, score, evidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id, trace_id, link["target_type"], link.get("target_id"),
                link.get("target_key"), link["relation"], link.get("score") or 0.0,
                link.get("evidence"), ts,
            ),
        )


def incident_trace_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    links = resolve_agent_anchors(project, args.code_anchor)
    draft = build_agent_incident(
        args.symptom, args.scene, args.diagnosis_summary, args.observed_event,
        args.causal_step, links, args.status, args.resolution, args.intervention,
        args.verification_evidence, args.confidence,
    )
    output(write_incident_record(project, draft, links), args.json)


def incident_trace_status(args: argparse.Namespace) -> None:
    if args.status not in INCIDENT_TRACE_STATUSES:
        raise SystemExit(f"unsupported incident trace status: {args.status}")
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    ts = now_iso()
    with connect(project) as conn:
        current = conn.execute(
            "SELECT * FROM incident_traces WHERE project_id = ? AND id = ?",
            (project.project_id, args.id),
        ).fetchone()
        if not current:
            raise SystemExit(f"incident trace #{args.id} not found")
        current_data = row_dict(current)
        resolution = args.resolution or current_data.get("resolution")
        intervention = args.intervention or current_data.get("intervention")
        verification = args.verification_evidence or current_data.get("verification_evidence")
        if current_data.get("capture_mode") == INCIDENT_CAPTURE_AGENT and args.status == "resolved" and not resolution:
            raise SystemExit("--resolution is required when --status resolved")
        links = [row_dict(row) for row in conn.execute(
            "SELECT * FROM incident_trace_links WHERE project_id = ? AND trace_id = ?",
            (project.project_id, args.id),
        ).fetchall()]
        state = str(current_data.get("evidence_state") or "legacy_unverified")
        confidence = float(current_data.get("confidence") or 0.0)
        if current_data.get("capture_mode") == INCIDENT_CAPTURE_AGENT:
            state = evidence_state(links, resolution, intervention, verification)
            confidence = capped_confidence(confidence, state)
        conn.execute(
            """
            UPDATE incident_traces
            SET status = ?, resolution = ?, intervention = ?, verification_evidence = ?,
                evidence_state = ?, confidence = ?, updated_at = ?
            WHERE project_id = ? AND id = ?
            """,
            (
                args.status, resolution, intervention, verification, state, confidence,
                ts, project.project_id, args.id,
            ),
        )
        row = conn.execute(
            "SELECT * FROM incident_traces WHERE project_id = ? AND id = ?",
            (project.project_id, args.id),
        ).fetchone()
        conn.commit()
    output(shape_incident(row_dict(row), links), args.json)


def shape_incident(data: dict[str, Any], links: list[dict[str, Any]]) -> dict[str, Any]:
    data["schema_version"] = "agent-incident-record/v2"
    data["observed_events"] = json_values(data.get("dominant_log_events"))
    data["agent_causal_steps"] = json_values(data.get("causal_chain"))
    data["links"] = links
    data["role_boundary"] = {
        "runtime_reads_temporary_logs": False,
        "runtime_builds_causal_chains": False,
        "agent_supplies_diagnosis_and_causal_steps": True,
    }
    return data


def anchor_parts(value: str) -> tuple[str, str]:
    normalized = str(value or "").strip().replace("\\", "/").removeprefix("./")
    path, separator, symbol = normalized.partition("::")
    return path.strip(), symbol.strip() if separator else ""


def unique_strings(values: list[str], limit: int) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))[:limit]


def json_values(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []
