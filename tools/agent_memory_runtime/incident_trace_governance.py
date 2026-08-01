# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .models import Project
from .records import row_dict
from .storage import connect
from .text import json_list, query_tokens


def stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        stripped = value.strip()
        normalized = stripped.lower()
        if not stripped or normalized in seen:
            continue
        seen.add(normalized)
        result.append(stripped)
    return result


def trace_links_by_id(project: Project, trace_id: int) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM incident_trace_links
            WHERE project_id = ? AND trace_id = ?
            ORDER BY score DESC, id DESC
            """,
            (project.project_id, trace_id),
        ).fetchall()
    return [row_dict(row) for row in rows]


def trace_has_code_anchor(project: Project, trace_id: int) -> bool:
    return any(
        link.get("target_type") in {"code_log_statement", "code_file", "code_symbol", "memory_edge"}
        for link in trace_links_by_id(project, trace_id)
    )


def reflection_template_for_trace(project: Project, trace: dict[str, Any]) -> dict[str, Any]:
    links = trace_links_by_id(project, int(trace["id"]))
    link_terms = [
        str(link.get("target_key") or "")
        for link in links
        if str(link.get("target_key") or "").strip()
    ]
    events = json_list(trace.get("dominant_log_events"))
    useful_terms = stable_unique([*events, *query_tokens(trace.get("symptom") or ""), *query_tokens(" ".join(events)), *link_terms])[:10]
    inspection_targets = stable_unique(
        [
            target.split("::", 1)[0]
            for target in link_terms
            if target.strip()
        ]
    )
    return {
        "experience_type": "procedure_experience",
        "task_type": "diagnosis",
        "outcome": "success",
        "problem": trace.get("symptom"),
        "task": f"diagnose {trace.get('arkts_scene')} incident",
        "summary": trace.get("resolution") or trace.get("diagnosis_summary") or trace.get("normalized_error"),
        "reasoning_summary": trace.get("causal_chain"),
        "trigger_condition": trace.get("symptom"),
        "repair_action": trace.get("intervention") or trace.get("resolution"),
        "verification_method": trace.get("verification_evidence"),
        "useful_followup_focus": trace.get("arkts_scene"),
        "useful_followup_terms": useful_terms,
        "inspection_targets": inspection_targets,
        "source_cases": [f"incident_trace:{trace['id']}"],
        "reuse_feedback": "candidate until reused",
        "confidence": trace.get("confidence") or 0.7,
    }


def build_incident_trace_actions(project: Project, limit: int = 20) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = [
            row_dict(row)
            for row in conn.execute(
                """
                SELECT *
                FROM incident_traces
                WHERE project_id = ?
                  AND status NOT IN ('stale', 'ignored')
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (project.project_id, limit * 3),
            ).fetchall()
        ]
    actions: list[dict[str, Any]] = []
    for trace in rows:
        trace_id = int(trace["id"])
        has_anchor = trace_has_code_anchor(project, trace_id)
        capture_mode = str(trace.get("capture_mode") or "legacy_runtime_derived")
        evidence_state = str(trace.get("evidence_state") or "legacy_unverified")
        if capture_mode != "agent_structured":
            actions.append(
                {
                    "action": "review_legacy_incident_trace",
                    "governance_lane": "incident_trace",
                    "type": "incident_trace",
                    "id": trace_id,
                    "arkts_scene": trace.get("arkts_scene"),
                    "evidence_state": "legacy_unverified",
                    "reason": "legacy Runtime-derived trace is quarantined from Context and cannot be promoted",
                    "risk": "high",
                    "requires_confirmation": True,
                    "command": None,
                    "suggested_actions": [
                        "inspect the original task evidence outside Runtime",
                        "record a new Agent-structured incident outcome when still valid",
                        "mark this legacy trace stale or ignored",
                    ],
                }
            )
            continue
        if trace.get("status") == "resolved" and has_anchor and evidence_state == "verified":
            actions.append(
                {
                    "action": "promote_incident_trace_to_reflection",
                    "governance_lane": "incident_trace",
                    "type": "incident_trace",
                    "id": trace_id,
                    "arkts_scene": trace.get("arkts_scene"),
                    "evidence_state": evidence_state,
                    "reason": "resolved incident trace has code anchors and can be reviewed as a diagnosis reflection",
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": None,
                    "reflection_payload_template": reflection_template_for_trace(project, trace),
                }
            )
        elif evidence_state in {"reported", "supported"}:
            actions.append(
                {
                    "action": "complete_incident_verification",
                    "governance_lane": "incident_trace",
                    "type": "incident_trace",
                    "id": trace_id,
                    "arkts_scene": trace.get("arkts_scene"),
                    "evidence_state": evidence_state,
                    "reason": "Agent-reported incident lacks anchored intervention and verification closure",
                    "risk": "medium",
                    "requires_confirmation": False,
                    "command": None,
                    "suggested_actions": [
                        "confirm at least one current code anchor",
                        "record the applied intervention",
                        "record repeatable verification evidence",
                    ],
                }
            )
        if not has_anchor:
            actions.append(
                {
                    "action": "review_log_anchor_gap",
                    "governance_lane": "incident_trace",
                    "type": "incident_trace",
                    "id": trace_id,
                    "arkts_scene": trace.get("arkts_scene"),
                    "reason": "Agent-reported incident has no anchor in the current learned code index",
                    "risk": "low",
                    "requires_confirmation": False,
                    "command": None,
                    "suggested_actions": [
                        "learn the missing ArkTS scope",
                        "add or enrich code log business semantics",
                        "ignore if the runtime log is one-off noise",
                    ],
                }
            )
    return actions[:limit]
