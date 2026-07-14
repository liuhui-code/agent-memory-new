# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import Counter
import sqlite3
from typing import Any


def scoped_node_counts(scoped_ids: dict[str, set[int]]) -> dict[str, int]:
    return {entity_type: len(ids) for entity_type, ids in sorted(scoped_ids.items())}


def _edge_rows_for_side(
    conn: sqlite3.Connection,
    project_id: str,
    entity_type: str,
    ids: set[int],
    side: str,
) -> list[sqlite3.Row]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    id_column = "source_id" if side == "source" else "target_id"
    type_column = "source_type" if side == "source" else "target_type"
    return conn.execute(
        f"""
        SELECT id, relation
        FROM memory_edges
        WHERE project_id = ? AND valid_to IS NULL AND {type_column} = ? AND {id_column} IN ({placeholders})
        """,
        (project_id, entity_type, *sorted(ids)),
    ).fetchall()


def scoped_edge_summary(
    conn: sqlite3.Connection,
    project_id: str,
    scoped_ids: dict[str, set[int]],
) -> dict[str, Any]:
    rows_by_id: dict[int, sqlite3.Row] = {}
    for entity_type, ids in scoped_ids.items():
        for side in ("source", "target"):
            for row in _edge_rows_for_side(conn, project_id, entity_type, ids, side):
                rows_by_id[int(row["id"])] = row
    relation_counts = Counter(str(row["relation"] or "unknown") for row in rows_by_id.values())
    return {
        "node_counts": scoped_node_counts(scoped_ids),
        "edge_count": len(rows_by_id),
        "relation_counts": dict(sorted(relation_counts.items())),
    }


def edge_rebuild_metrics(
    *,
    scope_file_paths: list[str],
    before: dict[str, Any],
    after: dict[str, Any],
    replace: bool,
) -> dict[str, Any]:
    before_edges = int(before.get("edge_count") or 0)
    after_edges = int(after.get("edge_count") or 0)
    return {
        "mode": "replace" if replace else "merge",
        "scope_file_count": len(scope_file_paths),
        "scope_files": sorted(scope_file_paths),
        "before": before,
        "after": after,
        "edges_deleted_estimate": before_edges,
        "edges_inserted_estimate": after_edges,
        "edge_delta": after_edges - before_edges,
    }
