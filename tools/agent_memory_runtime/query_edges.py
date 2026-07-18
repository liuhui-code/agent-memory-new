# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .models import EVIDENCE_CHAIN_LIMIT, NETWORK_EDGE_LIMIT, NETWORK_MAX_DEPTH, Project, QUERY_ALLOWED_EDGE_RELATIONS
from .records import row_dict
from .storage import connect

BATCHED_EDGE_TARGET_SIZE = 200
EDGE_RECALL_MULTIPLIER = 4
FILE_BACKED_ENTITY_TABLES = {
    "code_symbol": "code_symbols",
    "code_log_statement": "code_log_statements",
}
RELATION_PRIORITY = {
    "passes_property": 4,
    "renders_component": 3,
    "routes_to": 2,
    "imports": 1,
}


def collect_related_edge_candidates(
    project: Project,
    targets: dict[str, set[int]],
) -> list[dict[str, Any]]:
    return collect_related_edges(project, targets, EDGE_RECALL_MULTIPLIER)


def collect_related_edges(
    project: Project,
    targets: dict[str, set[int]],
    recall_multiplier: int = 1,
) -> list[dict[str, Any]]:
    edge_map: dict[int, dict[str, Any]] = {}
    edge_limit = NETWORK_EDGE_LIMIT * max(1, recall_multiplier)

    def chunked(values: list[int], size: int) -> list[list[int]]:
        return [values[index : index + size] for index in range(0, len(values), size)]

    with connect(project) as conn:
        allowed_relations = sorted(QUERY_ALLOWED_EDGE_RELATIONS)
        relation_placeholders = ",".join("?" for _ in allowed_relations)
        for entity_type, ids in targets.items():
            ordered_ids = sorted(ids)
            if not ordered_ids:
                continue
            for id_batch in chunked(ordered_ids, BATCHED_EDGE_TARGET_SIZE):
                placeholders = ",".join("?" for _ in id_batch)
                node_table = FILE_BACKED_ENTITY_TABLES.get(entity_type)
                file_cte = ""
                file_clauses = ""
                file_parameters: list[Any] = []
                if node_table:
                    file_cte = f"""
                    WITH matched_files AS (
                      SELECT files.id
                      FROM code_files AS files
                      JOIN {node_table} AS nodes
                        ON nodes.project_id = files.project_id
                       AND nodes.file_path = files.file_path
                      WHERE nodes.project_id = ?
                        AND nodes.id IN ({placeholders})
                    )
                    """
                    file_clauses = """
                        OR (source_type = 'code_file' AND source_id IN (SELECT id FROM matched_files))
                        OR (target_type = 'code_file' AND target_id IN (SELECT id FROM matched_files))
                    """
                    file_parameters = [project.project_id, *id_batch]
                rows = conn.execute(
                    f"""
                    {file_cte}
                    SELECT *
                    FROM memory_edges
                    WHERE project_id = ?
                      AND valid_to IS NULL
                      AND relation IN ({relation_placeholders})
                      AND (
                        (source_type = ? AND source_id IN ({placeholders}))
                        OR (target_type = ? AND target_id IN ({placeholders}))
                        {file_clauses}
                      )
                    ORDER BY CASE
                      WHEN relation = 'passes_property' THEN 4
                      WHEN relation = 'renders_component' THEN 3
                      WHEN relation = 'routes_to' THEN 2
                      WHEN relation = 'imports' THEN 1
                      ELSE 0
                    END DESC, confidence DESC, id DESC
                    LIMIT ?
                    """,
                    [
                        *file_parameters,
                        project.project_id,
                        *allowed_relations,
                        entity_type,
                        *id_batch,
                        entity_type,
                        *id_batch,
                        edge_limit,
                    ],
                ).fetchall()
                for row in rows:
                    edge_map[row["id"]] = row_dict(row)
    edges = list(edge_map.values())
    edges.sort(
        key=lambda item: (
            RELATION_PRIORITY.get(str(item.get("relation") or ""), 0),
            item.get("confidence", 0),
            item.get("id", 0),
        ),
        reverse=True,
    )
    return edges[:edge_limit]



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
    if edge.get("relation") == "passes_property":
        return "matched ArkTS components connected by a property binding"
    if edge.get("relation") == "renders_component":
        return "matched ArkTS components connected by composition"
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
