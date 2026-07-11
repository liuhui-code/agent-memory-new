# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .incident_trace_builder import build_incident_trace_draft
from .incident_trace_models import INCIDENT_LOG_FILE_BYTES_LIMIT, INCIDENT_TRACE_STATUSES
from .records import output, row_dict
from .storage import connect, ensure_initialized, now_iso, resolve_project


def read_incident_log_text(args: argparse.Namespace) -> str:
    if bool(args.log_text) == bool(args.log_file):
        raise SystemExit("provide exactly one of --log-text or --log-file")
    if args.log_text:
        return str(args.log_text)
    path = Path(args.log_file).expanduser()
    try:
        return path.read_bytes()[:INCIDENT_LOG_FILE_BYTES_LIMIT].decode("utf-8", errors="replace")
    except OSError as exc:
        raise SystemExit(f"failed to read log file: {path}") from exc


def write_incident_trace(project: Any, draft: dict[str, Any]) -> dict[str, Any]:
    ts = now_iso()
    dominant_events = json.dumps(draft.get("dominant_log_events") or [], ensure_ascii=False)
    with connect(project) as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM incident_traces
            WHERE project_id = ? AND trace_key = ?
            """,
            (project.project_id, draft["trace_key"]),
        ).fetchone()
        if existing:
            trace_id = int(existing["id"])
            conn.execute(
                """
                UPDATE incident_traces
                SET symptom = ?, arkts_scene = ?, entry_log_text = ?, normalized_error = ?,
                    dominant_log_events = ?, suspected_chain = ?, confidence = ?, updated_at = ?
                WHERE project_id = ? AND id = ?
                """,
                (
                    draft["symptom"],
                    draft["arkts_scene"],
                    draft["entry_log_text"],
                    draft.get("normalized_error"),
                    dominant_events,
                    draft.get("suspected_chain"),
                    0.7,
                    ts,
                    project.project_id,
                    trace_id,
                ),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO incident_traces(
                  project_id, trace_key, status, symptom, arkts_scene, entry_log_text,
                  normalized_error, dominant_log_events, suspected_chain,
                  confidence, source, created_at, updated_at
                )
                VALUES (?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, 'incident-trace', ?, ?)
                """,
                (
                    project.project_id,
                    draft["trace_key"],
                    draft["symptom"],
                    draft["arkts_scene"],
                    draft["entry_log_text"],
                    draft.get("normalized_error"),
                    dominant_events,
                    draft.get("suspected_chain"),
                    0.7,
                    ts,
                    ts,
                ),
            )
            trace_id = int(cur.lastrowid)
        conn.execute(
            "DELETE FROM incident_trace_links WHERE project_id = ? AND trace_id = ?",
            (project.project_id, trace_id),
        )
        for link in draft.get("linked_targets") or []:
            conn.execute(
                """
                INSERT INTO incident_trace_links(
                  project_id, trace_id, target_type, target_id, target_key,
                  relation, score, evidence, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.project_id,
                    trace_id,
                    link["target_type"],
                    link.get("target_id"),
                    link.get("target_key"),
                    link["relation"],
                    link.get("score") or 0.0,
                    link.get("evidence"),
                    ts,
                ),
            )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM incident_traces WHERE project_id = ? AND id = ?",
            (project.project_id, trace_id),
        ).fetchone()
    data = row_dict(row)
    data["dominant_log_events"] = draft.get("dominant_log_events") or []
    data["matched_code_logs"] = draft.get("matched_code_logs") or []
    data["linked_targets"] = draft.get("linked_targets") or []
    data["candidate_chain"] = draft.get("candidate_chain") or []
    data["inspection_targets"] = draft.get("inspection_targets") or []
    data["suggested_followup_query"] = draft.get("suggested_followup_query") or ""
    data["scene_reasons"] = draft.get("scene_reasons") or []
    return data


def incident_trace_command(args: argparse.Namespace) -> None:
    if not str(args.symptom or "").strip():
        raise SystemExit("--symptom is required")
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    log_text = read_incident_log_text(args)
    draft = build_incident_trace_draft(project, args.symptom, log_text)
    output(write_incident_trace(project, draft), args.json)


def incident_trace_status(args: argparse.Namespace) -> None:
    if args.status not in INCIDENT_TRACE_STATUSES:
        raise SystemExit(f"unsupported incident trace status: {args.status}")
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    ts = now_iso()
    with connect(project) as conn:
        conn.execute(
            """
            UPDATE incident_traces
            SET status = ?, resolution = COALESCE(?, resolution), updated_at = ?
            WHERE project_id = ? AND id = ?
            """,
            (args.status, args.resolution, ts, project.project_id, args.id),
        )
        row = conn.execute(
            "SELECT * FROM incident_traces WHERE project_id = ? AND id = ?",
            (project.project_id, args.id),
        ).fetchone()
        conn.commit()
    if not row:
        raise SystemExit(f"incident trace #{args.id} not found")
    output(row_dict(row), args.json)

