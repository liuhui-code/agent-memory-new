# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .experience_maturity import score_experience_maturity
from .experience_usage import apply_usage_adjustment, collect_usage_adjustments_by_type
from .feedback_policy import candidate_ids
from .incident_trace_models import INCIDENT_TRACE_SEARCH_LIMIT
from .incident_trace_query import collect_incident_trace_matches
from .log_signal_quality import score_log_signal
from .models import Project, QUERY_FTS_RECALL_LIMITS
from .quality_scoring import score_reflection_quality, score_semantic_quality
from .query_edges import collect_related_edges
from .query_followups import FOCUS_PRIORITY_TERMS, focus_from_query
from .records import memory_warning, row_dict
from .retrieval_feedback import collect_feedback_adjustments
from .storage import connect
from .text import code_search_terms, json_list, query_tokens, score_weighted_fields, tokenize, unique_list

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



def apply_feedback_penalty(item: dict[str, Any], penalties: dict[int, dict[str, Any]]) -> None:
    feedback = penalties.get(int(item.get("id") or 0))
    if not feedback:
        item["feedback_penalty"] = 0.0
        return
    item["feedback_penalty"] = feedback["penalty"]
    item["feedback_reasons"] = unique_list([str(reason) for reason in feedback.get("reasons", [])])
    item["feedback_ids"] = feedback.get("feedback_ids", [])



def apply_calibration_feedback(item: dict[str, Any], feedback_rows: dict[int, dict[str, Any]]) -> None:
    feedback = feedback_rows.get(int(item.get("id") or 0))
    if not feedback:
        item["calibration_feedback_bonus"] = 0.0
        item["calibration_feedback_penalty"] = 0.0
        return
    item["calibration_feedback_bonus"] = feedback.get("bonus", 0.0)
    item["calibration_feedback_penalty"] = feedback.get("penalty", 0.0)
    item["calibration_feedback_reasons"] = unique_list([str(reason) for reason in feedback.get("reasons", [])])
    item["calibration_feedback_ids"] = feedback.get("feedback_ids", [])



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
    memory_candidate_ids = {
        "semantic": candidate_ids(semantic),
        "reflection": candidate_ids(reflections),
    }
    feedback, calibration = collect_feedback_adjustments(
        project, query, record_ids=memory_candidate_ids
    )
    usage = collect_usage_adjustments_by_type(
        project, query, record_ids=memory_candidate_ids
    )
    semantic_feedback = feedback["semantic"]
    reflection_feedback = feedback["reflection"]
    semantic_usage = usage["semantic"]
    reflection_usage = usage["reflection"]
    semantic_calibration_feedback = calibration["semantic"]
    reflection_calibration_feedback = calibration["reflection"]

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
            quality = score_semantic_quality(item)
            item["score"] = score + float(row["confidence"] or 0)
            item["quality_score"] = quality["quality_score"]
            item["quality_band"] = quality["quality_band"]
            item["quality_reasons"] = quality["reasons"]
            apply_feedback_penalty(item, semantic_feedback)
            apply_usage_adjustment(item, semantic_usage)
            apply_calibration_feedback(item, semantic_calibration_feedback)
            item["rerank_score"] = round(
                item["score"]
                + item["quality_score"] * 3.0
                + float(item.get("usage_feedback_bonus") or 0.0) * 30.0
                - float(item.get("usage_feedback_penalty") or 0.0) * 40.0
                - item.get("feedback_penalty", 0.0),
                3,
            )
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
            quality = score_reflection_quality(item)
            item["score"] = score
            item["quality_score"] = quality["quality_score"]
            item["quality_band"] = quality["quality_band"]
            item["quality_reasons"] = quality["reasons"]
            item["experience_evidence_profile"] = quality.get("experience_evidence_profile")
            apply_feedback_penalty(item, reflection_feedback)
            apply_usage_adjustment(item, reflection_usage)
            apply_calibration_feedback(item, reflection_calibration_feedback)
            item.update(score_experience_maturity(item))
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
            item.update(score_log_signal(item))
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
        results[key].sort(key=lambda item: (item.get("rerank_score", item.get("score", 0)), item.get("created_at", "")), reverse=True)
    return results
