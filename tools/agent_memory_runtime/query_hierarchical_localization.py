# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol

from .models import Project
from .query_behavior_concepts import behavior_marker_terms
from .query_definition_identity import explicit_owner_identity_match
from .query_artifact_roles import (
    annotate_artifact_roles,
    artifact_role_rank_score,
    artifact_role_shadow_priority,
    artifact_role_tiebreak,
)
from .query_hierarchical_owners import load_one_hop_owners
from .query_language import positive_retrieval_query
from .query_localization_file_candidates import select_file_candidates
from .semantic_callable_profile import matching_owner_kind, matching_target_owner_kind
from .records import row_dict
from .storage import connect
from .text import json_list, query_tokens, score_weighted_fields, unique_list


CALLABLE_TYPES = ("function", "method")
MAX_FILES = 8
MAX_FILE_CALLABLE_POOL = 128
MAX_DIRECT_CALLABLE_POOL = 32
MAX_GRAPH_SEEDS = 6
MAX_GRAPH_OWNERS = 16
MAX_CALLABLES = 12
MAX_CALLABLES_PER_FILE = 2
MAX_SOURCE_RANGES = 8
EXPRESSION_RADIUS = 2
FILE_RANK_PRIOR_MAX = 12.0
FILE_RANK_PRIOR_K = 10.0
LOCALIZATION_SCHEMA_VERSION = "agent-hierarchical-localization/v2"
LOCALIZATION_PROVIDER = "sqlite_hierarchical_localizer/v2"
class HierarchicalLocalizerPort(Protocol):
    def localize(
        self,
        project: Project,
        query: str,
        matches: dict[str, list[dict[str, Any]]],
        direct_scores_safe: bool = False,
    ) -> dict[str, Any]:
        ...

@dataclass(frozen=True)
class SQLiteHierarchicalLocalizer:
    """Bounded serving locator: fused files -> callables -> evidence ranges."""

    def localize(
        self,
        project: Project,
        query: str,
        matches: dict[str, list[dict[str, Any]]],
        direct_scores_safe: bool = False,
    ) -> dict[str, Any]:
        files = select_file_candidates(
            matches.get("wiki_matches") or [],
            MAX_FILES,
            query,
        )
        if not files:
            return empty_localization()
        direct_symbols = direct_symbol_candidates(matches.get("wiki_matches") or [], files)
        rows = load_file_callables(
            project,
            [item["file_path"] for item in files],
            list(direct_symbols)[:MAX_DIRECT_CALLABLE_POOL],
        )
        candidates = attach_candidate_metadata(rows, files, direct_symbols)
        ranking_query = positive_retrieval_query(query)
        use_direct_score = direct_scores_safe or ranking_query == " ".join(query.split())
        initial = rank_callables(candidates, ranking_query, use_direct_score)
        graph_seeds = select_graph_seeds(initial, MAX_GRAPH_SEEDS)
        owners = load_one_hop_owners(
            project, [item["id"] for item in graph_seeds], MAX_GRAPH_OWNERS,
        )
        ranked = rank_callables([*candidates, *owners], ranking_query, use_direct_score)
        selected = select_diverse_callables(ranked, MAX_CALLABLES)
        ranges = valid_source_ranges(selected, ranking_query)
        return {
            **localization_contract(),
            "limits": localization_limits(),
            "stage_counts": {
                "file_candidates": len(files),
                "file_callable_pool": len(candidates),
                "graph_seed_count": len(graph_seeds),
                "graph_owner_pool": len(owners),
                "selected_callables": len(selected),
                "selected_ranges": len(ranges),
            },
            "file_candidates": files,
            "graph_seeds": [compact_callable(item) for item in graph_seeds],
            "graph_owner_candidates": [compact_callable(item) for item in owners],
            "callable_candidates": [compact_callable(item) for item in selected],
            "source_ranges": ranges,
        }


def empty_localization() -> dict[str, Any]:
    return {
        **localization_contract(),
        "limits": localization_limits(),
        "stage_counts": {
            "file_candidates": 0,
            "file_callable_pool": 0,
            "graph_seed_count": 0,
            "graph_owner_pool": 0,
            "selected_callables": 0,
            "selected_ranges": 0,
        },
        "file_candidates": [],
        "graph_seeds": [],
        "graph_owner_candidates": [],
        "callable_candidates": [],
        "source_ranges": [],
    }


def localization_contract() -> dict[str, Any]:
    return {
        "schema_version": LOCALIZATION_SCHEMA_VERSION,
        "provider": LOCALIZATION_PROVIDER,
        "mode": "serving",
        "projection_contract": {
            "candidate_recall_changed": False,
            "affects_serving_projection": True,
            "consumer": "query_handoff.callable_evidence",
        },
    }


def localization_limits() -> dict[str, int]:
    return {
        "files": MAX_FILES,
        "file_callable_pool": MAX_FILE_CALLABLE_POOL,
        "direct_callable_pool": MAX_DIRECT_CALLABLE_POOL,
        "graph_seeds": MAX_GRAPH_SEEDS,
        "graph_owners": MAX_GRAPH_OWNERS,
        "callables": MAX_CALLABLES,
        "source_ranges": MAX_SOURCE_RANGES,
    }


def direct_symbol_candidates(
    items: list[dict[str, Any]],
    files: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    allowed_paths = {str(item["file_path"]) for item in files}
    result: dict[int, dict[str, Any]] = {}
    for item in items:
        if item.get("kind") != "symbol" or item.get("graph_depth"):
            continue
        record_id = int(item.get("id") or 0)
        if record_id <= 0 or str(item.get("file_path") or "") not in allowed_paths:
            continue
        result[record_id] = item
    return result


def load_file_callables(
    project: Project,
    file_paths: list[str],
    preferred_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    if not file_paths:
        return []
    preferred = [int(value) for value in (preferred_ids or []) if int(value) > 0]
    placeholders = ",".join("?" for _ in file_paths)
    type_placeholders = ",".join("?" for _ in CALLABLE_TYPES)
    preferred_placeholders = ",".join("?" for _ in preferred)
    preference = (
        f"CASE WHEN id IN ({preferred_placeholders}) THEN 0 ELSE 1 END"
        if preferred else "1"
    )
    per_file_limit = max(1, (MAX_FILE_CALLABLE_POOL + len(file_paths) - 1) // len(file_paths))
    with connect(project) as conn:
        rows = conn.execute(
            f"""
            WITH ordered AS (
              SELECT code_symbols.*,
                     ROW_NUMBER() OVER (
                       PARTITION BY file_path
                       ORDER BY start_line, id
                     ) AS source_rank,
                     COUNT(*) OVER (PARTITION BY file_path) AS source_count,
                     {preference} AS preferred_rank
              FROM code_symbols
              WHERE project_id = ? AND file_path IN ({placeholders})
                AND symbol_type IN ({type_placeholders})
            ), stratified AS (
              SELECT ordered.*,
                     ROW_NUMBER() OVER (
                       PARTITION BY file_path,
                         MIN(? - 1, CAST((source_rank - 1) * ? / source_count AS INTEGER))
                       ORDER BY preferred_rank, source_rank, id
                     ) AS stratum_rank
              FROM ordered
            ), bounded AS (
              SELECT stratified.*,
                     ROW_NUMBER() OVER (
                       PARTITION BY file_path
                       ORDER BY preferred_rank, stratum_rank, source_rank, id
                     ) AS file_pool_rank
              FROM stratified
              WHERE preferred_rank = 0 OR stratum_rank = 1
            )
            SELECT * FROM bounded
            WHERE file_pool_rank <= ?
            ORDER BY file_pool_rank, file_path, start_line, id
            LIMIT ?
            """,
            (
                *preferred,
                project.project_id,
                *file_paths,
                *CALLABLE_TYPES,
                per_file_limit,
                per_file_limit,
                per_file_limit,
                MAX_FILE_CALLABLE_POOL,
            ),
        ).fetchall()
    return [row_dict(row) for row in rows]


def attach_candidate_metadata(
    rows: list[dict[str, Any]],
    files: list[dict[str, Any]],
    direct_symbols: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    file_ranks = {str(item["file_path"]): index for index, item in enumerate(files, start=1)}
    file_evidence = {str(item["file_path"]): item for item in files}
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        direct = direct_symbols.get(int(item["id"]))
        item["file_rank"] = file_ranks.get(str(item.get("file_path") or ""), MAX_FILES + 1)
        file_item = file_evidence.get(str(item.get("file_path") or ""), {})
        item["file_structural_coverage"] = int(file_item.get("structural_coverage") or 0)
        item["direct_score"] = float(direct.get("score") or 0.0) if direct else 0.0
        item["direct_match_reasons"] = list(direct.get("match_reasons") or []) if direct else []
        item["direct_recall_lanes"] = list(direct.get("recall_lanes") or []) if direct else []
        item["graph_depth"] = 0
        result.append(item)
    return result


def select_graph_seeds(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_ids: set[int] = set()
    evidence_first = [
        item for item in items
        if float(item.get("direct_score") or 0.0) > 0 or item.get("mechanism_hits")
        or "exact_symbol" in (item.get("localization_reasons") or [])
    ]
    evidence_first.sort(key=graph_seed_priority)
    for item in [*evidence_first, *items]:
        record_id = int(item.get("id") or 0)
        if record_id <= 0 or record_id in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(record_id)
        if len(selected) >= limit:
            break
    return selected


def graph_seed_priority(item: dict[str, Any]) -> tuple[float, int, int, float, int]:
    reasons = set(item.get("localization_reasons") or [])
    return (
        -float(item.get("direct_score") or 0.0),
        -int("exact_symbol" in reasons),
        -len(item.get("mechanism_hits") or []),
        -float(item.get("localization_score") or 0.0),
        int(item.get("id") or 0),
    )


def rank_callables(
    items: list[dict[str, Any]],
    query: str,
    use_direct_score: bool = True,
) -> list[dict[str, Any]]:
    terms = query_tokens(query)
    expanded_terms = set(terms)
    scored: list[dict[str, Any]] = []
    for item in dedupe_callables(items):
        lexical, reasons = score_weighted_fields(
            query,
            terms,
            expanded_terms,
            [
                ("symbol", str(item.get("symbol") or ""), 4.0),
                ("business_terms", " ".join(json_list(item.get("business_terms"))), 4.0),
                ("business_summary", str(item.get("business_summary") or ""), 3.0),
                ("summary", str(item.get("summary") or ""), 1.5),
                ("method_evidence", str(item.get("method_evidence") or ""), 2.0),
                ("string_evidence", str(item.get("string_evidence") or ""), 2.5),
            ],
            [("exact_symbol", str(item.get("symbol") or ""), 12.0)],
        )
        mechanism_hits = matching_mechanisms(item.get("mechanism_evidence"), query)
        direct_score = float(item.get("direct_score") or 0.0) if use_direct_score else 0.0
        score = lexical + min(9.0, direct_score * 0.18)
        file_rank = int(item.get("file_rank") or 0)
        rank_prior = (
            linear_file_rank_prior(file_rank)
            if use_direct_score
            else file_rank_prior(file_rank)
        )
        item["first_stage_rank_prior"] = rank_prior
        score += rank_prior
        if rank_prior:
            reasons.append("first_stage_rank_prior")
        if mechanism_hits:
            score += min(9.0, 3.0 * len(mechanism_hits[0]["matched_terms"]))
            reasons.append("semantic_mechanism")
        owner_kind_match = matching_owner_kind(query, item.get("owner_kind"))
        owner_identity_match = explicit_owner_identity_match(query, item.get("owner_name"))
        item["owner_kind_match"] = owner_kind_match
        item["explicit_owner_identity_match"] = owner_identity_match
        item["target_owner_kind_match"] = matching_target_owner_kind(query, item.get("owner_kind"))
        if owner_kind_match:
            score += 6.0
            reasons.append("structured_owner_kind")
        if owner_identity_match:
            reasons.append("explicit_owner_identity")
        if item.get("graph_depth"):
            score += 3.0 + float(item.get("graph_confidence") or 0.0) * 3.0
            reasons.extend(f"graph_owner:{value}" for value in item.get("graph_relations") or [])
        if item.get("start_line") and item.get("end_line"):
            score += 0.5
            reasons.append("source_locatable")
        item["localization_score"] = round(score, 3)
        item["evidence_score"] = round(score - rank_prior if not use_direct_score else score, 3)
        item["localization_reasons"] = unique_list([
            *reasons,
            *(str(value) for value in item.get("direct_match_reasons") or []),
        ])
        item["mechanism_hits"] = mechanism_hits
        scored.append(item)
    role_aware = annotate_artifact_roles(scored, query)
    return sorted(
        role_aware,
        key=lambda item: (
            artifact_role_shadow_priority(item),
            -int(bool(item.get("explicit_owner_identity_match"))),
            -int(bool(item.get("target_owner_kind_match"))),
            -artifact_role_rank_score(item),
            artifact_role_tiebreak(item),
            int(item.get("graph_depth") or 0),
            str(item.get("file_path") or ""),
            int(item.get("start_line") or 0),
            int(item.get("id") or 0),
        ),
    )


def file_rank_prior(rank: int) -> float:
    if rank <= 0 or rank > MAX_FILES:
        return 0.0
    return round(FILE_RANK_PRIOR_MAX * (FILE_RANK_PRIOR_K + 1) / (FILE_RANK_PRIOR_K + rank), 3)


def linear_file_rank_prior(rank: int) -> float:
    return float(max(0, MAX_FILES + 1 - rank)) if rank > 0 else 0.0


def dedupe_callables(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chosen: dict[int, dict[str, Any]] = {}
    for item in items:
        record_id = int(item.get("id") or 0)
        if record_id <= 0:
            continue
        current = chosen.get(record_id)
        if current is None or int(item.get("graph_depth") or 0) < int(current.get("graph_depth") or 0):
            chosen[record_id] = item
    return list(chosen.values())


def select_diverse_callables(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    path_counts: dict[str, int] = {}
    for item in items:
        path = str(item.get("file_path") or "")
        if path_counts.get(path, 0) >= MAX_CALLABLES_PER_FILE:
            deferred.append(item)
            continue
        selected.append(item)
        path_counts[path] = path_counts.get(path, 0) + 1
        if len(selected) >= limit:
            return selected
    selected.extend(deferred[: max(0, limit - len(selected))])
    return selected[:limit]


def matching_mechanisms(payload: Any, query: str) -> list[dict[str, Any]]:
    try:
        records = json.loads(str(payload or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(records, list):
        return []
    expected = set(query_tokens(query)) | set(behavior_marker_terms(query))
    matches: list[dict[str, Any]] = []
    for item in records:
        if not isinstance(item, dict) or not isinstance(item.get("line"), int):
            continue
        kind = str(item.get("kind") or "")
        terms = {kind, kind.replace("_", "")}
        terms.update(str(value) for value in item.get("terms") or [] if str(value))
        matched = sorted(expected & {value.casefold() for value in terms})
        if matched:
            matches.append({
                "line": int(item["line"]),
                "kind": kind,
                "matched_terms": matched,
                "detail": str(item.get("detail") or ""),
            })
    return sorted(matches, key=lambda item: (-len(item["matched_terms"]), item["line"], item["kind"]))


def compact_callable(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol_id": item.get("id"),
        "file_path": item.get("file_path"),
        "symbol": item.get("symbol"),
        "qualified_name": item.get("qualified_name"),
        "start_line": item.get("start_line"),
        "end_line": item.get("end_line"),
        "score": item.get("localization_score"),
        "evidence_score": item.get("evidence_score"),
        "reasons": item.get("localization_reasons") or [],
        "graph_depth": item.get("graph_depth"),
        "graph_relations": item.get("graph_relations") or [],
        "recall_lanes": item.get("direct_recall_lanes") or [],
        "owner_name": item.get("owner_name"),
        "owner_kind": item.get("owner_kind"),
        **({"file_structural_coverage": item.get("file_structural_coverage")}
           if item.get("file_structural_coverage") else {}),
        **({"explicit_owner_identity_match": True} if item.get("explicit_owner_identity_match") else {}),
        "callable_roles": json_list(item.get("callable_roles")),
        "artifact_role": item.get("artifact_role"),
        "artifact_query_intent": item.get("artifact_query_intent"),
        **({"artifact_role_competition": True} if item.get("artifact_role_competition") else {}),
        **({"artifact_role_representative": True} if item.get("artifact_role_representative") else {}),
        **({"artifact_role_shadow": True} if item.get("artifact_role_shadow") else {}),
        **({"target_owner_kind_match": True} if item.get("target_owner_kind_match") else {}),
    }


def source_range(item: dict[str, Any], query: str) -> dict[str, Any]:
    start = int(item.get("start_line") or 0)
    end = int(item.get("end_line") or 0)
    base = {
        "symbol_id": item.get("id"),
        "file_path": item.get("file_path"),
        "symbol": item.get("symbol"),
        "callable_start_line": start,
        "callable_end_line": end,
    }
    hits = matching_mechanisms(item.get("mechanism_evidence"), query)
    if hits and start > 0 and end >= start:
        hit = hits[0]
        line = min(end, max(start, int(hit["line"])))
        return {
            **base,
            "start_line": max(start, line - EXPRESSION_RADIUS),
            "end_line": min(end, line + EXPRESSION_RADIUS),
            "selection_reason": "semantic_mechanism_window",
            "mechanism_kind": hit["kind"],
            "mechanism_terms": hit["matched_terms"],
        }
    return {
        **base,
        "start_line": start,
        "end_line": end,
        "selection_reason": "callable_symbol_range",
    }


def valid_source_ranges(items: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    for item in items:
        candidate = source_range(item, query)
        start = int(candidate.get("start_line") or 0)
        end = int(candidate.get("end_line") or 0)
        if start <= 0 or end < start:
            continue
        ranges.append(candidate)
        if len(ranges) >= MAX_SOURCE_RANGES:
            break
    return ranges
