# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .design_evidence import evidence_class
from .models import Project
from .semantic_index import SEMANTIC_RELATIONS
from .storage import connect


MAX_CHAIN_DEPTH = 2
MAX_CHAIN_EDGES = 16


def semantic_causal_chains(project: Project, logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chains: list[dict[str, Any]] = []
    with connect(project) as conn:
        for log in logs[:5]:
            symbol = enclosing_symbol(conn, project, log)
            steps: list[dict[str, Any]] = [observed_log_step(log)]
            gaps: list[dict[str, str]] = []
            if not symbol:
                gaps.append({"kind": "missing_enclosing_symbol", "action": "refresh the log file semantic index"})
            else:
                steps.append({
                    "source": f"log:{log['id']}",
                    "relation": "emitted_by",
                    "target": symbol_label(symbol),
                    "target_id": int(symbol["id"]),
                    "evidence_role": "supports",
                    "evidence_class": str(symbol.get("evidence_class") or "static"),
                    "confidence": 0.95,
                })
                steps.extend(traverse_semantic_edges(conn, project, int(symbol["id"])))
                if len(steps) == 2:
                    gaps.append({"kind": "missing_semantic_neighbors", "action": "refresh callers and typed dependencies"})
            chains.append({
                "anchor_log_id": int(log["id"]),
                "anchor": str(log.get("message_template") or log.get("raw_statement") or "")[:160],
                "steps": steps[:MAX_CHAIN_EDGES + 2],
                "gaps": gaps,
            })
    return chains


def enclosing_symbol(conn: Any, project: Project, log: dict[str, Any]) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT s.* FROM memory_edges e
        JOIN code_symbols s ON s.id = e.source_id AND s.project_id = e.project_id
        WHERE e.project_id = ? AND e.valid_to IS NULL
          AND e.source_type = 'code_symbol' AND e.relation = 'emits_log'
          AND e.target_type = 'code_log_statement' AND e.target_id = ?
        ORDER BY s.symbol_key IS NOT NULL DESC, e.confidence DESC LIMIT 1
        """,
        (project.project_id, int(log["id"])),
    ).fetchone()
    if row:
        return dict(row)
    function_name = str(log.get("function") or "")
    if not function_name:
        return None
    row = conn.execute(
        """
        SELECT * FROM code_symbols
        WHERE project_id = ? AND file_path = ? AND symbol = ?
        ORDER BY symbol_key IS NOT NULL DESC, id LIMIT 2
        """,
        (project.project_id, str(log.get("file_path") or ""), function_name),
    ).fetchall()
    return dict(row[0]) if len(row) == 1 else None


def observed_log_step(log: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "runtime",
        "relation": "observed_log",
        "target": f"log:{log['id']}",
        "evidence_role": "observed",
        "evidence_class": "observed",
        "confidence": 1.0,
        "detail": str(log.get("message_template") or log.get("raw_statement") or "")[:160],
    }


def traverse_semantic_edges(conn: Any, project: Project, start_id: int) -> list[dict[str, Any]]:
    frontier = {start_id}
    seen = {start_id}
    selected: dict[int, tuple[dict[str, Any], bool]] = {}
    for _depth in range(MAX_CHAIN_DEPTH):
        if not frontier or len(selected) >= MAX_CHAIN_EDGES:
            break
        placeholders = ",".join("?" for _ in frontier)
        relations = sorted(SEMANTIC_RELATIONS)
        relation_placeholders = ",".join("?" for _ in relations)
        rows = conn.execute(
            f"""
            SELECT * FROM memory_edges
            WHERE project_id = ? AND valid_to IS NULL
              AND relation IN ({relation_placeholders})
              AND source_type = 'code_symbol' AND target_type = 'code_symbol'
              AND (source_id IN ({placeholders}) OR (relation = 'calls' AND target_id IN ({placeholders})))
            ORDER BY
              CASE
                WHEN evidence_kind LIKE 'exact_semantic_%' OR evidence_kind LIKE 'compiler_%' THEN 4
                WHEN evidence_kind LIKE 'static_semantic_%' OR evidence_kind LIKE 'static_%' THEN 3
                WHEN evidence_kind LIKE '%heuristic%' THEN 2
                ELSE 1
              END DESC,
              confidence DESC, id DESC LIMIT ?
            """,
            (project.project_id, *relations, *frontier, *frontier, MAX_CHAIN_EDGES - len(selected)),
        ).fetchall()
        next_frontier: set[int] = set()
        for raw in rows:
            row = dict(raw)
            reverse = int(row["target_id"]) in frontier and int(row["source_id"]) not in frontier
            selected[int(row["id"])] = (row, reverse)
            neighbor = int(row["source_id"] if reverse else row["target_id"])
            if neighbor not in seen:
                seen.add(neighbor)
                next_frontier.add(neighbor)
        frontier = next_frontier
    labels = symbol_labels(conn, project, seen)
    steps: list[dict[str, Any]] = []
    for edge, reverse in selected.values():
        source_id = int(edge["target_id"] if reverse else edge["source_id"])
        target_id = int(edge["source_id"] if reverse else edge["target_id"])
        relation = "called_by" if reverse else str(edge["relation"])
        precision = evidence_class(str(edge.get("evidence_kind") or "legacy"), str(edge.get("extractor_version") or "legacy"))
        role = "possible" if precision in {"exact", "static"} else "inferred"
        steps.append({
            "source": labels.get(source_id, f"symbol:{source_id}"),
            "relation": relation,
            "target": labels.get(target_id, f"symbol:{target_id}"),
            "target_id": target_id,
            "evidence_role": role,
            "evidence_class": precision,
            "confidence": round(float(edge.get("confidence") or 0.0), 3),
            "edge_id": int(edge["id"]),
        })
    return steps[:MAX_CHAIN_EDGES]


def symbol_labels(conn: Any, project: Project, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = conn.execute(
        f"SELECT * FROM code_symbols WHERE project_id = ? AND id IN ({','.join('?' for _ in ids)})",
        (project.project_id, *sorted(ids)),
    ).fetchall()
    return {int(row["id"]): symbol_label(dict(row)) for row in rows}


def symbol_label(row: dict[str, Any]) -> str:
    qualified = str(row.get("qualified_name") or row.get("symbol") or row.get("id"))
    return f"{row.get('file_path')}::{qualified}"


def semantic_chain_links(chains: list[dict[str, Any]], logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    log_by_id = {int(log["id"]): log for log in logs}
    links: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chain in chains:
        log = log_by_id.get(int(chain["anchor_log_id"]))
        for step in chain["steps"]:
            target = str(step.get("target") or "")
            if "::" not in target or target in seen:
                continue
            seen.add(target)
            links.append({
                "target_type": "code_symbol",
                "target_id": step.get("target_id"),
                "target_key": target,
                "relation": "semantic_candidate",
                "score": float(log.get("score") or 0.0) if log else 0.0,
                "evidence": f"{step['evidence_role']}:{step['relation']}:{step['evidence_class']}",
            })
    return links[:10]


def semantic_chain_strings(chains: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for chain in chains:
        for step in chain["steps"][1:]:
            result.append(
                f"{step['source']} {step['relation']} {step['target']} "
                f"[{step['evidence_role']}/{step['evidence_class']}]"
            )
    return result[:16]
