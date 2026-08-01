# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .incident_trace_models import INCIDENT_TRACE_LINK_LIMIT
from .models import Project
from .records import row_dict
from .storage import connect
from .text import query_tokens, score_weighted_fields, tokenize, unique_list


def incident_fts_match_expression(query: str) -> str | None:
    tokens = unique_list([token for token in query_tokens(query) if len(token) > 1])
    if not tokens:
        return None
    quoted = ['"' + token.replace('"', '""') + '"' for token in tokens[:12]]
    return " OR ".join(quoted)


def trace_links(conn: Any, project: Project, trace_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM incident_trace_links
        WHERE project_id = ? AND trace_id = ?
        ORDER BY score DESC, id DESC
        LIMIT ?
        """,
        (project.project_id, trace_id, INCIDENT_TRACE_LINK_LIMIT),
    ).fetchall()
    return [row_dict(row) for row in rows]


def collect_incident_trace_matches(project: Project, query: str, limit: int) -> list[dict[str, Any]]:
    tokens = query_tokens(query)
    expanded_terms = set(tokens) - set(tokenize(query))
    match_expr = incident_fts_match_expression(query)
    with connect(project) as conn:
        rows = []
        if match_expr:
            rows = conn.execute(
                """
                SELECT incident_traces.*
                FROM incident_trace_fts
                JOIN incident_traces ON incident_traces.id = incident_trace_fts.rowid
                WHERE incident_trace_fts MATCH ?
                  AND incident_trace_fts.project_id = ?
                  AND incident_traces.status NOT IN ('stale', 'ignored')
                  AND incident_traces.capture_mode = 'agent_structured'
                ORDER BY bm25(incident_trace_fts)
                LIMIT ?
                """,
                (match_expr, project.project_id, limit * 3),
            ).fetchall()
        if not rows:
            like = f"%{query.strip()}%"
            rows = conn.execute(
                """
                SELECT *
                FROM incident_traces
                WHERE project_id = ?
                  AND status NOT IN ('stale', 'ignored')
                  AND capture_mode = 'agent_structured'
                  AND (
                    COALESCE(symptom, '') LIKE ?
                    OR COALESCE(dominant_log_events, '') LIKE ?
                    OR COALESCE(diagnosis_summary, '') LIKE ?
                    OR COALESCE(causal_chain, '') LIKE ?
                  )
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (project.project_id, like, like, like, like, limit * 3),
            ).fetchall()
        matches: list[dict[str, Any]] = []
        for row in rows:
            text = " ".join(
                str(row[key] or "")
                for key in (
                    "symptom",
                    "goal",
                    "arkts_scene",
                    "dominant_log_events",
                    "diagnosis_summary",
                    "causal_chain",
                    "resolution",
                    "intervention",
                    "verification_evidence",
                )
            )
            score, reasons = score_weighted_fields(
                query,
                tokens,
                expanded_terms,
                [("incident_trace", text, 1.2)],
                [("exact_incident_symptom", row["symptom"], 5.0)],
            )
            if not score:
                continue
            item = row_dict(row)
            item["score"] = round(score + float(row["confidence"] or 0), 2)
            item["match_reasons"] = reasons
            item["observed_events"] = json_list_value(row["dominant_log_events"])
            item["agent_causal_steps"] = json_list_value(row["causal_chain"])
            for key in (
                "entry_log_text", "dominant_log_events", "normalized_error",
                "suspected_chain", "causal_chain", "span_graph", "root_cause_hypothesis",
            ):
                item.pop(key, None)
            item["authority"] = "agent_reported_incident"
            item["links"] = trace_links(conn, project, int(row["id"]))
            matches.append(item)
    matches.sort(key=lambda item: (item.get("score", 0), item.get("updated_at", ""), item.get("id", 0)), reverse=True)
    return matches[:limit]


def json_list_value(value: Any) -> list[Any]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []
