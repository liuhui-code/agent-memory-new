# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .models import Project
from .records import row_dict
from .storage import connect
from .text import code_search_terms, json_list, matching_code_path_segments, query_tokens


PROMOTABLE_RELATIONS = {"imports", "passes_property", "renders_component", "routes_to"}
MAX_GRAPH_NEIGHBORS = 2
GRAPH_SCORE_DECAY = 0.82
REVERSE_ROUTE_SCORE_DECAY = 0.9
GRAPH_MAX_SEED_RATIO = {
    "imports": 0.75,
    "passes_property": 0.95,
    "renders_component": 0.85,
    "routes_to": 0.95,
}
COMPONENT_FLOW_RELATIONS = {"passes_property", "renders_component"}
COMPONENT_FLOW_MAX_DEPTH = 2
COMPONENT_FLOW_CANDIDATE_LIMIT = 24


def collect_result_graph_neighbors(
    project: Project,
    results: dict[str, list[dict[str, Any]]],
    query: str = "",
) -> list[dict[str, Any]]:
    return collect_graph_neighbor_matches(
        project,
        results["edge_matches"],
        results["wiki_matches"],
        results["code_log_matches"],
        query,
    )


def collect_graph_neighbor_matches(
    project: Project,
    edges: list[dict[str, Any]],
    wiki_matches: list[dict[str, Any]],
    log_matches: list[dict[str, Any]],
    query: str = "",
) -> list[dict[str, Any]]:
    matched = matched_endpoint_scores(project, wiki_matches, log_matches)
    candidates: dict[tuple[str, int], tuple[float, str, int]] = {}
    for edge in edges:
        relation = str(edge.get("relation") or "")
        if relation not in PROMOTABLE_RELATIONS:
            continue
        source = endpoint(edge, "source")
        target = endpoint(edge, "target")
        promote_neighbor(candidates, matched, source, target, edge, relation, reverse=False)
        promote_neighbor(candidates, matched, target, source, edge, relation, reverse=True)
    for key, evidence in component_lineage_candidates(
        project,
        matched_path_scores(wiki_matches, log_matches),
        query,
    ).items():
        if evidence[0] > candidates.get(key, (0.0, "", 1))[0]:
            candidates[key] = evidence
    if not candidates:
        return []
    resolved = resolve_candidates(project, candidates)
    resolved.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
    existing_paths = existing_matches_by_path(wiki_matches)
    selected = []
    for item in resolved[:MAX_GRAPH_NEIGHBORS]:
        file_path = str(item.get("file_path") or "")
        if file_path in existing_paths:
            boost_match(existing_paths[file_path], item)
        else:
            selected.append(item)
    return selected


def existing_matches_by_path(
    values: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in values:
        file_path = str(item.get("file_path") or "")
        current = result.get(file_path)
        if file_path and (
            current is None
            or float(item.get("score") or 0.0) > float(current.get("score") or 0.0)
        ):
            result[file_path] = item
    return result


def boost_match(target: dict[str, Any], evidence: dict[str, Any]) -> None:
    target["score"] = max(
        float(target.get("score") or 0.0),
        float(evidence.get("score") or 0.0),
    )
    target["match_reasons"] = list(dict.fromkeys([
        *(str(item) for item in target.get("match_reasons") or []),
        *(str(item) for item in evidence.get("match_reasons") or []),
    ]))


def matched_endpoint_scores(
    project: Project,
    wiki_matches: list[dict[str, Any]],
    log_matches: list[dict[str, Any]],
) -> dict[tuple[str, int], float]:
    result: dict[tuple[str, int], float] = {}
    path_scores: dict[str, float] = {}
    for item in wiki_matches:
        entity_type = "code_file" if item.get("kind") == "file" else "code_symbol"
        add_score(result, entity_type, item)
        add_path_score(path_scores, item)
    for item in log_matches:
        add_score(result, "code_log_statement", item)
        add_path_score(path_scores, item)
    add_containing_file_scores(project, result, path_scores)
    return result


def add_path_score(result: dict[str, float], item: dict[str, Any]) -> None:
    file_path = str(item.get("file_path") or "")
    if file_path:
        result[file_path] = max(result.get(file_path, 0.0), float(item.get("score") or 0.0))


def matched_path_scores(
    wiki_matches: list[dict[str, Any]],
    log_matches: list[dict[str, Any]],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for item in [*wiki_matches, *log_matches]:
        add_path_score(scores, item)
    return scores


def component_lineage_candidates(
    project: Project,
    path_scores: dict[str, float],
    query: str,
) -> dict[tuple[str, int], tuple[float, str, int]]:
    seeds = query_conditioned_lineage_seeds(path_scores, query)
    if not seeds:
        return {}
    values = ",".join("(?, ?)" for _ in seeds)
    parameters: list[Any] = []
    for path, score in seeds:
        parameters.extend([path, score])
    with connect(project) as conn:
        rows = conn.execute(
            f"""
            WITH RECURSIVE
            seed_paths(file_path, seed_score) AS (VALUES {values}),
            seeds(file_id, seed_score) AS (
              SELECT files.id, seed_paths.seed_score
              FROM seed_paths
              JOIN code_files AS files
                ON files.project_id = ? AND files.file_path = seed_paths.file_path
            ),
            component_edges(source_file_id, target_file_id, relation, evidence, confidence) AS (
              SELECT edges.source_id, target_files.id, edges.relation,
                     edges.evidence, edges.confidence
              FROM memory_edges AS edges
              JOIN code_symbols AS target_symbols
                ON edges.target_type = 'code_symbol'
               AND target_symbols.project_id = edges.project_id
               AND target_symbols.id = edges.target_id
              JOIN code_files AS target_files
                ON target_files.project_id = target_symbols.project_id
               AND target_files.file_path = target_symbols.file_path
              WHERE edges.project_id = ?
                AND edges.valid_to IS NULL
                AND edges.source_type = 'code_file'
                AND edges.relation IN ('passes_property', 'renders_component')
            ),
            walk(file_id, depth, score, relation, evidence, trail) AS (
              SELECT edges.source_file_id, 1,
                     seeds.seed_score * (0.72 + edges.confidence * 0.2),
                     edges.relation, edges.evidence,
                     ',' || seeds.file_id || ',' || edges.source_file_id || ','
              FROM component_edges AS edges
              JOIN seeds ON seeds.file_id = edges.target_file_id
              WHERE edges.source_file_id NOT IN (SELECT file_id FROM seeds)
              UNION ALL
              SELECT edges.source_file_id, walk.depth + 1,
                     walk.score * (0.72 + edges.confidence * 0.2),
                     edges.relation, edges.evidence,
                     walk.trail || edges.source_file_id || ','
              FROM component_edges AS edges
              JOIN walk ON walk.file_id = edges.target_file_id
              WHERE walk.depth < ?
                AND instr(walk.trail, ',' || edges.source_file_id || ',') = 0
                AND edges.source_file_id NOT IN (SELECT file_id FROM seeds)
            )
            SELECT file_id, depth, score, relation, evidence
            FROM walk
            ORDER BY score DESC, depth ASC, file_id ASC
            LIMIT ?
            """,
            [
                *parameters,
                project.project_id,
                project.project_id,
                COMPONENT_FLOW_MAX_DEPTH,
                COMPONENT_FLOW_CANDIDATE_LIMIT,
            ],
        ).fetchall()
    query_terms = {term for term in query_tokens(query) if len(term) > 2}
    candidates: dict[tuple[str, int], tuple[float, str, int]] = {}
    for row in rows:
        evidence_terms = {term for term in query_tokens(str(row["evidence"] or "")) if len(term) > 2}
        overlap = len(query_terms & evidence_terms)
        support = min(1.0, overlap / 2.0)
        score = float(row["score"] or 0.0) * (0.85 + support * 0.15)
        key = ("code_file", int(row["file_id"]))
        value = (score, str(row["relation"]), int(row["depth"]))
        if score > candidates.get(key, (0.0, "", 1))[0]:
            candidates[key] = value
    return candidates


def query_conditioned_lineage_seeds(
    path_scores: dict[str, float],
    query: str,
) -> list[tuple[str, float]]:
    ranked = sorted(
        path_scores.items(),
        key=lambda item: (
            item[1] * (1.0 + 0.15 * len(matching_code_path_segments(query, item[0]))),
            item[1],
        ),
        reverse=True,
    )
    if not ranked:
        return []
    strongest = ranked[0][1]
    supported = [
        item for item in ranked
        if item[1] >= strongest * 0.7
        or matching_code_path_segments(query, item[0])
    ]
    return supported[:4]


def add_containing_file_scores(
    project: Project,
    result: dict[tuple[str, int], float],
    path_scores: dict[str, float],
) -> None:
    if not path_scores:
        return
    paths = sorted(path_scores)
    placeholders = ",".join("?" for _ in paths)
    with connect(project) as conn:
        rows = conn.execute(
            f"""
            SELECT id, file_path FROM code_files
            WHERE project_id = ? AND file_path IN ({placeholders})
            """,
            (project.project_id, *paths),
        ).fetchall()
    for row in rows:
        key = ("code_file", int(row["id"]))
        result[key] = max(result.get(key, 0.0), path_scores[str(row["file_path"])])


def add_score(
    result: dict[tuple[str, int], float],
    entity_type: str,
    item: dict[str, Any],
) -> None:
    if not isinstance(item.get("id"), int):
        return
    key = (entity_type, int(item["id"]))
    result[key] = max(result.get(key, 0.0), float(item.get("score") or 0.0))


def endpoint(edge: dict[str, Any], prefix: str) -> tuple[str, int] | None:
    entity_type = str(edge.get(f"{prefix}_type") or "")
    entity_id = edge.get(f"{prefix}_id")
    if entity_type not in {"code_file", "code_symbol"} or not isinstance(entity_id, int):
        return None
    return entity_type, entity_id


def promote_neighbor(
    candidates: dict[tuple[str, int], tuple[float, str, int]],
    matched: dict[tuple[str, int], float],
    origin: tuple[str, int] | None,
    neighbor: tuple[str, int] | None,
    edge: dict[str, Any],
    relation: str,
    reverse: bool,
) -> None:
    if origin not in matched or neighbor is None:
        return
    origin_score = matched[origin]
    decay = REVERSE_ROUTE_SCORE_DECAY if relation == "routes_to" and reverse else GRAPH_SCORE_DECAY
    score = min(
        origin_score * GRAPH_MAX_SEED_RATIO.get(relation, 0.75),
        origin_score * decay + float(edge.get("confidence") or 0.0) * 5.0,
    )
    lexical_support = min(1.0, matched.get(neighbor, 0.0) / max(origin_score, 0.001))
    score *= 0.5 + lexical_support * 0.5
    if score <= matched.get(neighbor, 0.0):
        return
    if score > candidates.get(neighbor, (0.0, "", 1))[0]:
        candidates[neighbor] = score, relation, 1


def resolve_candidates(
    project: Project,
    candidates: dict[tuple[str, int], tuple[float, str, int]],
) -> list[dict[str, Any]]:
    file_ids = sorted(item[1] for item in candidates if item[0] == "code_file")
    symbol_ids = sorted(item[1] for item in candidates if item[0] == "code_symbol")
    with connect(project) as conn:
        symbols = rows_by_ids(conn, "code_symbols", project.project_id, symbol_ids)
        files = rows_by_ids(conn, "code_files", project.project_id, file_ids)
        representative = representative_symbols(
            conn,
            project.project_id,
            [str(row["file_path"]) for row in files],
        )
    resolved = [
        neighbor_item(row, candidates[("code_symbol", int(row["id"]))])
        for row in symbols
    ]
    for row in files:
        symbol = representative.get(str(row["file_path"]))
        source = symbol if symbol is not None else row
        resolved.append(neighbor_item(source, candidates[("code_file", int(row["id"]))]))
    return resolved


def rows_by_ids(
    conn: Any,
    table: str,
    project_id: str,
    ids: list[int],
) -> list[Any]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    return conn.execute(
        f"SELECT * FROM {table} WHERE project_id = ? AND id IN ({placeholders})",
        (project_id, *ids),
    ).fetchall()


def representative_symbols(
    conn: Any,
    project_id: str,
    file_paths: list[str],
) -> dict[str, Any]:
    if not file_paths:
        return {}
    placeholders = ",".join("?" for _ in file_paths)
    rows = conn.execute(
        f"""
        SELECT * FROM code_symbols
        WHERE project_id = ? AND file_path IN ({placeholders})
          AND start_line IS NOT NULL AND end_line IS NOT NULL
        ORDER BY CASE symbol_type
          WHEN 'component' THEN 0 WHEN 'class' THEN 1 WHEN 'function' THEN 2 ELSE 3
        END, start_line, id
        """,
        (project_id, *file_paths),
    ).fetchall()
    result: dict[str, Any] = {}
    for row in rows:
        result.setdefault(str(row["file_path"]), row)
    return result


def neighbor_item(row: Any, score_relation: tuple[float, str, int]) -> dict[str, Any]:
    item = row_dict(row)
    item["kind"] = "symbol" if item.get("symbol") else "file"
    item["score"] = round(score_relation[0], 3)
    item["match_reasons"] = ["graph_neighbor", f"graph_relation:{score_relation[1]}"]
    item["graph_depth"] = score_relation[2]
    item["search_terms"] = code_search_terms(item["kind"], item)
    item["business_terms"] = json_list(item.get("business_terms"))
    return item
