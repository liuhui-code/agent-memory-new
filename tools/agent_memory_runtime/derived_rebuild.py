# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from typing import Any

from .code_wiki_edges import rebuild_code_memory_edges
from .code_wiki_imports import project_for_learning_source
from .models import Project
from .records import output
from .storage import connect, ensure_initialized, resolve_project
from .storage_search_schema import rebuild_search_indexes


def maintain_rebuild_derived(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, getattr(args, "source", None))
    target = str(args.target)
    payload: dict[str, Any] = {
        "project_id": project.project_id,
        "source": str(source_project.root),
        "target": target,
    }
    if target in {"search", "all"}:
        payload["search"] = rebuild_search(project)
    if target in {"graph", "all"}:
        payload.update(rebuild_graph(source_project))
    output(payload, args.json)


def rebuild_search(project: Project) -> dict[str, Any]:
    with connect(project) as conn:
        before = search_counts(conn)
        rebuild_search_indexes(conn)
        after = search_counts(conn)
        conn.commit()
    return {"before": before, "after": after, "status": "rebuilt"}


def rebuild_graph(project: Project) -> dict[str, Any]:
    with connect(project) as conn:
        business_before = business_snapshot(conn, project.project_id)
        memory_before = durable_memory_counts(conn, project.project_id)
        graph_before = graph_summary(conn, project.project_id)
        conn.execute("DELETE FROM memory_edges WHERE project_id = ?", (project.project_id,))
        semantic_stats = rebuild_code_memory_edges(conn, project)
        graph_after = graph_summary(conn, project.project_id)
        business_after = business_snapshot(conn, project.project_id)
        memory_after = durable_memory_counts(conn, project.project_id)
        conn.commit()
    return {
        "graph": {
            "before": graph_before,
            "after": graph_after,
            "semantic_index": semantic_stats,
            "status": "rebuilt",
        },
        "preserved": {
            "code_business_rows_changed": len(business_before.symmetric_difference(business_after)),
            "durable_memory_counts_before": memory_before,
            "durable_memory_counts_after": memory_after,
            "durable_memory_unchanged": memory_before == memory_after,
        },
    }


def search_counts(conn: Any) -> dict[str, int]:
    tables = (
        "semantic_fact_fts",
        "reflection_fts",
        "episode_fts",
        "code_file_fts",
        "code_symbol_fts",
        "code_log_fts",
    )
    return {
        table: int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])
        for table in tables
    }


def durable_memory_counts(conn: Any, project_id: str) -> dict[str, int]:
    return {
        table: int(
            conn.execute(
                f"SELECT COUNT(*) AS count FROM {table} WHERE project_id = ?",
                (project_id,),
            ).fetchone()["count"]
        )
        for table in ("semantic_facts", "reflections", "episodes")
    }


def business_snapshot(conn: Any, project_id: str) -> set[tuple[Any, ...]]:
    result: set[tuple[Any, ...]] = set()
    for table in ("code_files", "code_symbols", "code_log_statements"):
        rows = conn.execute(
            f"""
            SELECT id, business_summary, business_terms
            FROM {table}
            WHERE project_id = ?
              AND (COALESCE(business_summary, '') != '' OR COALESCE(business_terms, '') NOT IN ('', '[]'))
            """,
            (project_id,),
        ).fetchall()
        result.update(
            (table, int(row["id"]), str(row["business_summary"] or ""), str(row["business_terms"] or ""))
            for row in rows
        )
    return result


def graph_summary(conn: Any, project_id: str) -> dict[str, Any]:
    relation_rows = conn.execute(
        """
        SELECT relation, COUNT(*) AS count
        FROM memory_edges
        WHERE project_id = ? AND valid_to IS NULL
        GROUP BY relation
        ORDER BY count DESC, relation
        """,
        (project_id,),
    ).fetchall()
    relation_counts = {str(row["relation"]): int(row["count"]) for row in relation_rows}
    edge_count = sum(relation_counts.values())
    node_count = sum(
        int(
            conn.execute(
                f"SELECT COUNT(*) AS count FROM {table} WHERE project_id = ?",
                (project_id,),
            ).fetchone()["count"]
        )
        for table in ("code_files", "code_symbols", "code_log_statements")
    )
    dominant_relation = next(iter(relation_counts), None)
    dominant_count = relation_counts.get(dominant_relation or "", 0)
    dominant_share = round(dominant_count / max(1, edge_count), 4)
    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "edges_per_node": round(edge_count / max(1, node_count), 3),
        "relation_counts": relation_counts,
        "dominant_relation": dominant_relation,
        "dominant_relation_share": dominant_share,
        "relation_dominance_warning": (
            f"{dominant_relation} occupies {dominant_share:.1%} of active edges"
            if dominant_relation not in {None, "contains"} and dominant_share >= 0.5
            else None
        ),
    }
