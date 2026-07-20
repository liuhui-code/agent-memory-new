# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .models import Project, QUERY_FTS_RECALL_LIMITS
from .index_freshness import filter_fresh_candidate_rows
from .query_behavior_concepts import behavior_marker_terms
from .query_followups import FOCUS_PRIORITY_TERMS, focus_from_query
from .text import (
    ENGLISH_QUERY_STOPWORDS,
    bounded_query_tokens,
    query_tokens,
    tokenize,
    unique_list,
)


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
        "task", "summary", "lesson", "future_rule", "problem",
        "reasoning_summary", "useful_followup_terms", "inspection_targets",
        "verification_method", "source_cases", "skill_candidate", "evidence",
        "anchor_type", "anchor_key", "semantic_field", "existing_value",
        "proposed_value", "patch_reason",
    ),
    "episodes": ("task", "summary", "outcome", "files_touched", "commands_run"),
    "code_files": ("file_path", "summary", "business_summary", "business_terms"),
    "code_symbols": (
        "file_path", "symbol", "symbol_type", "summary",
        "business_summary", "business_terms",
    ),
    "code_log_statements": (
        "file_path", "function", "logger", "message_template", "raw_statement",
        "business_summary", "business_terms", "business_event", "trigger_stage",
        "symptom_terms", "likely_causes", "process_hint", "neighbor_terms",
    ),
}

ACTIVE_FILTERS = {
    "semantic_facts": "AND COALESCE(is_stale, 0) = 0 AND COALESCE(status, 'active') = 'active'",
    "reflections": "AND COALESCE(is_stale, 0) = 0 AND COALESCE(status, 'active') = 'active'",
    "episodes": "AND COALESCE(status, 'active') = 'active'",
}

TERM_COVERAGE_TABLES = {"code_files", "code_symbols", "code_log_statements"}
STRUCTURAL_RECALL_TABLES = {"code_files"}
GENERIC_RECALL_TERMS = {
    "application", "behavior", "both", "bright", "code", "content", "current",
    "class", "classes", "dark", "find", "function", "functions", "issue",
    "locate", "method", "methods", "mode", "owner", "owners", "problem",
    "project", "remain", "source", "symbol", "symbols", "system", "user",
}
MAX_TERM_LANES = 4
MAX_CODE_LIKE_FALLBACK_ROWS = 50_000


@dataclass(frozen=True)
class CandidateRecallBatch:
    rows: dict[str, list[Any]]
    lanes_by_id: dict[str, dict[int, list[str]]]
    audit: dict[str, Any]


class CandidateRecallPort(Protocol):
    def recall(self, conn: Any, project: Project, query: str) -> CandidateRecallBatch:
        ...


class SQLiteCandidateRecall:
    """Bounded lexical candidate generation behind the retrieval port."""

    def recall(self, conn: Any, project: Project, query: str) -> CandidateRecallBatch:
        rows: dict[str, list[Any]] = {}
        lanes_by_id: dict[str, dict[int, list[str]]] = {}
        table_audits: dict[str, dict[str, Any]] = {}
        for table_name, limit in QUERY_FTS_RECALL_LIMITS.items():
            ids, lane_map, audit = recall_candidate_ids_with_lanes(
                conn, project, table_name, query, limit
            )
            rows[table_name] = fetch_rows_by_ids(
                conn, table_name, project, ids, ACTIVE_FILTERS.get(table_name, "")
            )
            lanes_by_id[table_name] = lane_map
            table_audits[table_name] = audit
        rows, source_freshness = filter_fresh_candidate_rows(
            conn, project, rows
        )
        return CandidateRecallBatch(
            rows=rows,
            lanes_by_id=lanes_by_id,
            audit={
                "schema_version": "agent-candidate-recall-audit/v1",
                "source_freshness": source_freshness,
                "provider": "sqlite_fts5_fielded/v2",
                "tables": table_audits,
            },
        )


def fts_match_expression(query: str) -> str | None:
    tokens = unique_list([
        token for token in bounded_query_tokens(query, 12)
        if len(token) > 1 and token.casefold() not in GENERIC_RECALL_TERMS
    ])
    return fts_expression(tokens, " OR ")


def fts_expression(tokens: list[str], operator: str) -> str | None:
    if not tokens:
        return None
    quoted = ['"' + token.replace('"', '""') + '"*' for token in tokens]
    return operator.join(quoted)


def recall_focus_terms(query: str) -> list[str]:
    terms = []
    for token in tokenize(query):
        normalized = token.casefold()
        if normalized in ENGLISH_QUERY_STOPWORDS or normalized in GENERIC_RECALL_TERMS:
            continue
        if normalized.isascii() and len(normalized) < 4:
            continue
        if normalized not in terms:
            terms.append(normalized)
    if len(terms) <= MAX_TERM_LANES:
        return terms
    return [*terms[:2], *terms[-2:]]


def recall_candidate_ids(
    conn: Any,
    project: Project,
    table_name: str,
    query: str,
    limit: int,
) -> list[int]:
    ids, _lanes, _audit = recall_candidate_ids_with_lanes(
        conn, project, table_name, query, limit
    )
    return ids


def recall_candidate_ids_with_lanes(
    conn: Any,
    project: Project,
    table_name: str,
    query: str,
    limit: int,
) -> tuple[list[int], dict[int, list[str]], dict[str, Any]]:
    lane_ids: dict[str, list[int]] = {}
    focus_terms = recall_focus_terms(query)
    structural_terms = (
        behavior_marker_terms(query)
        if table_name in STRUCTURAL_RECALL_TABLES else []
    )
    fielded_recall = table_name in TERM_COVERAGE_TABLES and bool(focus_terms)
    broad_limit = max(1, int(limit * 0.7)) if fielded_recall else limit
    broad_expression = fts_match_expression(query)
    lane_ids["broad_fts"] = fts_ids(
        conn,
        project,
        table_name,
        broad_expression,
        broad_limit,
    )
    broad_saturated = len(lane_ids["broad_fts"]) >= broad_limit
    if structural_terms:
        lane_ids["structural_fts"] = fts_ids(
            conn,
            project,
            table_name,
            fts_expression(structural_terms, " OR "),
            max(8, limit // 4),
        )
    if fielded_recall and broad_saturated and len(focus_terms) >= 2:
        lane_ids["conjunctive_fts"] = fts_ids(
            conn,
            project,
            table_name,
            fts_expression(focus_terms[:3], " AND "),
            max(8, limit // 5),
        )
    if fielded_recall and broad_saturated:
        per_term_limit = max(8, limit // 8)
        for index, term in enumerate(focus_terms):
            lane_ids[f"term_fts:{index + 1}"] = fts_ids(
                conn,
                project,
                table_name,
                fts_expression([term], " OR "),
                per_term_limit,
            )
    ordered = merge_lane_ids(lane_ids, limit)
    used_fallback = False
    fallback_skipped = False
    if not ordered and broad_expression and like_fallback_allowed(conn, table_name):
        fallback = like_recall_candidate_ids(conn, project, table_name, query, limit)
        lane_ids["like_fallback"] = fallback
        ordered = fallback
        used_fallback = bool(fallback)
    elif not ordered and broad_expression:
        fallback_skipped = True
    lane_map = lanes_for_selected_ids(lane_ids, ordered)
    return ordered, lane_map, {
        "requested_limit": limit,
        "candidate_count": len(ordered),
        "saturated": len(ordered) >= limit,
        "broad_saturated": broad_saturated,
        "used_fallback": used_fallback,
        "fallback_skipped_for_scale": fallback_skipped,
        "focus_term_count": len(focus_terms),
        "structural_term_count": len(structural_terms),
        "lane_counts": {key: len(value) for key, value in lane_ids.items()},
    }


def like_fallback_allowed(conn: Any, table_name: str) -> bool:
    if table_name not in TERM_COVERAGE_TABLES:
        return True
    row = conn.execute(f"SELECT MAX(id) AS high_watermark FROM {table_name}").fetchone()
    high_watermark = int(row["high_watermark"] or 0) if row else 0
    return high_watermark <= MAX_CODE_LIKE_FALLBACK_ROWS


def fts_ids(
    conn: Any,
    project: Project,
    table_name: str,
    expression: str | None,
    limit: int,
) -> list[int]:
    if not expression:
        return []
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
        (expression, project.project_id, limit),
    ).fetchall()
    return [int(row["rowid"]) for row in rows]


def merge_lane_ids(lanes: dict[str, list[int]], limit: int) -> list[int]:
    priority = [
        "conjunctive_fts",
        *[f"term_fts:{index + 1}" for index in range(MAX_TERM_LANES)],
        "structural_fts",
        "broad_fts",
    ]
    result: list[int] = []
    seen: set[int] = set()
    for lane in priority:
        for record_id in lanes.get(lane, []):
            if record_id in seen:
                continue
            seen.add(record_id)
            result.append(record_id)
            if len(result) >= limit:
                return result
    return result


def lanes_for_selected_ids(
    lanes: dict[str, list[int]],
    selected: list[int],
) -> dict[int, list[str]]:
    selected_set = set(selected)
    result: dict[int, list[str]] = {record_id: [] for record_id in selected}
    for lane, ids in lanes.items():
        for record_id in ids:
            if record_id in selected_set:
                result[record_id].append(lane)
    return result


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
    focus_terms = [
        term for term in FOCUS_PRIORITY_TERMS.get(focus or "", [])
        if term in expanded_tokens
    ]
    other_expanded = [term for term in expanded_tokens if term not in focus_terms]
    terms = unique_list([
        *original_tokens[:1], *focus_terms, *original_tokens[1:],
        *other_expanded, query.strip(),
    ])
    terms = [term for term in terms if len(term.strip()) > 1][:12]
    if not terms:
        return []
    term_clauses: list[str] = []
    params: list[Any] = [project.project_id]
    for term in terms:
        columns_sql = [f"COALESCE({column}, '') LIKE ?" for column in columns]
        term_clauses.append("(" + " OR ".join(columns_sql) + ")")
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
