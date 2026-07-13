# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .models import EVIDENCE_CHAIN_LIMIT, NETWORK_EDGE_LIMIT, NETWORK_MAX_DEPTH, Project, QUERY_ALLOWED_EDGE_RELATIONS
from .records import row_dict
from .storage import connect

BATCHED_EDGE_TARGET_SIZE = 200


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
