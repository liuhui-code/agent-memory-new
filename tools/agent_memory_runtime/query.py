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
from .text import code_search_terms, json_list, query_tokens, score_weighted_fields, tokenize, unique_list

SEARCH_RESULT_LIMITS = {
    "semantic_facts": 20,
    "reflections": 10,
    "episodes": 10,
    "wiki_matches": 20,
    "code_log_matches": 20,
    "edge_matches": 10,
}

CONTEXT_RESULT_LIMITS = {
    "semantic_facts": 3,
    "reflections": 3,
    "episodes": 2,
    "wiki_matches": 5,
    "code_log_matches": 5,
    "edge_matches": 10,
}

BATCHED_EDGE_TARGET_SIZE = 200


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


def limited_matches(
    matches: dict[str, list[dict[str, Any]]],
    limits: dict[str, int],
) -> dict[str, list[dict[str, Any]]]:
    return {
        key: value[: limits.get(key, len(value))]
        for key, value in matches.items()
    }


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


def focus_from_query(query: str) -> str | None:
    lowered = query.lower()
    if any(trigger in lowered for trigger in ("跳转", "路由", "导航", "白屏", "空白页", "打不开")):
        return "route"
    if any(trigger in lowered for trigger in ("资源", "图片", "图标", "文案", "字符串", "显示不出来", "不显示", "找不到资源")):
        return "resource"
    if any(trigger in lowered for trigger in ("权限", "授权", "依赖", "配置", "ability", "module")):
        return "config"
    if any(trigger in lowered for trigger in ("日志", "报错", "错误", "异常", "失败", "崩溃", "打印", "定位")):
        return "log"
    return None


def infer_followup_focus(query: str, data: dict[str, list[dict[str, Any]]]) -> str | None:
    focus = focus_from_query(query)
    if focus:
        return focus
    for row in data.get("wiki_matches", [])[:3]:
        symbol_type = str(row.get("symbol_type") or "")
        if symbol_type in {"route", "resource", "permission", "dependency", "ability"}:
            return "config" if symbol_type in {"permission", "dependency", "ability"} else symbol_type
    if data.get("code_log_matches"):
        return "log"
    return None


def rank_followup_seed_terms(query: str, terms: list[str], limit: int = 12, focus: str | None = None) -> list[str]:
    candidates: list[tuple[int, int, str]] = []
    order = 0
    focus = focus or focus_from_query(query)

    def add(priority: int, value: str | None) -> None:
        nonlocal order
        if not value:
            return
        stripped = str(value).strip()
        if not stripped:
            return
        candidates.append((priority, order, stripped))
        order += 1

    def classify_term_priority(term: str) -> int:
        lowered = term.lower()
        query_lowered = query.lower()
        if focus == "route":
            if lowered.startswith("pages/") and not lowered.endswith(".ets"):
                return 130
            if "router" in lowered or "route" in lowered:
                return 125
            if lowered.endswith(".ets"):
                return 78
            if "failed" in lowered or "error" in lowered or "log" in lowered:
                return 68
        if focus == "resource":
            if lowered.startswith("app.") or "$r" in lowered or "resource" in lowered or "media" in lowered or "string" in lowered:
                return 125
            if lowered.startswith("pages/"):
                return 68
        if focus == "config":
            if "权限" in query_lowered and "permission" in lowered:
                return 132
            if "依赖" in query_lowered and "dependency" in lowered:
                return 132
            if "ability" in query_lowered and "ability" in lowered:
                return 132
            if "permission" in lowered:
                return 126
            if "dependency" in lowered:
                return 124
            if "ability" in lowered:
                return 118
            if lowered.endswith(".json5"):
                return 125
            if lowered.startswith("pages/") or lowered.endswith(".ets"):
                return 68
        if focus == "log":
            if "failed" in lowered or "error" in lowered or "warn" in lowered or "log" in lowered or "hilog" in lowered:
                return 125
            if lowered.startswith("pages/") or lowered.endswith(".ets"):
                return 68
        if lowered.startswith("pages/") or lowered.startswith("app.") or "$r" in lowered:
            return 96
        if "/" in lowered or "." in lowered:
            return 92
        if "failed" in lowered or "error" in lowered or "warn" in lowered or "log" in lowered:
            return 88
        if "route" in lowered or "router" in lowered or "resource" in lowered or "hilog" in lowered:
            return 84
        if "profile" in lowered or "load" in lowered or "user" in lowered:
            return 78
        return 70

    for term in terms:
        add(classify_term_priority(str(term)), str(term))

    seen: set[str] = set()
    ranked: list[str] = []
    for _, _, value in sorted(candidates, key=lambda item: (-item[0], item[1])):
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ranked.append(normalized)
        if len(ranked) >= limit:
            break
    return ranked


def suggested_followup_terms(query: str, data: dict[str, list[dict[str, Any]]], limit: int = 12) -> list[str]:
    focus = infer_followup_focus(query, data)
    terms: list[str] = []
    for row in data.get("code_log_matches", [])[:5]:
        if row.get("message_template"):
            terms.append(str(row["message_template"]))
        if row.get("function"):
            terms.append(str(row["function"]))
        if row.get("file_path"):
            terms.append(str(row["file_path"]))
        terms.extend(json_list(row.get("business_terms")))
        terms.extend(row.get("search_terms") or [])

    for row in data.get("wiki_matches", [])[:5]:
        if row.get("symbol"):
            terms.append(str(row["symbol"]))
        if row.get("file_path"):
            terms.append(str(row["file_path"]))
        terms.extend(json_list(row.get("business_terms")))
        terms.extend(row.get("search_terms") or [])

    for row in data.get("semantic_facts", [])[:3]:
        terms.extend(tokenize(str(row.get("fact") or "")))
    for row in data.get("reflections", [])[:2]:
        terms.extend(tokenize(" ".join(str(row.get(key) or "") for key in ("task", "problem", "lesson", "future_rule"))))
    return rank_followup_seed_terms(query, terms, limit=limit, focus=focus)


def limited_context(project: Project, query: str) -> dict[str, Any]:
    matches = collect_matches(project, query)
    bounded = limited_matches(matches, CONTEXT_RESULT_LIMITS)
    followup_focus = infer_followup_focus(query, bounded)
    context = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "query": query,
        "followup_focus": followup_focus,
        "advisory_notice": "Memory is advisory. Current source files and explicit user instructions override stored memory.",
        "semantic_facts": bounded["semantic_facts"],
        "reflections": bounded["reflections"],
        "episodes": bounded["episodes"],
        "wiki_matches": bounded["wiki_matches"],
        "code_log_matches": bounded["code_log_matches"],
        "edge_matches": bounded["edge_matches"],
        "evidence_chains": build_evidence_chains(bounded["edge_matches"]),
        "suggested_followup_terms": suggested_followup_terms(query, bounded),
        "network_limits": network_limits(),
    }
    record_context_use(project, context)
    record_query_miss_if_empty(project, "context", query, context)
    return context


def limited_search(
    project: Project,
    query: str,
    cursor: int = 0,
    per_type_limit: int | None = None,
    aggregate_limit: int | None = None,
) -> dict[str, Any]:
    matches = collect_matches(project, query)
    return batched_search(matches, query=query, cursor=cursor, per_type_limit=per_type_limit, aggregate_limit=aggregate_limit)


def batched_search(
    matches: dict[str, list[dict[str, Any]]],
    query: str = "",
    cursor: int = 0,
    per_type_limit: int | None = None,
    aggregate_limit: int | None = None,
) -> dict[str, Any]:
    effective_per_type_limit = max(1, per_type_limit or max(SEARCH_RESULT_LIMITS.values()))
    effective_aggregate_limit = max(1, aggregate_limit or sum(SEARCH_RESULT_LIMITS.values()))
    safe_cursor = max(0, cursor)
    followup_focus = infer_followup_focus(query, matches)

    candidates: list[dict[str, Any]] = []
    total_candidates_by_type: dict[str, int] = {}
    for key, items in matches.items():
        total_candidates_by_type[key] = len(items)
        window_size = min(len(items), safe_cursor + effective_per_type_limit)
        for item in items[:window_size]:
            candidate = dict(item)
            candidate["_match_type"] = key
            candidates.append(candidate)

    candidates.sort(key=lambda item: (item.get("score", 0), item.get("created_at", ""), item.get("id", 0)), reverse=True)
    visible = candidates[safe_cursor : safe_cursor + effective_aggregate_limit]
    next_cursor = safe_cursor + len(visible) if safe_cursor + len(visible) < len(candidates) else None

    payload: dict[str, list[dict[str, Any]]] = {key: [] for key in matches}
    returned_counts_by_type: dict[str, int] = {key: 0 for key in matches}
    for item in visible:
        item_type = str(item.pop("_match_type"))
        returned_counts_by_type[item_type] += 1
        payload[item_type].append(item)

    payload["result_limits"] = SEARCH_RESULT_LIMITS.copy()
    payload["cursor"] = safe_cursor
    payload["per_type_limit"] = effective_per_type_limit
    payload["aggregate_limit"] = effective_aggregate_limit
    payload["followup_focus"] = followup_focus
    payload["truncated"] = next_cursor is not None
    payload["next_cursor"] = next_cursor
    payload["total_candidates_by_type"] = total_candidates_by_type
    payload["returned_counts_by_type"] = returned_counts_by_type
    payload["suggested_followup_terms"] = suggested_followup_terms(query, payload)
    return payload


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
