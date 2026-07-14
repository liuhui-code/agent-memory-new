# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .models import Project
from .design_evidence import EVIDENCE_RANK, evidence_class
from .storage import connect
from .text import query_tokens, unique_list


ARCHITECTURE_TYPES = {"code_file", "code_symbol", "code_log_statement"}
DEPENDENCY_RELATIONS = {
    "imports", "routes_to", "renders_component", "uses_service", "calls",
    "configured_by", "tested_by", "reads_state", "writes_state",
    "consumes_api", "implements", "overrides", "registers_callback",
    "extends", "awaits",
}


def build_architecture_slice(
    project: Project,
    evidence_items: Iterable[Any],
    query: str,
    explicit_paths: list[str] | None = None,
    max_nodes: int = 80,
    max_edges: int = 160,
    max_depth: int = 2,
) -> dict[str, Any]:
    limits = {
        "max_nodes": max(1, min(max_nodes, 80)),
        "max_edges": max(1, min(max_edges, 160)),
        "max_depth": max(0, min(max_depth, 2)),
    }
    paths = unique_paths((explicit_paths or []) + evidence_paths(evidence_items))
    with connect(project) as conn:
        anchor_rows = find_anchor_files(conn, project, paths, query)
        anchor_keys = {("code_file", int(row["id"])) for row in anchor_rows}
        seen = set(anchor_keys)
        frontier = set(anchor_keys)
        edge_rows: dict[int, dict[str, Any]] = {}
        for _depth in range(limits["max_depth"]):
            if not frontier or len(edge_rows) >= limits["max_edges"]:
                break
            rows = edges_for_frontier(
                conn,
                project,
                frontier,
                limits["max_edges"] - len(edge_rows),
            )
            next_frontier: set[tuple[str, int]] = set()
            for row in rows:
                edge_rows[int(row["id"])] = row
                for key in edge_endpoints(row):
                    if key in seen or len(seen) >= limits["max_nodes"]:
                        continue
                    seen.add(key)
                    next_frontier.add(key)
            frontier = next_frontier
        node_rows = load_nodes(conn, project, seen)

    node_map = {key: node_payload(key, row) for key, row in node_rows.items()}
    stable_edges = stable_edge_payloads(edge_rows.values(), node_map, limits["max_edges"])
    nodes = sorted(node_map.values(), key=lambda item: (item["layer"], item["id"]))
    anchor_ids = [node_map[key]["id"] for key in anchor_keys if key in node_map]
    relations = Counter(edge["relation"] for edge in stable_edges)
    return {
        "entry_points": anchor_ids,
        "nodes": nodes,
        "edges": stable_edges,
        "boundaries": boundary_summary(nodes, stable_edges),
        "state_owners": state_owners(stable_edges),
        "extension_points": extension_points(nodes, stable_edges),
        "public_consumers": public_consumers(stable_edges, set(anchor_ids)),
        "test_anchors": [node for node in nodes if node["layer"] == "test"][:12],
        "observability_anchors": [node for node in nodes if node["kind"] == "log"][:12],
        "evidence_gaps": slice_gaps(anchor_ids, stable_edges, nodes),
        "audit": {
            **limits,
            "node_count": len(nodes),
            "edge_count": len(stable_edges),
            "relations": dict(relations),
            "truncated_nodes": len(seen) >= limits["max_nodes"],
            "truncated_edges": len(edge_rows) >= limits["max_edges"],
        },
    }


def evidence_paths(items: Iterable[Any]) -> list[str]:
    paths: list[str] = []
    for item in items:
        raw = getattr(item, "raw", {}) or {}
        value = raw.get("file_path") or getattr(item, "location", None)
        if not value:
            continue
        path = str(value).split(":", 1)[0]
        if Path(path).suffix:
            paths.append(path)
    return paths


def unique_paths(paths: list[str]) -> list[str]:
    return unique_list([str(path).strip().replace("\\", "/") for path in paths if str(path).strip()])[:12]


def find_anchor_files(conn: Any, project: Project, paths: list[str], query: str) -> list[dict[str, Any]]:
    rows: list[Any] = []
    if paths:
        placeholders = ",".join("?" for _ in paths)
        rows = conn.execute(
            f"SELECT * FROM code_files WHERE project_id = ? AND file_path IN ({placeholders}) LIMIT 12",
            (project.project_id, *paths),
        ).fetchall()
    if rows:
        return [dict(row) for row in rows]
    terms = [term for term in query_tokens(query) if len(term) > 2][:6]
    if not terms:
        return []
    clauses = " OR ".join("LOWER(file_path || ' ' || COALESCE(business_summary, '') || ' ' || COALESCE(business_terms, '')) LIKE ?" for _ in terms)
    rows = conn.execute(
        f"SELECT * FROM code_files WHERE project_id = ? AND ({clauses}) ORDER BY updated_at DESC LIMIT 8",
        (project.project_id, *(f"%{term.lower()}%" for term in terms)),
    ).fetchall()
    return [dict(row) for row in rows]


def edges_for_frontier(
    conn: Any,
    project: Project,
    frontier: set[tuple[str, int]],
    limit: int,
) -> list[dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    grouped: dict[str, list[int]] = defaultdict(list)
    for entity_type, entity_id in frontier:
        grouped[entity_type].append(entity_id)
    for entity_type, ids in grouped.items():
        placeholders = ",".join("?" for _ in ids)
        query_limit = max(1, min(limit - len(rows), 160))
        if query_limit <= 0:
            break
        matches = conn.execute(
            f"""
            SELECT * FROM memory_edges
            WHERE project_id = ? AND valid_to IS NULL
              AND ((source_type = ? AND source_id IN ({placeholders}))
                OR (target_type = ? AND target_id IN ({placeholders})))
              AND source_type IN ('code_file', 'code_symbol', 'code_log_statement')
              AND target_type IN ('code_file', 'code_symbol', 'code_log_statement')
            ORDER BY confidence DESC, id DESC LIMIT ?
            """,
            (project.project_id, entity_type, *ids, entity_type, *ids, query_limit),
        ).fetchall()
        for row in matches:
            rows[int(row["id"])] = dict(row)
    return list(rows.values())[:limit]


def edge_endpoints(row: dict[str, Any]) -> tuple[tuple[str, int], tuple[str, int]]:
    return (
        (str(row["source_type"]), int(row["source_id"])),
        (str(row["target_type"]), int(row["target_id"])),
    )


def load_nodes(
    conn: Any,
    project: Project,
    keys: set[tuple[str, int]],
) -> dict[tuple[str, int], dict[str, Any]]:
    result: dict[tuple[str, int], dict[str, Any]] = {}
    tables = {
        "code_file": "code_files",
        "code_symbol": "code_symbols",
        "code_log_statement": "code_log_statements",
    }
    for entity_type, table in tables.items():
        ids = sorted(entity_id for kind, entity_id in keys if kind == entity_type)
        if not ids:
            continue
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE project_id = ? AND id IN ({placeholders})",
            (project.project_id, *ids),
        ).fetchall()
        for row in rows:
            result[(entity_type, int(row["id"]))] = dict(row)
    return result


def node_payload(key: tuple[str, int], row: dict[str, Any]) -> dict[str, Any]:
    entity_type, entity_id = key
    path = str(row.get("file_path") or "")
    if entity_type == "code_file":
        stable_id, kind, name = f"file:{path}", "file", path
    elif entity_type == "code_symbol":
        name = str(row.get("symbol") or entity_id)
        stable_id, kind = f"symbol:{path}::{name}", str(row.get("symbol_type") or "symbol")
    else:
        line = row.get("line") or entity_id
        stable_id, kind = f"log:{path}:{line}", "log"
        name = str(row.get("message_template") or row.get("function") or line)
    return {
        "id": stable_id,
        "entity_type": entity_type,
        "record_id": entity_id,
        "kind": kind,
        "name": name,
        "file_path": path,
        "layer": infer_layer(path),
        "summary": str(row.get("business_summary") or row.get("summary") or ""),
        "symbol_key": row.get("symbol_key"),
        "qualified_name": row.get("qualified_name"),
        "signature": row.get("signature"),
        "span": {
            "start_line": row.get("start_line"),
            "end_line": row.get("end_line"),
        } if entity_type == "code_symbol" else None,
        "semantic_adapter": row.get("semantic_adapter"),
        "evidence_class": row.get("evidence_class"),
    }


def infer_layer(path: str) -> str:
    value = path.lower()
    if any(term in value for term in ("test", "spec")):
        return "test"
    if value.endswith((".json", ".json5", ".yaml", ".yml", ".toml")) or "config" in value:
        return "config"
    if any(term in value for term in ("page", "view", "component", "/ui/")):
        return "ui"
    if any(term in value for term in ("repository", "storage", "database", "cache", "/data/")):
        return "data"
    if any(term in value for term in ("viewmodel", "/state/", "/store/")):
        return "state"
    if any(term in value for term in ("service", "client", "/api/")):
        return "service"
    return "core"


def stable_edge_payloads(
    rows: Iterable[dict[str, Any]],
    nodes: dict[tuple[str, int], dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        source_key, target_key = edge_endpoints(row)
        if source_key not in nodes or target_key not in nodes:
            continue
        result.append({
            "id": int(row["id"]),
            "source": nodes[source_key]["id"],
            "relation": str(row["relation"]),
            "target": nodes[target_key]["id"],
            "confidence": round(float(row.get("confidence") or 0.0), 3),
            "evidence": str(row.get("evidence") or ""),
            "evidence_kind": str(row.get("evidence_kind") or "legacy"),
            "evidence_class": evidence_class(
                str(row.get("evidence_kind") or "legacy"),
                str(row.get("extractor_version") or "legacy"),
            ),
            "extractor_version": str(row.get("extractor_version") or "legacy"),
            "source_revision": row.get("source_revision"),
        })
    return sorted(
        result,
        key=lambda edge: (-EVIDENCE_RANK[edge["evidence_class"]], -edge["confidence"], edge["id"]),
    )[:limit]


def boundary_summary(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {node["id"]: node for node in nodes}
    grouped: dict[str, set[str]] = defaultdict(set)
    for node in nodes:
        grouped[node["layer"]].add(node["file_path"])
    incoming = Counter(by_id[edge["target"]]["layer"] for edge in edges if edge["source"] in by_id and edge["target"] in by_id)
    return [
        {"layer": layer, "files": sorted(paths)[:12], "incoming_edges": incoming[layer]}
        for layer, paths in sorted(grouped.items())
    ]


def state_owners(edges: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {"owner": edge["source"], "state": edge["target"], "relation": edge["relation"]}
        for edge in edges if edge["relation"] in {"defines_state", "owns_state"}
    ][:20]


def extension_points(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    degree = Counter()
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
    candidates = [node for node in nodes if node["kind"] in {"component", "class", "function", "file"}]
    candidates.sort(key=lambda node: (degree[node["id"]], node["kind"] != "file"), reverse=True)
    return [{"id": node["id"], "kind": node["kind"], "degree": degree[node["id"]]} for node in candidates[:12]]


def public_consumers(edges: list[dict[str, Any]], anchors: set[str]) -> list[dict[str, Any]]:
    return [
        edge for edge in edges
        if edge["relation"] in DEPENDENCY_RELATIONS and edge["target"] in anchors
    ][:20]


def slice_gaps(
    anchors: list[str],
    edges: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    if not anchors:
        gaps.append({"kind": "missing_architecture_anchor", "action": "learn or name the current entry file/symbol"})
    if anchors and not edges:
        gaps.append({"kind": "missing_design_edges", "action": "refresh the narrow learned scope before treating dependency absence as fact"})
    if nodes and not any(node["layer"] == "test" for node in nodes):
        gaps.append({"kind": "missing_test_anchor", "action": "identify focused verification for the proposed design"})
    if nodes and not any(node["kind"] == "log" for node in nodes):
        gaps.append({"kind": "missing_observability_anchor", "action": "check whether changed high-risk paths need a stable result/failure signal"})
    return gaps
