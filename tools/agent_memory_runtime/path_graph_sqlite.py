# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

from .design_evidence import evidence_class
from .graph_quality_snapshot import load_graph_revision
from .models import Project
from .path_context_models import (
    ExpectedLogAnchor,
    GraphEdge,
    GraphExpansion,
    GraphNode,
    GraphSnapshot,
    NodeRef,
)
from .storage import connect


class SQLiteProgramGraphReader:
    def __init__(self, project: Project) -> None:
        self.project = project

    def snapshot(self) -> GraphSnapshot:
        with connect(self.project) as conn:
            revision = load_graph_revision(conn, self.project.project_id)
        return GraphSnapshot(self.project.project_id, revision)

    def emitters(self, log_ids: Sequence[int]) -> dict[int, tuple[GraphNode, ...]]:
        if not log_ids:
            return {}
        with connect(self.project) as conn:
            rows = conn.execute(
                f"""
                SELECT e.target_id AS log_id, s.*, f.language
                FROM memory_edges e
                JOIN code_symbols s ON s.project_id = e.project_id
                  AND e.source_type = 'code_symbol' AND s.id = e.source_id
                LEFT JOIN code_files f ON f.project_id = s.project_id AND f.file_path = s.file_path
                WHERE e.project_id = ? AND e.valid_to IS NULL
                  AND e.relation = 'emits_log' AND e.target_type = 'code_log_statement'
                  AND e.target_id IN ({','.join('?' for _ in log_ids)})
                ORDER BY e.confidence DESC, s.symbol_key IS NOT NULL DESC, s.id
                """,
                (self.project.project_id, *log_ids),
            ).fetchall()
            grouped: dict[int, list[GraphNode]] = defaultdict(list)
            for row in rows:
                grouped[int(row["log_id"])].append(symbol_node(dict(row)))
            missing = [log_id for log_id in log_ids if log_id not in grouped]
            if missing:
                self._fallback_emitters(conn, missing, grouped)
        return {key: tuple(value) for key, value in grouped.items()}

    def predecessors(self, node_refs: Sequence[NodeRef], relations: set[str]) -> GraphExpansion:
        refs = unique_refs(node_refs)
        if not refs or not relations:
            return GraphExpansion()
        clauses: list[str] = []
        params: list[Any] = [self.project.project_id, *sorted(relations)]
        for entity_type, ids in grouped_ids(refs).items():
            clauses.append(f"(target_type = ? AND target_id IN ({','.join('?' for _ in ids)}))")
            params.extend([entity_type, *ids])
        with connect(self.project) as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM memory_edges
                WHERE project_id = ? AND valid_to IS NULL
                  AND relation IN ({','.join('?' for _ in relations)})
                  AND ({' OR '.join(clauses)})
                ORDER BY confidence DESC, id DESC
                LIMIT 240
                """,
                params,
            ).fetchall()
            edges = tuple(edge_from_row(dict(row)) for row in rows)
            node_refs_to_load = unique_refs([edge.source for edge in edges] + [edge.target for edge in edges])
            nodes = load_nodes(conn, self.project, node_refs_to_load)
        return GraphExpansion(nodes=nodes, edges=edges)

    def nearby_logs(self, node_refs: Sequence[NodeRef]) -> dict[str, tuple[ExpectedLogAnchor, ...]]:
        refs = [ref for ref in unique_refs(node_refs) if ref.entity_type in {"code_symbol", "code_file"}]
        if not refs:
            return {}
        clauses: list[str] = []
        params: list[Any] = [self.project.project_id]
        for entity_type, ids in grouped_ids(refs).items():
            relation = "emits_log" if entity_type == "code_symbol" else "contains"
            clauses.append(
                f"(e.source_type = ? AND e.source_id IN ({','.join('?' for _ in ids)}) AND e.relation = ?)"
            )
            params.extend([entity_type, *ids, relation])
        with connect(self.project) as conn:
            rows = conn.execute(
                f"""
                SELECT e.source_type, e.source_id, l.*
                FROM memory_edges e
                JOIN code_log_statements l ON l.project_id = e.project_id
                  AND e.target_type = 'code_log_statement' AND l.id = e.target_id
                WHERE e.project_id = ? AND e.valid_to IS NULL AND ({' OR '.join(clauses)})
                ORDER BY e.source_type, e.source_id, l.line, l.id
                LIMIT 160
                """,
                params,
            ).fetchall()
        grouped: dict[str, list[ExpectedLogAnchor]] = defaultdict(list)
        for row in rows:
            key = f"{row['source_type']}:{row['source_id']}"
            if len(grouped[key]) >= 4:
                continue
            grouped[key].append(expected_log(dict(row), key))
        return {key: tuple(value) for key, value in grouped.items()}

    def _fallback_emitters(self, conn: Any, log_ids: list[int], grouped: dict[int, list[GraphNode]]) -> None:
        rows = conn.execute(
            f"""
            SELECT l.id AS log_id, s.*, f.language
            FROM code_log_statements l
            JOIN code_symbols s ON s.project_id = l.project_id
              AND s.file_path = l.file_path AND s.symbol = l.function
            LEFT JOIN code_files f ON f.project_id = s.project_id AND f.file_path = s.file_path
            WHERE l.project_id = ? AND l.id IN ({','.join('?' for _ in log_ids)})
            ORDER BY s.symbol_key IS NOT NULL DESC, s.id
            """,
            (self.project.project_id, *log_ids),
        ).fetchall()
        for row in rows:
            grouped[int(row["log_id"])].append(symbol_node(dict(row)))


def grouped_ids(refs: Sequence[NodeRef]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = defaultdict(list)
    for ref in refs:
        result[ref.entity_type].append(ref.entity_id)
    return result


def unique_refs(refs: Sequence[NodeRef]) -> list[NodeRef]:
    return list({ref.key: ref for ref in refs}.values())


def load_nodes(conn: Any, project: Project, refs: Sequence[NodeRef]) -> dict[str, GraphNode]:
    result: dict[str, GraphNode] = {}
    ids_by_type = grouped_ids(refs)
    symbol_ids = ids_by_type.get("code_symbol", [])
    if symbol_ids:
        rows = conn.execute(
            f"""
            SELECT s.*, f.language FROM code_symbols s
            LEFT JOIN code_files f ON f.project_id = s.project_id AND f.file_path = s.file_path
            WHERE s.project_id = ? AND s.id IN ({','.join('?' for _ in symbol_ids)})
            """,
            (project.project_id, *symbol_ids),
        ).fetchall()
        result.update((f"code_symbol:{row['id']}", symbol_node(dict(row))) for row in rows)
    file_ids = ids_by_type.get("code_file", [])
    if file_ids:
        rows = conn.execute(
            f"SELECT * FROM code_files WHERE project_id = ? AND id IN ({','.join('?' for _ in file_ids)})",
            (project.project_id, *file_ids),
        ).fetchall()
        result.update((f"code_file:{row['id']}", file_node(dict(row))) for row in rows)
    return result


def symbol_node(row: dict[str, Any]) -> GraphNode:
    return GraphNode(
        ref=NodeRef("code_symbol", int(row["id"])),
        kind="symbol",
        name=str(row.get("symbol") or ""),
        qualified_name=str(row.get("qualified_name") or row.get("symbol") or ""),
        file_path=str(row.get("file_path") or ""),
        symbol_type=str(row.get("symbol_type") or ""),
        language=str(row.get("language") or ""),
        start_line=int(row["start_line"]) if row.get("start_line") is not None else None,
        end_line=int(row["end_line"]) if row.get("end_line") is not None else None,
    )


def file_node(row: dict[str, Any]) -> GraphNode:
    path = str(row.get("file_path") or "")
    return GraphNode(
        ref=NodeRef("code_file", int(row["id"])),
        kind="file",
        name=path.rsplit("/", 1)[-1],
        qualified_name=path,
        file_path=path,
        language=str(row.get("language") or ""),
    )


def edge_from_row(row: dict[str, Any]) -> GraphEdge:
    kind = str(row.get("evidence_kind") or "legacy")
    extractor = str(row.get("extractor_version") or "legacy")
    return GraphEdge(
        edge_id=int(row["id"]),
        source=NodeRef(str(row["source_type"]), int(row["source_id"])),
        target=NodeRef(str(row["target_type"]), int(row["target_id"])),
        relation=str(row["relation"]),
        evidence_class=evidence_class(kind, extractor),
        evidence_kind=kind,
        extractor_version=extractor,
        source_revision=str(row.get("source_revision") or ""),
        confidence=float(row.get("confidence") or 0.0),
        ambiguity="dynamic_target" if float(row.get("confidence") or 0.0) < 0.7 else "",
    )


def expected_log(row: dict[str, Any], node_key: str) -> ExpectedLogAnchor:
    return ExpectedLogAnchor(
        log_id=int(row["id"]),
        node_id=node_key,
        message_template=str(row.get("message_template") or ""),
        logger=str(row.get("logger") or ""),
        event_name=str(row.get("business_event") or ""),
        file_path=str(row.get("file_path") or ""),
        function=str(row.get("function") or ""),
        line=int(row["line"]) if row.get("line") is not None else None,
    )
