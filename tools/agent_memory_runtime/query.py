# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import re
from typing import Any

from .models import (
    EVIDENCE_CHAIN_LIMIT,
    NETWORK_EDGE_LIMIT,
    NETWORK_MAX_DEPTH,
    Project,
    QUERY_FTS_RECALL_LIMITS,
    QUERY_ALLOWED_EDGE_RELATIONS,
)
from .incident_trace_models import INCIDENT_TRACE_QUERY_LIMIT, INCIDENT_TRACE_SEARCH_LIMIT
from .incident_trace_query import collect_incident_trace_matches
from .records import memory_warning, row_dict
from .storage import connect, now_iso
from .text import code_search_terms, json_list, query_tokens, score_weighted_fields, tokenize, unique_list

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

BATCHED_EDGE_TARGET_SIZE = 200

FTS_TABLES = {
    "semantic_facts": "semantic_fact_fts",
    "reflections": "reflection_fts",
    "episodes": "episode_fts",
    "code_files": "code_file_fts",
    "code_symbols": "code_symbol_fts",
    "code_log_statements": "code_log_fts",
}

LIKE_RECALL_COLUMNS = {
    "semantic_facts": ("fact", "source", "category", "scope", "evidence"),
    "reflections": (
        "task",
        "summary",
        "lesson",
        "future_rule",
        "problem",
        "reasoning_summary",
        "useful_followup_terms",
        "inspection_targets",
        "verification_method",
        "source_cases",
        "skill_candidate",
        "evidence",
        "anchor_type",
        "anchor_key",
        "semantic_field",
        "existing_value",
        "proposed_value",
        "patch_reason",
    ),
    "episodes": ("task", "summary", "outcome", "files_touched", "commands_run"),
    "code_files": ("file_path", "summary", "business_summary", "business_terms"),
    "code_symbols": ("file_path", "symbol", "symbol_type", "summary", "business_summary", "business_terms"),
    "code_log_statements": ("file_path", "function", "logger", "message_template", "raw_statement", "business_summary", "business_terms", "business_event", "trigger_stage", "symptom_terms", "likely_causes", "process_hint", "neighbor_terms"),
}

FOCUS_PRIORITY_TERMS = {
    "route": ["route", "routes", "router", "pushurl", "replaceurl", "navigation", "page", "pages", "pagestack"],
    "resource": ["resource", "resources", "media", "image", "string", "app.media", "app.string", "$r"],
    "config": ["permission", "permissions", "dependency", "dependencies", "ability", "module", "json5", "config"],
    "log": ["log", "logger", "console", "hilog", "error", "warning", "exception", "failed", "failure", "debug"],
}

MEMORY_INTENTS = {
    "code_current",
    "procedure_reuse",
    "correction_guard",
    "semantic_lookup",
    "incident_diagnosis",
    "general_context",
}

REFLECTION_LANE_LIMITS = {
    "correction_guards": 4,
    "semantic_patch_notes": 6,
    "blocked_memory_notes": 8,
    "conflict_notes": 5,
}


def fts_match_expression(query: str) -> str | None:
    tokens = unique_list([token for token in query_tokens(query) if len(token) > 1])
    if not tokens:
        return None
    quoted = ['"' + token.replace('"', '""') + '"' for token in tokens[:12]]
    return " OR ".join(quoted)


def recall_candidate_ids(
    conn: Any,
    project: Project,
    table_name: str,
    query: str,
    limit: int,
) -> list[int]:
    match_expr = fts_match_expression(query)
    ids: list[int] = []
    if match_expr:
        fts_table = FTS_TABLES[table_name]
        rows = conn.execute(
            f"""
            SELECT rowid
            FROM {fts_table}
            WHERE {fts_table} MATCH ?
              AND project_id = ?
            ORDER BY bm25({fts_table})
            LIMIT ?
            """,
            (match_expr, project.project_id, limit),
        ).fetchall()
        ids = [int(row["rowid"]) for row in rows]
    if ids:
        return ids
    return like_recall_candidate_ids(conn, project, table_name, query, limit)


def like_recall_candidate_ids(
    conn: Any,
    project: Project,
    table_name: str,
    query: str,
    limit: int,
) -> list[int]:
    columns = LIKE_RECALL_COLUMNS[table_name]
    original_tokens = tokenize(query)
    expanded_tokens = [token for token in query_tokens(query) if token not in original_tokens]
    focus = focus_from_query(query)
    focus_terms = [term for term in FOCUS_PRIORITY_TERMS.get(focus or "", []) if term in expanded_tokens]
    other_expanded_terms = [term for term in expanded_tokens if term not in focus_terms]
    primary_original = original_tokens[:1]
    secondary_original = original_tokens[1:]
    terms = unique_list([*primary_original, *focus_terms, *secondary_original, *other_expanded_terms, query.strip()])
    terms = [term for term in terms if len(term.strip()) > 1][:12]
    if not terms:
        return []
    term_clauses: list[str] = []
    params: list[Any] = [project.project_id]
    for term in terms:
        column_clauses = [f"COALESCE({column}, '') LIKE ?" for column in columns]
        term_clauses.append("(" + " OR ".join(column_clauses) + ")")
        params.extend([f"%{term.strip()}%"] * len(columns))
    rows = conn.execute(
        f"""
        SELECT id
        FROM {table_name}
        WHERE project_id = ?
          AND ({' OR '.join(term_clauses)})
        ORDER BY id DESC
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def fetch_rows_by_ids(
    conn: Any,
    base_table: str,
    project: Project,
    ids: list[int],
    extra_where: str = "",
) -> list[Any]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    return conn.execute(
        f"""
        SELECT *
        FROM {base_table}
        WHERE project_id = ?
          AND id IN ({placeholders})
          {extra_where}
        """,
        (project.project_id, *ids),
    ).fetchall()


def collect_matches(project: Project, query: str) -> dict[str, list[dict[str, Any]]]:
    tokens = query_tokens(query)
    original_terms = set(tokenize(query))
    expanded_terms = set(tokens) - original_terms
    results: dict[str, list[dict[str, Any]]] = {
        "semantic_facts": [],
        "reflections": [],
        "episodes": [],
        "wiki_matches": [],
        "code_log_matches": [],
        "edge_matches": [],
        "incident_trace_matches": [],
    }
    with connect(project) as conn:
        semantic = fetch_rows_by_ids(
            conn,
            "semantic_facts",
            project,
            recall_candidate_ids(conn, project, "semantic_facts", query, QUERY_FTS_RECALL_LIMITS["semantic_facts"]),
            "AND COALESCE(is_stale, 0) = 0 AND COALESCE(status, 'active') = 'active'",
        )
        reflections = fetch_rows_by_ids(
            conn,
            "reflections",
            project,
            recall_candidate_ids(conn, project, "reflections", query, QUERY_FTS_RECALL_LIMITS["reflections"]),
            "AND COALESCE(is_stale, 0) = 0 AND COALESCE(status, 'active') = 'active'",
        )
        episodes = fetch_rows_by_ids(
            conn,
            "episodes",
            project,
            recall_candidate_ids(conn, project, "episodes", query, QUERY_FTS_RECALL_LIMITS["episodes"]),
            "AND COALESCE(status, 'active') = 'active'",
        )
        files = fetch_rows_by_ids(
            conn,
            "code_files",
            project,
            recall_candidate_ids(conn, project, "code_files", query, QUERY_FTS_RECALL_LIMITS["code_files"]),
        )
        symbols = fetch_rows_by_ids(
            conn,
            "code_symbols",
            project,
            recall_candidate_ids(conn, project, "code_symbols", query, QUERY_FTS_RECALL_LIMITS["code_symbols"]),
        )
        logs = fetch_rows_by_ids(
            conn,
            "code_log_statements",
            project,
            recall_candidate_ids(conn, project, "code_log_statements", query, QUERY_FTS_RECALL_LIMITS["code_log_statements"]),
        )
    results["incident_trace_matches"] = collect_incident_trace_matches(project, query, INCIDENT_TRACE_SEARCH_LIMIT)

    for row in semantic:
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [("semantic_fact", row["fact"], 1.0)],
            [("exact_semantic_fact", row["fact"], 2.0)],
        )
        if score:
            item = row_dict(row)
            item["score"] = score + float(row["confidence"] or 0)
            item["match_reasons"] = reasons
            item["warning"] = memory_warning(item)
            results["semantic_facts"].append(item)

    for row in reflections:
        text = " ".join(
            str(row[key] or "")
            for key in (
                "task",
                "task_type",
                "outcome",
                "problem",
                "summary",
                "reasoning_summary",
                "context_used",
                "what_worked",
                "what_failed",
                "hidden_assumptions",
                "negative_preconditions",
                "verification_method",
                "reuse_feedback",
                "source_cases",
                "skill_candidate",
                "mistake",
                "lesson",
                "future_rule",
                "trigger_condition",
                "repair_action",
                "evidence",
            )
        )
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [("reflection", text, 1.0)],
            [("exact_reflection", text, 2.0)],
        )
        if score:
            item = row_dict(row)
            item["score"] = score
            item["match_reasons"] = reasons
            item["warning"] = memory_warning(item)
            results["reflections"].append(item)

    for row in episodes:
        text = f"{row['task']} {row['summary']} {row['outcome'] or ''}"
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [("episode", text, 0.8)],
            [("exact_episode", text, 1.5)],
        )
        if score:
            item = row_dict(row)
            item["score"] = score
            item["match_reasons"] = reasons
            item["warning"] = memory_warning(item)
            results["episodes"].append(item)

    for row in files:
        search_terms = code_search_terms("file", row)
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [
                ("business_terms", " ".join(json_list(row["business_terms"])), 5.0),
                ("business_summary", row["business_summary"] or "", 3.0),
                ("file_path", row["file_path"], 3.0),
                ("file_summary", row["summary"] or "", 1.0),
                ("file_language", row["language"] or "", 0.6),
                ("search_terms", " ".join(search_terms), 0.8),
            ],
            [("exact_file_path", row["file_path"], 12.0)],
        )
        if score:
            item = row_dict(row)
            item["kind"] = "file"
            item["score"] = score
            item["search_terms"] = search_terms
            item["business_terms"] = json_list(row["business_terms"])
            item["match_reasons"] = reasons
            results["wiki_matches"].append(item)

    for row in symbols:
        search_terms = code_search_terms("symbol", row)
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [
                ("business_terms", " ".join(json_list(row["business_terms"])), 5.0),
                ("business_summary", row["business_summary"] or "", 3.0),
                ("file_path", row["file_path"], 2.0),
                ("symbol", row["symbol"], 4.0),
                ("symbol_type", row["symbol_type"] or "", 2.0),
                ("symbol_summary", row["summary"] or "", 1.5),
                ("search_terms", " ".join(search_terms), 1.0),
            ],
            [
                ("exact_symbol", row["symbol"], 12.0),
                ("exact_file_path", row["file_path"], 4.0),
            ],
        )
        if score:
            item = row_dict(row)
            item["kind"] = "symbol"
            item["score"] = score
            item["search_terms"] = search_terms
            item["business_terms"] = json_list(row["business_terms"])
            item["match_reasons"] = reasons
            results["wiki_matches"].append(item)

    for row in logs:
        search_terms = code_search_terms("log_statement", row)
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [
                ("business_terms", " ".join(json_list(row["business_terms"])), 5.0),
                ("symptom_terms", " ".join(json_list(row["symptom_terms"])), 5.0),
                ("likely_causes", " ".join(json_list(row["likely_causes"])), 4.0),
                ("business_summary", row["business_summary"] or "", 3.0),
                ("business_event", row["business_event"] or "", 4.0),
                ("trigger_stage", row["trigger_stage"] or "", 2.5),
                ("process_hint", row["process_hint"] or "", 2.5),
                ("neighbor_terms", " ".join(json_list(row["neighbor_terms"])), 2.0),
                ("log_message", row["message_template"], 3.0),
                ("log_context", " ".join(str(row[key] or "") for key in ("file_path", "function", "level", "logger", "raw_statement")), 1.2),
                ("search_terms", " ".join(search_terms), 1.0),
            ],
            [
                ("exact_log_message", row["message_template"], 12.0),
                ("exact_file_path", row["file_path"], 4.0),
                ("exact_function", row["function"] or "", 5.0),
                ("exact_business_event", row["business_event"] or "", 7.0),
            ],
        )
        if score:
            item = row_dict(row)
            item["kind"] = "log_statement"
            item["score"] = score
            item["search_terms"] = search_terms
            item["business_terms"] = json_list(row["business_terms"])
            item["match_reasons"] = reasons
            results["code_log_matches"].append(item)

    edge_targets: dict[str, set[int]] = {
        "code_file": set(),
        "code_symbol": set(),
        "code_log_statement": set(),
    }
    for item in results["wiki_matches"]:
        if item.get("kind") == "file":
            edge_targets["code_file"].add(int(item["id"]))
        elif item.get("kind") == "symbol":
            edge_targets["code_symbol"].add(int(item["id"]))
    for item in results["code_log_matches"]:
        edge_targets["code_log_statement"].add(int(item["id"]))
    if any(edge_targets.values()):
        results["edge_matches"] = collect_related_edges(project, edge_targets)

    for key in results:
        results[key].sort(key=lambda item: (item.get("score", 0), item.get("created_at", "")), reverse=True)
    return results


def infer_memory_intent(query: str) -> str:
    lowered = query.lower()
    if any(token in lowered for token in ("日志", "报错", "错误", "异常", "失败", "崩溃", "incident", "log", "traceback", "exception")):
        return "incident_diagnosis"
    if any(token in lowered for token in ("业务语义", "业务含义", "语义", "semantic", "business meaning", "business_summary", "business_terms", "补充", "纠正")):
        return "semantic_lookup"
    if any(token in lowered for token in ("误导", "错误经验", "纠错", "冲突", "不要", "避免", "correction", "wrong", "misleading")):
        return "correction_guard"
    if any(token in lowered for token in ("如何", "怎么", "步骤", "流程", "方案", "procedure", "playbook", "workflow", "how to")):
        return "procedure_reuse"
    if any(token in lowered for token in ("代码", "函数", "文件", "调用", "当前", "source", "code", "function", "file")):
        return "code_current"
    return "general_context"


def text_for_reflection_gate(item: dict[str, Any]) -> str:
    fields = [
        "task",
        "summary",
        "mistake",
        "lesson",
        "future_rule",
        "problem",
        "reasoning_summary",
        "context_used",
        "what_worked",
        "what_failed",
        "hidden_assumptions",
        "negative_preconditions",
        "useful_followup_terms",
        "misleading_followup_terms",
        "inspection_targets",
        "final_verification_path",
        "related_cases",
        "verification_method",
        "reuse_feedback",
        "source_cases",
        "skill_candidate",
        "scope",
        "evidence",
        "trigger_condition",
        "anti_pattern",
        "repair_action",
        "applies_to",
        "does_not_apply_to",
        "anchor_type",
        "anchor_key",
        "semantic_field",
        "existing_value",
        "proposed_value",
        "patch_reason",
    ]
    return " ".join(str(item.get(field) or "") for field in fields)


def token_overlap_score(query: str, text: str) -> float:
    query_set = {token for token in query_tokens(query) if len(token) > 1}
    text_set = {token for token in query_tokens(text) if len(token) > 1}
    if not query_set or not text_set:
        return 0.0
    return len(query_set & text_set) / max(1, len(query_set))


def reflection_memory_lane(item: dict[str, Any]) -> str:
    experience_type = str(item.get("experience_type") or "")
    if experience_type == "procedure_experience":
        return "reusable_procedure"
    if experience_type == "correction_experience":
        return "correction_guard"
    if experience_type == "semantic_patch_experience":
        return "semantic_patch"
    return "historical_reflection"


def reflection_gate_decision(query: str, intent: str, item: dict[str, Any]) -> dict[str, Any]:
    lane = reflection_memory_lane(item)
    text = text_for_reflection_gate(item)
    overlap = token_overlap_score(query, text)
    base_score = float(item.get("score") or 0)
    confidence = float(item.get("confidence") or 0.8)
    score = min(100.0, base_score * 4.0 + overlap * 40.0 + confidence * 10.0)
    reasons: list[str] = []

    if overlap:
        reasons.append("query_terms_overlap_reflection")
    if confidence >= 0.8:
        reasons.append("confidence_ok")
    if item.get("verification_method"):
        score += 8
        reasons.append("has_verification_method")
    if item.get("source_cases"):
        score += 6
        reasons.append("has_source_cases")
    if item.get("last_outcome") == "misleading":
        score -= 35
        reasons.append("previously_misleading")
    if float(item.get("misleading_score") or 0.0) > 0:
        score -= min(25, float(item.get("misleading_score") or 0.0) * 25)
        reasons.append("explicit_misleading_score")

    if lane == "reusable_procedure":
        allowed = intent in {"procedure_reuse", "general_context", "incident_diagnosis"}
        if allowed:
            score += 18
            reasons.append("procedure_lane_matches_intent")
        else:
            score -= 20
            reasons.append("procedure_lane_not_primary_for_intent")
    elif lane == "correction_guard":
        allowed = intent in {"correction_guard", "incident_diagnosis", "semantic_lookup"}
        if allowed:
            score += 12
            reasons.append("correction_guard_matches_intent")
        else:
            reasons.append("correction_guard_kept_out_of_main_context")
    elif lane == "semantic_patch":
        allowed = intent in {"semantic_lookup", "code_current", "general_context"}
        if allowed:
            score += 15
            reasons.append("semantic_patch_matches_intent")
        else:
            reasons.append("semantic_patch_not_a_task_procedure")
    else:
        allowed = True
        reasons.append("legacy_reflection_allowed")

    return {
        "lane": lane,
        "allowed": allowed,
        "score": round(max(0.0, score), 2),
        "reasons": reasons,
    }


def blocked_memory_note(item: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "experience_type": item.get("experience_type"),
        "memory_lane": decision["lane"],
        "gate_score": decision["score"],
        "reason": "; ".join(decision["reasons"]) or "blocked by memory query firewall",
    }


def semantic_patch_note(item: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "anchor_type": item.get("anchor_type"),
        "anchor_key": item.get("anchor_key"),
        "semantic_field": item.get("semantic_field"),
        "existing_value": item.get("existing_value"),
        "proposed_value": item.get("proposed_value"),
        "patch_reason": item.get("patch_reason") or item.get("reasoning_summary"),
        "confidence": item.get("confidence"),
        "gate_score": decision["score"],
        "gate_reasons": decision["reasons"],
    }


def query_matches_anchor(query: str, item: dict[str, Any]) -> bool:
    anchor = " ".join(str(item.get(key) or "") for key in ("anchor_key", "semantic_field", "proposed_value"))
    return token_overlap_score(query, anchor) > 0


def gate_matches_by_intent(
    project: Project,
    query: str,
    matches: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    intent = infer_memory_intent(query)
    gated_matches: dict[str, list[dict[str, Any]]] = {
        key: [dict(item) for item in value]
        for key, value in matches.items()
    }
    main_reflections: list[dict[str, Any]] = []
    correction_guards: list[dict[str, Any]] = []
    semantic_patch_notes: list[dict[str, Any]] = []
    blocked_notes: list[dict[str, Any]] = []
    lane_counts: dict[str, int] = {
        "main_reflections": 0,
        "correction_guards": 0,
        "semantic_patch_notes": 0,
        "blocked_memory_notes": 0,
    }

    for item in gated_matches.get("reflections", []):
        decision = reflection_gate_decision(query, intent, item)
        item["memory_lane"] = decision["lane"]
        item["gate_score"] = decision["score"]
        item["gate_reasons"] = decision["reasons"]
        if decision["lane"] == "semantic_patch":
            if decision["allowed"] or query_matches_anchor(query, item):
                semantic_patch_notes.append(semantic_patch_note(item, decision))
                lane_counts["semantic_patch_notes"] += 1
            else:
                blocked_notes.append(blocked_memory_note(item, decision))
                lane_counts["blocked_memory_notes"] += 1
            continue
        if decision["lane"] == "correction_guard":
            if decision["allowed"] and decision["score"] >= 20:
                correction_guards.append(item)
                lane_counts["correction_guards"] += 1
            else:
                blocked_notes.append(blocked_memory_note(item, decision))
                lane_counts["blocked_memory_notes"] += 1
            continue
        if decision["allowed"] and decision["score"] >= 15:
            main_reflections.append(item)
            lane_counts["main_reflections"] += 1
        else:
            blocked_notes.append(blocked_memory_note(item, decision))
            lane_counts["blocked_memory_notes"] += 1

    main_reflections.sort(key=lambda item: (item.get("gate_score", 0), item.get("score", 0), item.get("id", 0)), reverse=True)
    correction_guards.sort(key=lambda item: (item.get("gate_score", 0), item.get("score", 0), item.get("id", 0)), reverse=True)
    semantic_patch_notes.sort(key=lambda item: (item.get("gate_score", 0), item.get("id", 0)), reverse=True)
    gated_matches["reflections"] = main_reflections
    conflict_notes = matching_conflict_notes(project, query, REFLECTION_LANE_LIMITS["conflict_notes"])
    return {
        "matches": gated_matches,
        "memory_intent": intent,
        "retrieval_lanes": {
            "counts": lane_counts,
            "policy": {
                "procedure_experience": "main context only when the query intent can reuse a procedure",
                "correction_experience": "guardrail lane; not injected as the main task direction by default",
                "semantic_patch_experience": "semantic patch lane; used to explain or repair code business semantics",
            },
        },
        "memory_brief": {
            "intent": intent,
            "main_reflection_count": len(main_reflections),
            "correction_guard_count": len(correction_guards),
            "semantic_patch_count": len(semantic_patch_notes),
            "blocked_count": len(blocked_notes),
            "conflict_count": len(conflict_notes),
        },
        "correction_guards": correction_guards[: REFLECTION_LANE_LIMITS["correction_guards"]],
        "semantic_patch_notes": semantic_patch_notes[: REFLECTION_LANE_LIMITS["semantic_patch_notes"]],
        "blocked_memory_notes": blocked_notes[: REFLECTION_LANE_LIMITS["blocked_memory_notes"]],
        "conflict_notes": conflict_notes,
    }


def matching_conflict_notes(project: Project, query: str, limit: int) -> list[dict[str, Any]]:
    tokens = {token for token in query_tokens(query) if len(token) > 1}
    if not tokens:
        return []
    notes: list[dict[str, Any]] = []
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT id, entity_type, target, field, existing, incoming, decision_note, replacement_source, observed_at
            FROM semantic_conflicts
            WHERE project_id = ? AND status = 'open'
            ORDER BY observed_at DESC, id DESC
            LIMIT 50
            """,
            (project.project_id,),
        ).fetchall()
    for row in rows:
        item = row_dict(row)
        text = " ".join(str(item.get(key) or "") for key in ("entity_type", "target", "field", "existing", "incoming", "decision_note"))
        if {token for token in query_tokens(text) if len(token) > 1} & tokens:
            notes.append(item)
            if len(notes) >= limit:
                break
    return notes


def limited_matches(
    matches: dict[str, list[dict[str, Any]]],
    limits: dict[str, int],
) -> dict[str, list[dict[str, Any]]]:
    return {
        key: value[: limits.get(key, len(value))]
        for key, value in matches.items()
    }


def collect_related_edges(project: Project, targets: dict[str, set[int]]) -> list[dict[str, Any]]:
    edge_map: dict[int, dict[str, Any]] = {}

    def chunked(values: list[int], size: int) -> list[list[int]]:
        return [values[index : index + size] for index in range(0, len(values), size)]

    with connect(project) as conn:
        for entity_type, ids in targets.items():
            ordered_ids = sorted(ids)
            if not ordered_ids:
                continue
            for id_batch in chunked(ordered_ids, BATCHED_EDGE_TARGET_SIZE):
                placeholders = ",".join("?" for _ in id_batch)
                params: list[Any] = [
                    project.project_id,
                    *sorted(QUERY_ALLOWED_EDGE_RELATIONS),
                    entity_type,
                    *id_batch,
                ]
                source_rows = conn.execute(
                    f"""
                    SELECT *
                    FROM memory_edges
                    WHERE project_id = ?
                      AND relation IN ({','.join('?' for _ in sorted(QUERY_ALLOWED_EDGE_RELATIONS))})
                      AND source_type = ?
                      AND source_id IN ({placeholders})
                    ORDER BY confidence DESC, id DESC
                    LIMIT ?
                    """,
                    [*params, NETWORK_EDGE_LIMIT],
                ).fetchall()
                target_rows = conn.execute(
                    f"""
                    SELECT *
                    FROM memory_edges
                    WHERE project_id = ?
                      AND relation IN ({','.join('?' for _ in sorted(QUERY_ALLOWED_EDGE_RELATIONS))})
                      AND target_type = ?
                      AND target_id IN ({placeholders})
                    ORDER BY confidence DESC, id DESC
                    LIMIT ?
                    """,
                    [*params, NETWORK_EDGE_LIMIT],
                ).fetchall()
                for row in [*source_rows, *target_rows]:
                    edge_map[row["id"]] = row_dict(row)
    edges = list(edge_map.values())
    edges.sort(key=lambda item: (item.get("confidence", 0), item.get("id", 0)), reverse=True)
    return edges[:NETWORK_EDGE_LIMIT]


def network_limits() -> dict[str, Any]:
    return {
        "max_depth": NETWORK_MAX_DEPTH,
        "edge_limit": NETWORK_EDGE_LIMIT,
        "evidence_chain_limit": EVIDENCE_CHAIN_LIMIT,
        "allowed_relations": sorted(QUERY_ALLOWED_EDGE_RELATIONS),
    }


def evidence_reason(edge: dict[str, Any]) -> str:
    if (
        edge.get("source_type") == "code_symbol"
        and edge.get("relation") == "emits_log"
        and edge.get("target_type") == "code_log_statement"
    ):
        return "matched log statement emitted by symbol"
    if edge.get("relation") == "contains":
        return "matched node contained by learned code file"
    if edge.get("relation") == "imports":
        return "matched file connected by ArkTS import"
    if edge.get("relation") == "routes_to":
        return "matched file connected by ArkTS router target"
    if edge.get("relation") == "uses_resource":
        return "matched ArkTS resource used by learned file"
    return "matched node connected by allowed one-hop edge"


def build_evidence_chains(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chains: list[dict[str, Any]] = []
    for edge in edges[:EVIDENCE_CHAIN_LIMIT]:
        chains.append(
            {
                "depth": NETWORK_MAX_DEPTH,
                "reason": evidence_reason(edge),
                "source_type": edge.get("source_type"),
                "source_id": edge.get("source_id"),
                "relation": edge.get("relation"),
                "target_type": edge.get("target_type"),
                "target_id": edge.get("target_id"),
                "evidence": edge.get("evidence"),
                "confidence": edge.get("confidence"),
            }
        )
    return chains


def focus_from_query(query: str) -> str | None:
    lowered = query.lower()
    if any(trigger in lowered for trigger in ("跳转", "路由", "导航", "白屏", "空白页", "打不开")):
        return "route"
    if any(trigger in lowered for trigger in ("资源", "图片", "图标", "文案", "字符串", "显示不出来", "不显示", "找不到资源")):
        return "resource"
    if any(trigger in lowered for trigger in ("权限", "授权", "依赖", "配置", "ability", "module")):
        return "config"
    if any(trigger in lowered for trigger in ("日志", "报错", "错误", "异常", "失败", "崩溃", "打印", "定位")):
        return "log"
    return None


def infer_followup_focus(query: str, data: dict[str, list[dict[str, Any]]]) -> str | None:
    focus = focus_from_query(query)
    if focus:
        return focus
    for row in data.get("wiki_matches", [])[:3]:
        symbol_type = str(row.get("symbol_type") or "")
        if symbol_type in {"route", "resource", "permission", "dependency", "ability"}:
            return "config" if symbol_type in {"permission", "dependency", "ability"} else symbol_type
    if data.get("code_log_matches"):
        return "log"
    return None


def rank_followup_seed_terms(query: str, terms: list[str], limit: int = 12, focus: str | None = None) -> list[str]:
    candidates: list[tuple[int, int, str]] = []
    order = 0
    focus = focus or focus_from_query(query)

    def add(priority: int, value: str | None) -> None:
        nonlocal order
        if not value:
            return
        stripped = str(value).strip()
        if not stripped:
            return
        candidates.append((priority, order, stripped))
        order += 1

    def classify_term_priority(term: str) -> int:
        lowered = term.lower()
        query_lowered = query.lower()
        if focus == "route":
            if lowered.startswith("pages/") and not lowered.endswith(".ets"):
                return 130
            if "router" in lowered or "route" in lowered:
                return 125
            if lowered.endswith(".ets"):
                return 78
            if "failed" in lowered or "error" in lowered or "log" in lowered:
                return 68
        if focus == "resource":
            if lowered.startswith("app.") or "$r" in lowered or "resource" in lowered or "media" in lowered or "string" in lowered:
                return 125
            if lowered.startswith("pages/"):
                return 68
        if focus == "config":
            if "权限" in query_lowered and "permission" in lowered:
                return 132
            if "依赖" in query_lowered and "dependency" in lowered:
                return 132
            if "ability" in query_lowered and "ability" in lowered:
                return 132
            if "permission" in lowered:
                return 126
            if "dependency" in lowered:
                return 124
            if "ability" in lowered:
                return 118
            if lowered.endswith(".json5"):
                return 125
            if lowered.startswith("pages/") or lowered.endswith(".ets"):
                return 68
        if focus == "log":
            if "failed" in lowered or "error" in lowered or "warn" in lowered or "log" in lowered or "hilog" in lowered:
                return 125
            if "session" in lowered or "invalid" in lowered or "401" in lowered or "permission denied" in lowered:
                return 118
            if lowered.startswith("pages/") or lowered.endswith(".ets"):
                return 68
        if lowered.startswith("pages/") or lowered.startswith("app.") or "$r" in lowered:
            return 96
        if "/" in lowered or "." in lowered:
            return 92
        if "failed" in lowered or "error" in lowered or "warn" in lowered or "log" in lowered:
            return 88
        if "route" in lowered or "router" in lowered or "resource" in lowered or "hilog" in lowered:
            return 84
        if "profile" in lowered or "load" in lowered or "user" in lowered:
            return 78
        return 70

    for term in terms:
        add(classify_term_priority(str(term)), str(term))

    seen: set[str] = set()
    ranked: list[str] = []
    for _, _, value in sorted(candidates, key=lambda item: (-item[0], item[1])):
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ranked.append(normalized)
        if len(ranked) >= limit:
            break
    return ranked


def suggested_followup_terms(query: str, data: dict[str, list[dict[str, Any]]], limit: int = 12) -> list[str]:
    focus = infer_followup_focus(query, data)
    terms: list[str] = []
    for row in data.get("code_log_matches", [])[:5]:
        if row.get("message_template"):
            terms.append(str(row["message_template"]))
        if row.get("function"):
            terms.append(str(row["function"]))
        if row.get("file_path"):
            terms.append(str(row["file_path"]))
        terms.extend(json_list(row.get("business_terms")))
        terms.extend(row.get("search_terms") or [])

    for row in data.get("wiki_matches", [])[:5]:
        if row.get("symbol"):
            terms.append(str(row["symbol"]))
        if row.get("file_path"):
            terms.append(str(row["file_path"]))
        terms.extend(json_list(row.get("business_terms")))
        terms.extend(row.get("search_terms") or [])

    for row in data.get("semantic_facts", [])[:3]:
        terms.extend(tokenize(str(row.get("fact") or "")))
    for row in data.get("reflections", [])[:2]:
        terms.extend(tokenize(" ".join(str(row.get(key) or "") for key in ("task", "problem", "lesson", "future_rule"))))
    return rank_followup_seed_terms(query, terms, limit=limit, focus=focus)


def string_literals(text: str) -> list[str]:
    return [match.group(2) for match in re.finditer(r"""(['"])(.*?)(?<!\\)\1""", str(text or ""))]


def unique_preserved(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        stripped = str(value).strip()
        normalized = stripped.lower()
        if not stripped or normalized in seen:
            continue
        seen.add(normalized)
        result.append(stripped)
    return result


def log_logger_hints(row: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    logger = str(row.get("logger") or "")
    function = str(row.get("function") or "")
    raw_statement = str(row.get("raw_statement") or "")
    if logger:
        hints.append(logger)
    if function:
        hints.append(function)
    literals = string_literals(raw_statement)
    if logger == "hilog" and len(literals) >= 2:
        hints.append(literals[0])
    elif literals:
        hints.append(literals[0])
    return unique_preserved(hints)


def build_log_search_plan(query: str, data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    focus = infer_followup_focus(query, data)
    top_logs = data.get("code_log_matches", [])[:5]
    search_terms = rank_followup_seed_terms(
        query,
        [
            *suggested_followup_terms(query, data, limit=14),
            *[str(row.get("message_template") or "") for row in top_logs],
            *[str(row.get("business_summary") or "") for row in top_logs],
            *[str(row.get("business_event") or "") for row in top_logs],
            *[str(row.get("trigger_stage") or "") for row in top_logs],
            *[term for row in top_logs for term in json_list(row.get("symptom_terms"))],
            *[term for row in top_logs for term in json_list(row.get("likely_causes"))],
            *[str(row.get("process_hint") or "") for row in top_logs],
            *[term for row in top_logs for term in json_list(row.get("neighbor_terms"))],
        ],
        limit=14,
        focus=focus or "log",
    )
    logger_hints: list[str] = []
    function_hints: list[str] = []
    file_hints: list[str] = []
    candidate_log_events: list[dict[str, Any]] = []
    for row in top_logs:
        logger_hints.extend(log_logger_hints(row))
        if row.get("function"):
            function_hints.append(str(row["function"]))
        if row.get("file_path"):
            file_hints.append(str(row["file_path"]))
        candidate_log_events.append(
            {
                "message_template": str(row.get("message_template") or ""),
                "business_summary": str(row.get("business_summary") or ""),
                "business_terms": json_list(row.get("business_terms")),
                "business_event": str(row.get("business_event") or ""),
                "trigger_stage": str(row.get("trigger_stage") or ""),
                "symptom_terms": json_list(row.get("symptom_terms")),
                "likely_causes": json_list(row.get("likely_causes")),
                "process_hint": str(row.get("process_hint") or ""),
                "neighbor_terms": json_list(row.get("neighbor_terms")),
                "file_path": str(row.get("file_path") or ""),
                "function": str(row.get("function") or ""),
                "logger": str(row.get("logger") or ""),
            }
        )
    recommended_order = [
        "search failure/error logs for the target event first",
        "search preceding start/request/info logs around the same page or function",
        "compare neighboring logs that share the same logger, page, process, or business object",
    ]
    if focus == "route":
        recommended_order = [
            "search route jump failure logs and target page names first",
            "search neighboring router start/info logs for the same page transition",
            "compare related page registration or route target anchors in code memory",
        ]
    elif focus == "resource":
        recommended_order = [
            "search resource resolve or missing-resource logs first",
            "search preceding page/build/image logs around the same component",
            "compare resource keys and related code anchors before expanding scope",
        ]
    elif focus == "config":
        recommended_order = [
            "search permission/dependency/config failure logs first",
            "search neighboring ability/module startup logs for the same process",
            "compare config anchors and related code/wiki evidence before widening the search",
        ]
    return {
        "focus": focus or "log",
        "candidate_log_events": candidate_log_events,
        "search_terms": search_terms,
        "logger_hints": unique_preserved(logger_hints),
        "function_hints": unique_preserved(function_hints),
        "file_hints": unique_preserved(file_hints),
        "process_hints": unique_preserved(
            [str(item.get("process_hint") or "") for item in candidate_log_events if str(item.get("process_hint") or "").strip()]
        ),
        "recommended_order": recommended_order,
    }


def limited_context(project: Project, query: str) -> dict[str, Any]:
    matches = collect_matches(project, query)
    gated = gate_matches_by_intent(project, query, matches)
    bounded = limited_matches(gated["matches"], CONTEXT_RESULT_LIMITS)
    followup_focus = infer_followup_focus(query, bounded)
    context = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "query": query,
        "memory_intent": gated["memory_intent"],
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
        "evidence_chains": build_evidence_chains(bounded["edge_matches"]),
        "suggested_followup_terms": suggested_followup_terms(query, bounded),
        "log_search_plan": build_log_search_plan(query, bounded),
        "network_limits": network_limits(),
    }
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
    matches = collect_matches(project, query)
    gated = gate_matches_by_intent(project, query, matches)
    payload = batched_search(gated["matches"], query=query, cursor=cursor, per_type_limit=per_type_limit, aggregate_limit=aggregate_limit)
    payload["memory_intent"] = gated["memory_intent"]
    payload["retrieval_lanes"] = gated["retrieval_lanes"]
    payload["memory_brief"] = gated["memory_brief"]
    payload["correction_guards"] = gated["correction_guards"]
    payload["semantic_patch_notes"] = gated["semantic_patch_notes"]
    payload["blocked_memory_notes"] = gated["blocked_memory_notes"]
    payload["conflict_notes"] = gated["conflict_notes"]
    return payload


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
    payload["log_search_plan"] = build_log_search_plan(query, payload)
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
