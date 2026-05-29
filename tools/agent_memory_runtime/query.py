# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .models import (
    EVIDENCE_CHAIN_LIMIT,
    NETWORK_EDGE_LIMIT,
    NETWORK_MAX_DEPTH,
    Project,
    QUERY_ALLOWED_EDGE_RELATIONS,
)
from .records import memory_warning, row_dict
from .storage import connect, now_iso
from .text import code_search_terms, json_list, query_tokens, score_weighted_fields, tokenize


def collect_matches(project: Project, query: str) -> dict[str, list[dict[str, Any]]]:
    tokens = query_tokens(query)
    original_terms = set(tokenize(query))
    expanded_terms = set(tokens) - original_terms
    results: dict[str, list[dict[str, Any]]] = {
        "semantic_facts": [],
        "reflections": [],
        "episodes": [],
        "wiki_matches": [],
        "code_log_matches": [],
        "edge_matches": [],
    }
    with connect(project) as conn:
        semantic = conn.execute(
            """
            SELECT *
            FROM semantic_facts
            WHERE project_id = ? AND COALESCE(is_stale, 0) = 0
              AND COALESCE(status, 'active') = 'active'
            """,
            (project.project_id,),
        ).fetchall()
        reflections = conn.execute(
            """
            SELECT *
            FROM reflections
            WHERE project_id = ? AND COALESCE(is_stale, 0) = 0
              AND COALESCE(status, 'active') = 'active'
            """,
            (project.project_id,),
        ).fetchall()
        episodes = conn.execute(
            """
            SELECT *
            FROM episodes
            WHERE project_id = ? AND COALESCE(status, 'active') = 'active'
            """,
            (project.project_id,),
        ).fetchall()
        files = conn.execute(
            """
            SELECT *
            FROM code_files
            WHERE project_id = ?
            """,
            (project.project_id,),
        ).fetchall()
        symbols = conn.execute(
            """
            SELECT *
            FROM code_symbols
            WHERE project_id = ?
            """,
            (project.project_id,),
        ).fetchall()
        logs = conn.execute(
            """
            SELECT *
            FROM code_log_statements
            WHERE project_id = ?
            """,
            (project.project_id,),
        ).fetchall()

    for row in semantic:
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [("semantic_fact", row["fact"], 1.0)],
            [("exact_semantic_fact", row["fact"], 2.0)],
        )
        if score:
            item = row_dict(row)
            item["score"] = score + float(row["confidence"] or 0)
            item["match_reasons"] = reasons
            item["warning"] = memory_warning(item)
            results["semantic_facts"].append(item)

    for row in reflections:
        text = " ".join(
            str(row[key] or "")
            for key in (
                "task",
                "task_type",
                "outcome",
                "problem",
                "summary",
                "reasoning_summary",
                "context_used",
                "what_worked",
                "what_failed",
                "hidden_assumptions",
                "negative_preconditions",
                "verification_method",
                "reuse_feedback",
                "source_cases",
                "skill_candidate",
                "mistake",
                "lesson",
                "future_rule",
                "trigger_condition",
                "repair_action",
                "evidence",
            )
        )
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [("reflection", text, 1.0)],
            [("exact_reflection", text, 2.0)],
        )
        if score:
            item = row_dict(row)
            item["score"] = score
            item["match_reasons"] = reasons
            item["warning"] = memory_warning(item)
            results["reflections"].append(item)

    for row in episodes:
        text = f"{row['task']} {row['summary']} {row['outcome'] or ''}"
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [("episode", text, 0.8)],
            [("exact_episode", text, 1.5)],
        )
        if score:
            item = row_dict(row)
            item["score"] = score
            item["match_reasons"] = reasons
            item["warning"] = memory_warning(item)
            results["episodes"].append(item)

    for row in files:
        search_terms = code_search_terms("file", row)
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [
                ("business_terms", " ".join(json_list(row["business_terms"])), 5.0),
                ("business_summary", row["business_summary"] or "", 3.0),
                ("file_path", row["file_path"], 3.0),
                ("file_summary", row["summary"] or "", 1.0),
                ("file_language", row["language"] or "", 0.6),
                ("search_terms", " ".join(search_terms), 0.8),
            ],
            [("exact_file_path", row["file_path"], 12.0)],
        )
        if score:
            item = row_dict(row)
            item["kind"] = "file"
            item["score"] = score
            item["search_terms"] = search_terms
            item["business_terms"] = json_list(row["business_terms"])
            item["match_reasons"] = reasons
            results["wiki_matches"].append(item)

    for row in symbols:
        search_terms = code_search_terms("symbol", row)
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [
                ("business_terms", " ".join(json_list(row["business_terms"])), 5.0),
                ("business_summary", row["business_summary"] or "", 3.0),
                ("file_path", row["file_path"], 2.0),
                ("symbol", row["symbol"], 4.0),
                ("symbol_type", row["symbol_type"] or "", 2.0),
                ("symbol_summary", row["summary"] or "", 1.5),
                ("search_terms", " ".join(search_terms), 1.0),
            ],
            [
                ("exact_symbol", row["symbol"], 12.0),
                ("exact_file_path", row["file_path"], 4.0),
            ],
        )
        if score:
            item = row_dict(row)
            item["kind"] = "symbol"
            item["score"] = score
            item["search_terms"] = search_terms
            item["business_terms"] = json_list(row["business_terms"])
            item["match_reasons"] = reasons
            results["wiki_matches"].append(item)

    for row in logs:
        search_terms = code_search_terms("log_statement", row)
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [
                ("business_terms", " ".join(json_list(row["business_terms"])), 5.0),
                ("business_summary", row["business_summary"] or "", 3.0),
                ("log_message", row["message_template"], 3.0),
                ("log_context", " ".join(str(row[key] or "") for key in ("file_path", "function", "level", "logger", "raw_statement")), 1.2),
                ("search_terms", " ".join(search_terms), 1.0),
            ],
            [
                ("exact_log_message", row["message_template"], 12.0),
                ("exact_file_path", row["file_path"], 4.0),
                ("exact_function", row["function"] or "", 5.0),
            ],
        )
        if score:
            item = row_dict(row)
            item["kind"] = "log_statement"
            item["score"] = score
            item["search_terms"] = search_terms
            item["business_terms"] = json_list(row["business_terms"])
            item["match_reasons"] = reasons
            results["code_log_matches"].append(item)

    edge_targets: dict[str, set[int]] = {
        "code_file": set(),
        "code_symbol": set(),
        "code_log_statement": set(),
    }
    for item in results["wiki_matches"]:
        if item.get("kind") == "file":
            edge_targets["code_file"].add(int(item["id"]))
        elif item.get("kind") == "symbol":
            edge_targets["code_symbol"].add(int(item["id"]))
    for item in results["code_log_matches"]:
        edge_targets["code_log_statement"].add(int(item["id"]))
    if any(edge_targets.values()):
        results["edge_matches"] = collect_related_edges(project, edge_targets)

    for key in results:
        results[key].sort(key=lambda item: (item.get("score", 0), item.get("created_at", "")), reverse=True)
    return results


def collect_related_edges(project: Project, targets: dict[str, set[int]]) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = [project.project_id]
    for entity_type, ids in targets.items():
        for entity_id in sorted(ids):
            clauses.append("(source_type = ? AND source_id = ?)")
            values.extend([entity_type, entity_id])
            clauses.append("(target_type = ? AND target_id = ?)")
            values.extend([entity_type, entity_id])
    if not clauses:
        return []
    with connect(project) as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM memory_edges
            WHERE project_id = ?
              AND relation IN ({','.join('?' for _ in sorted(QUERY_ALLOWED_EDGE_RELATIONS))})
              AND ({' OR '.join(clauses)})
            ORDER BY confidence DESC, id DESC
            LIMIT ?
            """,
            [
                values[0],
                *sorted(QUERY_ALLOWED_EDGE_RELATIONS),
                *values[1:],
                NETWORK_EDGE_LIMIT,
            ],
        ).fetchall()
    return [row_dict(row) for row in rows]


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


def limited_context(project: Project, query: str) -> dict[str, Any]:
    matches = collect_matches(project, query)
    context = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "query": query,
        "advisory_notice": "Memory is advisory. Current source files and explicit user instructions override stored memory.",
        "semantic_facts": matches["semantic_facts"][:3],
        "reflections": matches["reflections"][:3],
        "episodes": matches["episodes"][:2],
        "wiki_matches": matches["wiki_matches"][:5],
        "code_log_matches": matches["code_log_matches"][:5],
        "edge_matches": matches["edge_matches"][:10],
        "evidence_chains": build_evidence_chains(matches["edge_matches"]),
        "network_limits": network_limits(),
    }
    record_context_use(project, context)
    record_query_miss_if_empty(project, "context", query, context)
    return context


def record_context_use(project: Project, context_data: dict[str, Any]) -> None:
    ts = now_iso()
    updates = [
        ("semantic_facts", context_data.get("semantic_facts", [])),
        ("reflections", context_data.get("reflections", [])),
        ("episodes", context_data.get("episodes", [])),
    ]
    with connect(project) as conn:
        for table, items in updates:
            for item in items:
                conn.execute(
                    f"""
                    UPDATE {table}
                    SET use_count = COALESCE(use_count, 0) + 1,
                        last_used_at = ?
                    WHERE project_id = ? AND id = ?
                    """,
                    (ts, project.project_id, item["id"]),
                )
        conn.commit()


def result_counts(data: dict[str, Any]) -> dict[str, int]:
    return {
        key: len(value)
        for key, value in data.items()
        if isinstance(value, list)
    }


def has_any_result(data: dict[str, Any]) -> bool:
    return any(result_counts(data).values())


def normalize_query_miss(query: str) -> str:
    return " ".join(query.lower().split())


def record_query_miss_if_empty(project: Project, source: str, query: str, data: dict[str, Any]) -> None:
    counts = result_counts(data)
    if any(counts.values()):
        return
    normalized_query = normalize_query_miss(query)
    ts = now_iso()
    counts_json = json.dumps(counts, ensure_ascii=False)
    with connect(project) as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM query_misses
            WHERE project_id = ?
              AND source = ?
              AND normalized_query = ?
              AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """,
            (project.project_id, source, normalized_query),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE query_misses
                SET result_counts = ?,
                    last_seen_at = ?,
                    miss_count = COALESCE(miss_count, 1) + 1
                WHERE project_id = ? AND id = ?
                """,
                (counts_json, ts, project.project_id, existing["id"]),
            )
            conn.commit()
            return
        conn.execute(
            """
            INSERT INTO query_misses(
              project_id, query, normalized_query, source, result_counts,
              created_at, last_seen_at, miss_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                project.project_id,
                query,
                normalized_query,
                source,
                counts_json,
                ts,
                ts,
            ),
        )
        conn.commit()
