# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .models import Project, QUERY_FTS_RECALL_LIMITS
from .index_freshness import filter_fresh_candidate_rows
from .query_behavior_concepts import behavior_marker_terms
from .query_followups import FOCUS_PRIORITY_TERMS, focus_from_query
from .query_fielded_retrieval import (
    candidate_refs,
    fielded_passage_rankings,
    passage_candidate_refs,
)
from .query_method_evidence import (
    method_evidence_focus_terms,
    method_evidence_term_coverage,
    method_query_variants,
    qualifying_method_evidence_ids,
)
from .query_rank_fusion import RankFusionPort, ReciprocalRankFusion
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
METHOD_EVIDENCE_RECALL_LIMIT = 24
CANDIDATE_CHANNEL_WEIGHTS = {
    "conjunctive_fts": 1.4,
    "term_fts": 1.15,
    "structural_fts": 1.25,
    "file_identity_fts": 1.35,
    "file_semantic_fts": 1.0,
    "symbol_identity_fts": 1.45,
    "symbol_semantic_fts": 1.0,
    "broad_fts": 1.0,
    "method_body_fts": 0.8,
    "string_key_fts": 1.2,
    "semantic_mechanism_fts": 1.25,
    "passage_fts": 1.1,
    "like_fallback": 0.7,
}


@dataclass(frozen=True)
class CandidateRecallBatch:
    rows: dict[str, list[Any]]
    lanes_by_id: dict[str, dict[int, list[str]]]
    fusion_by_id: dict[str, dict[int, dict[str, Any]]]
    audit: dict[str, Any]


@dataclass(frozen=True)
class TableCandidateRecall:
    ids: list[int]
    lanes_by_id: dict[int, list[str]]
    fusion_by_id: dict[int, dict[str, Any]]
    audit: dict[str, Any]


class CandidateRecallPort(Protocol):
    def recall(self, conn: Any, project: Project, query: str) -> CandidateRecallBatch:
        ...


class SQLiteCandidateRecall:
    """Bounded lexical candidate generation behind the retrieval port."""

    def __init__(
        self,
        rank_fusion: RankFusionPort | None = None,
        enable_passage_shadow: bool = False,
    ) -> None:
        self.rank_fusion = rank_fusion or ReciprocalRankFusion(
            channel_weights=CANDIDATE_CHANNEL_WEIGHTS
        )
        self.enable_passage_shadow = enable_passage_shadow

    def recall(self, conn: Any, project: Project, query: str) -> CandidateRecallBatch:
        rows: dict[str, list[Any]] = {}
        lanes_by_id: dict[str, dict[int, list[str]]] = {}
        fusion_by_id: dict[str, dict[int, dict[str, Any]]] = {}
        selected_ids: dict[str, list[int]] = {}
        table_audits: dict[str, dict[str, Any]] = {}
        for table_name, limit in QUERY_FTS_RECALL_LIMITS.items():
            recalled = recall_table_candidates(
                conn, project, table_name, query, limit, self.rank_fusion,
                self.enable_passage_shadow,
            )
            rows[table_name] = fetch_rows_by_ids(
                conn,
                table_name,
                project,
                recalled.ids,
                ACTIVE_FILTERS.get(table_name, ""),
            )
            selected_ids[table_name] = recalled.ids
            lanes_by_id[table_name] = recalled.lanes_by_id
            fusion_by_id[table_name] = recalled.fusion_by_id
            table_audits[table_name] = recalled.audit
        for table_name, table_rows in rows.items():
            table_audits[table_name]["candidate_refs"] = candidate_refs(
                table_rows, selected_ids[table_name], lanes_by_id[table_name]
            )
        rows, source_freshness = filter_fresh_candidate_rows(
            conn, project, rows
        )
        return CandidateRecallBatch(
            rows=rows,
            lanes_by_id=lanes_by_id,
            fusion_by_id=fusion_by_id,
            audit={
                "schema_version": "agent-candidate-recall-audit/v1",
                "source_freshness": source_freshness,
                "provider": "sqlite_fts5_passage_rrf/v4",
                "rank_fusion_provider": "reciprocal_rank_fusion/v1",
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
    result = recall_table_candidates(
        conn,
        project,
        table_name,
        query,
        limit,
        ReciprocalRankFusion(channel_weights=CANDIDATE_CHANNEL_WEIGHTS),
    )
    return result.ids, result.lanes_by_id, result.audit


def recall_table_candidates(
    conn: Any,
    project: Project,
    table_name: str,
    query: str,
    limit: int,
    rank_fusion: RankFusionPort,
    enable_passage_shadow: bool = False,
) -> TableCandidateRecall:
    lane_ids: dict[str, list[int]] = {}
    fielded_audit: dict[str, Any] = {}
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
    source_type = {
        "code_files": "code_file", "code_symbols": "code_symbol",
    }.get(table_name)
    if source_type and enable_passage_shadow:
        fielded = fielded_passage_rankings(
            conn, project, query, limit, source_type
        )
        if source_type == "code_symbol":
            method_terms = method_evidence_focus_terms(query)
            method_ids = fielded.rankings.get("method_body_fts", [])
            fielded.rankings["method_body_fts"] = (
                qualifying_method_evidence_ids(
                    conn, project, method_ids, method_terms
                )
                if len(method_terms) >= 2 else []
            )
        fielded_fusion = rank_fusion.fuse(fielded.rankings, limit)
        fielded_ids = [item.record_id for item in fielded_fusion.candidates]
        fielded_audit = {
            **fielded.audit,
            "mode": "shadow",
            "serving_candidates_changed": False,
            "rank_fusion": fielded_fusion.audit(),
            "candidate_fusion": {
                str(item.record_id): item.audit()
                for item in fielded_fusion.candidates
            },
            "candidate_refs": passage_candidate_refs(
                conn, project, source_type, fielded_ids, fielded.rankings
            ),
        }
    elif source_type:
        fielded_audit = {
            "provider": "code_passage_fts/v2", "mode": "disabled"
        }
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
    method_terms = method_evidence_focus_terms(query)
    if table_name == "code_symbols" and len(method_terms) >= 2:
        method_ids = fts_table_ids(
            conn, project, "code_method_fts",
            fts_expression(method_terms, " OR "),
            METHOD_EVIDENCE_RECALL_LIMIT,
        )
        lane_ids["method_body_fts"] = qualifying_method_evidence_ids(
            conn, project, method_ids, method_terms
        )
    fused = rank_fusion.fuse(lane_ids, limit)
    ordered = [item.record_id for item in fused.candidates]
    used_fallback = False
    fallback_skipped = False
    if not ordered and broad_expression and like_fallback_allowed(conn, table_name):
        fallback = like_recall_candidate_ids(conn, project, table_name, query, limit)
        lane_ids["like_fallback"] = fallback
        fused = rank_fusion.fuse(lane_ids, limit)
        ordered = [item.record_id for item in fused.candidates]
        used_fallback = bool(fallback)
    elif not ordered and broad_expression:
        fallback_skipped = True
    lane_map = lanes_for_selected_ids(lane_ids, ordered)
    fusion_map = {
        item.record_id: item.audit()
        for item in fused.candidates
    }
    return TableCandidateRecall(ordered, lane_map, fusion_map, {
        "requested_limit": limit,
        "candidate_count": len(ordered),
        "saturated": len(ordered) >= limit,
        "broad_saturated": broad_saturated,
        "used_fallback": used_fallback,
        "fallback_skipped_for_scale": fallback_skipped,
        "focus_term_count": len(focus_terms),
        "structural_term_count": len(structural_terms),
        "lane_counts": {key: len(value) for key, value in lane_ids.items()},
        "fielded_retrieval": fielded_audit,
        "rank_fusion": fused.audit(),
    })


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
    return fts_table_ids(conn, project, FTS_TABLES[table_name], expression, limit)


def fts_table_ids(
    conn: Any,
    project: Project,
    fts_table: str,
    expression: str | None,
    limit: int,
) -> list[int]:
    if not expression:
        return []
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
    fused = ReciprocalRankFusion(
        channel_weights=CANDIDATE_CHANNEL_WEIGHTS
    ).fuse(lanes, limit)
    return [item.record_id for item in fused.candidates]


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
