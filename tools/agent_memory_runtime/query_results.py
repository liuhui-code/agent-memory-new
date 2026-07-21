# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .incident_trace_models import INCIDENT_TRACE_QUERY_LIMIT
from .memory_calibration import calibrate_payload
from .models import Project
from .query_code_selection import diverse_code_matches
from .query_collect import collect_matches_with_audit
from .query_edges import network_limits
from .query_followups import infer_followup_focus, suggested_followup_terms
from .query_handoff import build_query_handoff
from .query_intents import gate_matches_by_intent
from .storage import connect, now_iso

SEARCH_RESULT_LIMITS = {
    "semantic_facts": 20,
    "reflections": 10,
    "episodes": 10,
    "wiki_matches": 20,
    "code_log_matches": 20,
    "edge_matches": 10,
    "incident_trace_matches": 10,
}


CONTEXT_RESULT_LIMITS = {
    "semantic_facts": 3,
    "reflections": 3,
    "episodes": 2,
    "wiki_matches": 5,
    "code_log_matches": 5,
    "edge_matches": 10,
    "incident_trace_matches": 5,
}

def limited_matches(
    matches: dict[str, list[dict[str, Any]]],
    limits: dict[str, int],
    query: str = "",
) -> dict[str, list[dict[str, Any]]]:
    bounded = {
        key: value[: limits.get(key, len(value))]
        for key, value in matches.items()
    }
    wiki_limit = limits.get("wiki_matches", len(matches.get("wiki_matches", [])))
    bounded["wiki_matches"] = diverse_code_matches(
        matches.get("wiki_matches", []),
        wiki_limit,
        query=query,
    )
    return bounded


def limited_context(
    project: Project,
    query: str,
    enable_passage_shadow: bool = False,
) -> dict[str, Any]:
    collection = collect_matches_with_audit(
        project, query, enable_passage_shadow=enable_passage_shadow
    )
    matches = collection.matches
    gated = gate_matches_by_intent(project, query, matches)
    bounded = limited_matches(gated["matches"], CONTEXT_RESULT_LIMITS, query)
    bounded["code_log_matches"] = [
        {key: value for key, value in item.items() if key != "likely_causes"}
        for item in bounded["code_log_matches"]
    ]
    followup_focus = infer_followup_focus(query, bounded)
    context = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "query": query,
        "memory_intent": gated["memory_intent"],
        "memory_intent_v2": gated["memory_intent_v2"],
        "retrieval_lanes": gated["retrieval_lanes"],
        "memory_brief": gated["memory_brief"],
        "followup_focus": followup_focus,
        "advisory_notice": "Memory is advisory. Current source files and explicit user instructions override stored memory.",
        "semantic_facts": bounded["semantic_facts"],
        "reflections": bounded["reflections"],
        "episodes": bounded["episodes"],
        "wiki_matches": bounded["wiki_matches"],
        "code_log_matches": bounded["code_log_matches"],
        "edge_matches": bounded["edge_matches"],
        "incident_trace_matches": bounded["incident_trace_matches"][:INCIDENT_TRACE_QUERY_LIMIT],
        "correction_guards": gated["correction_guards"],
        "semantic_patch_notes": gated["semantic_patch_notes"],
        "blocked_memory_notes": gated["blocked_memory_notes"],
        "conflict_notes": gated["conflict_notes"],
        "suggested_followup_terms": suggested_followup_terms(query, bounded),
        "query_handoff": build_query_handoff(query, bounded),
        "network_limits": network_limits(),
        "source_freshness": collection.recall_audit.get("source_freshness", {}),
    }
    calibrate_payload(context)
    context["query_audit"] = build_query_audit(
        context,
        collection.recall_audit,
        retrieval_stage_counts(matches, gated["matches"], bounded),
    )
    record_context_use(project, context)
    record_query_miss_if_empty(project, "context", query, context)
    return context



def limited_search(
    project: Project,
    query: str,
    cursor: int = 0,
    per_type_limit: int | None = None,
    aggregate_limit: int | None = None,
) -> dict[str, Any]:
    collection = collect_matches_with_audit(project, query)
    matches = collection.matches
    gated = gate_matches_by_intent(project, query, matches)
    gated["matches"]["code_log_matches"] = [
        {key: value for key, value in item.items() if key != "likely_causes"}
        for item in gated["matches"]["code_log_matches"]
    ]
    payload = batched_search(gated["matches"], query=query, cursor=cursor, per_type_limit=per_type_limit, aggregate_limit=aggregate_limit)
    payload["memory_intent"] = gated["memory_intent"]
    payload["memory_intent_v2"] = gated["memory_intent_v2"]
    payload["retrieval_lanes"] = gated["retrieval_lanes"]
    payload["memory_brief"] = gated["memory_brief"]
    payload["correction_guards"] = gated["correction_guards"]
    payload["semantic_patch_notes"] = gated["semantic_patch_notes"]
    payload["blocked_memory_notes"] = gated["blocked_memory_notes"]
    payload["conflict_notes"] = gated["conflict_notes"]
    payload["source_freshness"] = collection.recall_audit.get("source_freshness", {})
    calibrate_payload(payload)
    payload["query_audit"] = build_query_audit(
        payload,
        collection.recall_audit,
        retrieval_stage_counts(matches, gated["matches"], payload),
    )
    return payload



def build_query_audit(
    payload: dict[str, Any],
    candidate_recall: dict[str, Any] | None = None,
    retrieval_stages: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result_keys = [
        "semantic_facts",
        "reflections",
        "episodes",
        "wiki_matches",
        "code_log_matches",
        "edge_matches",
        "incident_trace_matches",
    ]
    result_counts = {
        key: len(payload.get(key) or [])
        for key in result_keys
        if isinstance(payload.get(key), list)
    }
    top_explanations: dict[str, list[dict[str, Any]]] = {}
    for key in result_keys:
        values = payload.get(key)
        if not isinstance(values, list):
            continue
        explanations = [compact_query_explanation(key, item) for item in values if isinstance(item, dict)]
        explanations.sort(
            key=lambda item: (
                float(item.get("rerank_score") or item.get("score") or 0.0),
                float(item.get("trust_score") or 0.0),
                int(item.get("id") or 0),
            ),
            reverse=True,
        )
        top_explanations[key] = explanations[:3]
    return {
        "result_counts": result_counts,
        "candidate_recall": candidate_recall or {},
        "retrieval_stages": retrieval_stages or {},
        "top_explanations": top_explanations,
        "audit_notice": "Ranking audit is advisory; inspect current source before trusting historical memory.",
    }



def compact_query_explanation(result_type: str, item: dict[str, Any]) -> dict[str, Any]:
    explanation = item.get("retrieval_explanation") if isinstance(item.get("retrieval_explanation"), dict) else {}
    return {
        "type": result_type,
        "id": item.get("id"),
        "score": item.get("score"),
        "rerank_score": item.get("rerank_score"),
        "quality_score": item.get("quality_score"),
        "trust_score": item.get("trust_score"),
        "trust_level": item.get("trust_level"),
        "feedback_penalty": item.get("feedback_penalty", 0.0),
        "usage_feedback_bonus": item.get("usage_feedback_bonus", 0.0),
        "usage_feedback_penalty": item.get("usage_feedback_penalty", 0.0),
        "match_reasons": item.get("match_reasons") or explanation.get("match_reasons") or [],
        "recall_lanes": item.get("recall_lanes") or [],
        "recall_fusion": item.get("recall_fusion") or {},
        "gate_reasons": item.get("gate_reasons") or explanation.get("gate_reasons") or [],
        "retrieval_explanation": explanation,
    }


def retrieval_stage_counts(
    scored: dict[str, list[dict[str, Any]]],
    intent_gated: dict[str, list[dict[str, Any]]],
    selected: dict[str, Any],
) -> dict[str, dict[str, int]]:
    keys = (
        "semantic_facts", "reflections", "episodes", "wiki_matches",
        "code_log_matches", "edge_matches", "incident_trace_matches",
    )
    return {
        "scored": {key: len(scored.get(key) or []) for key in keys},
        "after_intent_gate": {key: len(intent_gated.get(key) or []) for key in keys},
        "selected": {
            key: len(selected.get(key) or [])
            if isinstance(selected.get(key), list) else 0
            for key in keys
        },
    }



def batched_search(
    matches: dict[str, list[dict[str, Any]]],
    query: str = "",
    cursor: int = 0,
    per_type_limit: int | None = None,
    aggregate_limit: int | None = None,
) -> dict[str, Any]:
    effective_per_type_limit = max(1, per_type_limit or max(SEARCH_RESULT_LIMITS.values()))
    effective_aggregate_limit = max(1, aggregate_limit or sum(SEARCH_RESULT_LIMITS.values()))
    safe_cursor = max(0, cursor)
    followup_focus = infer_followup_focus(query, matches)

    candidates: list[dict[str, Any]] = []
    total_candidates_by_type: dict[str, int] = {}
    for key, items in matches.items():
        total_candidates_by_type[key] = len(items)
        window_size = min(len(items), safe_cursor + effective_per_type_limit)
        for item in items[:window_size]:
            candidate = dict(item)
            candidate["_match_type"] = key
            candidates.append(candidate)

    candidates.sort(key=lambda item: (item.get("score", 0), item.get("created_at", ""), item.get("id", 0)), reverse=True)
    visible = candidates[safe_cursor : safe_cursor + effective_aggregate_limit]
    next_cursor = safe_cursor + len(visible) if safe_cursor + len(visible) < len(candidates) else None

    payload: dict[str, list[dict[str, Any]]] = {key: [] for key in matches}
    returned_counts_by_type: dict[str, int] = {key: 0 for key in matches}
    for item in visible:
        item_type = str(item.pop("_match_type"))
        returned_counts_by_type[item_type] += 1
        payload[item_type].append(item)

    payload["result_limits"] = SEARCH_RESULT_LIMITS.copy()
    payload["cursor"] = safe_cursor
    payload["per_type_limit"] = effective_per_type_limit
    payload["aggregate_limit"] = effective_aggregate_limit
    payload["followup_focus"] = followup_focus
    payload["truncated"] = next_cursor is not None
    payload["next_cursor"] = next_cursor
    payload["total_candidates_by_type"] = total_candidates_by_type
    payload["returned_counts_by_type"] = returned_counts_by_type
    payload["suggested_followup_terms"] = suggested_followup_terms(query, payload)
    return payload



def record_context_use(project: Project, context_data: dict[str, Any]) -> None:
    ts = now_iso()
    updates = [
        ("semantic_facts", context_data.get("semantic_facts", [])),
        ("reflections", context_data.get("reflections", [])),
        ("episodes", context_data.get("episodes", [])),
    ]
    with connect(project) as conn:
        for table, items in updates:
            for item in items:
                conn.execute(
                    f"""
                    UPDATE {table}
                    SET use_count = COALESCE(use_count, 0) + 1,
                        last_used_at = ?
                    WHERE project_id = ? AND id = ?
                    """,
                    (ts, project.project_id, item["id"]),
                )
        conn.commit()



def result_counts(data: dict[str, Any]) -> dict[str, int]:
    return {
        key: len(value)
        for key, value in data.items()
        if isinstance(value, list)
    }



def has_any_result(data: dict[str, Any]) -> bool:
    return any(result_counts(data).values())



def normalize_query_miss(query: str) -> str:
    return " ".join(query.lower().split())



def record_query_miss_if_empty(project: Project, source: str, query: str, data: dict[str, Any]) -> None:
    counts = result_counts(data)
    if any(counts.values()):
        return
    normalized_query = normalize_query_miss(query)
    ts = now_iso()
    counts_json = json.dumps(counts, ensure_ascii=False)
    with connect(project) as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM query_misses
            WHERE project_id = ?
              AND source = ?
              AND normalized_query = ?
              AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """,
            (project.project_id, source, normalized_query),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE query_misses
                SET result_counts = ?,
                    last_seen_at = ?,
                    miss_count = COALESCE(miss_count, 1) + 1
                WHERE project_id = ? AND id = ?
                """,
                (counts_json, ts, project.project_id, existing["id"]),
            )
            conn.commit()
            return
        conn.execute(
            """
            INSERT INTO query_misses(
              project_id, query, normalized_query, source, result_counts,
              created_at, last_seen_at, miss_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                project.project_id,
                query,
                normalized_query,
                source,
                counts_json,
                ts,
                ts,
            ),
        )
        conn.commit()
