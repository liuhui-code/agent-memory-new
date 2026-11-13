# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any

from .models import Project
from .records import row_dict
from .query_language import positive_retrieval_query
from .storage import connect
from .text import code_search_terms, json_list


INDIRECT_PATH_RE = re.compile(
    r"(?:controller|helper|adapter|bridge|service|repository)(?:\.[^.]+)?$",
    re.I,
)
CALLER_QUERY_MARKERS = (
    "actual caller", "caller context", "call site", "click owner",
    "button callback", "onclick", "调用方", "调用位置", "点击所有者",
)
CALLER_RELATIONS = ("calls", "awaits", "registers_callback")
MAX_SEED_PATHS = 4
MAX_CALLER_OWNERS = 2


def collect_bounded_caller_owners(
    project: Project,
    matches: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    if not caller_owner_query(query):
        return []
    seed_scores = indirect_seed_scores(matches)
    if not seed_scores:
        return []
    paths = list(seed_scores)
    placeholders = ",".join("?" for _ in paths)
    relation_placeholders = ",".join("?" for _ in CALLER_RELATIONS)
    with connect(project) as conn:
        targets = conn.execute(
            f"SELECT id, file_path, symbol, owner_name FROM code_symbols "
            f"WHERE project_id = ? AND file_path IN ({placeholders})",
            (project.project_id, *paths),
        ).fetchall()
        def resolve_member(reference):
            owner, _, symbol = reference.rpartition(".")
            # Seed truncation is not identity disambiguation. Two project-wide
            # matches suffice to reject an ambiguous qualified member.
            return conn.execute(
                "SELECT id FROM code_symbols WHERE project_id = ? "
                "AND owner_name = ? AND symbol = ? LIMIT 2",
                (project.project_id, owner, symbol),
            ).fetchall()
        target_ids = explicit_caller_target_ids(targets, query, resolve_member)
        if target_ids == []:
            return []
        target_filter = ""
        target_params = []
        if target_ids is not None:
            target_filter = " AND targets.id IN (" + ",".join("?" for _ in target_ids) + ")"
            target_params = target_ids
        rows = conn.execute(
            f"""
            SELECT callers.*, files.summary AS caller_file_summary,
                   MAX(edges.confidence) AS caller_confidence,
                   GROUP_CONCAT(DISTINCT edges.relation) AS caller_relations
            FROM code_symbols AS targets
            JOIN memory_edges AS edges
              ON edges.project_id = targets.project_id
             AND edges.target_type = 'code_symbol'
             AND edges.target_id = targets.id
             AND edges.valid_to IS NULL
            JOIN code_symbols AS callers
              ON edges.source_type = 'code_symbol'
             AND callers.project_id = edges.project_id
             AND callers.id = edges.source_id
            JOIN code_files AS files
              ON files.project_id = callers.project_id
             AND files.file_path = callers.file_path
            WHERE targets.project_id = ?
              AND targets.file_path IN ({placeholders})
              AND edges.relation IN ({relation_placeholders})
              {target_filter}
              AND callers.file_path != targets.file_path
              AND files.summary LIKE '%uicallbackbinding%'
            GROUP BY callers.id
            ORDER BY caller_confidence DESC, callers.id DESC
            LIMIT 12
            """,
            (project.project_id, *paths, *CALLER_RELATIONS, *target_params),
        ).fetchall()
    return caller_items(rows, seed_scores)


def caller_owner_query(query: str) -> bool:
    lowered = query.casefold()
    return any(marker in lowered for marker in CALLER_QUERY_MARKERS)


def indirect_seed_scores(
    matches: list[dict[str, Any]],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for item in matches:
        path = str(item.get("file_path") or "")
        if not path or item.get("graph_depth") or not INDIRECT_PATH_RE.search(path):
            continue
        scores[path] = max(scores.get(path, 0.0), float(item.get("score") or 0.0))
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return dict(ranked[:MAX_SEED_PATHS])


def caller_items(
    rows: list[Any],
    seed_scores: dict[str, float],
) -> list[dict[str, Any]]:
    seed_score = max(seed_scores.values(), default=0.0)
    selected: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for row in rows:
        item = row_dict(row)
        path = str(item.get("file_path") or "")
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        file_summary = str(item.pop("caller_file_summary", "") or "")
        confidence = float(item.pop("caller_confidence", 0.0) or 0.0)
        relations = str(item.pop("caller_relations", "") or "")
        item["kind"] = "symbol"
        item["score"] = round(seed_score * 0.9 + confidence * 5.0, 3)
        item["summary"] = f"{item.get('summary') or ''} {file_summary}".strip()
        item["business_terms"] = json_list(item.get("business_terms"))
        item["search_terms"] = code_search_terms("symbol", item)
        item["match_reasons"] = [
            "graph_neighbor", "graph_relation:caller_owner", "caller_owner",
        ]
        item["graph_depth"] = 1
        item["caller_relations"] = relations.split(",") if relations else []
        selected.append(item)
        if len(selected) >= MAX_CALLER_OWNERS:
            break
    return selected


def explicit_caller_target_ids(targets, query, resolve_member=None):
    """Bind a qualified caller-of target to symbol IDs, not its whole file.

    Only an explicit English caller-of/for target clause is resolved here; generic
    and unknown request forms retain the old bounded file-seed behavior. A resolved
    clause with an unknown/ambiguous member grants no unrelated caller authority.
    """
    positive = positive_retrieval_query(query)
    if re.search(r"[\"']", positive):
        return None  # Do not treat quoted message text as a relation target.
    target_token = re.compile(r"`?([A-Za-z_$][\w$]*(?:[./][A-Za-z_$][\w$]*)+)`?")
    references = set()
    for clause in re.finditer(
        r"\b(?:actual callers?|caller context|call sites?)\s+(?:of|for)\s+(?:the\s+)?",
        positive, re.IGNORECASE,
    ):
        cursor = clause.end()
        while True:
            token = target_token.match(positive, cursor)
            if token is None:
                break
            references.add(token.group(1))
            separator = re.match(r"\s*(?:,|and)\s+", positive[token.end():])
            if separator is None:
                break
            cursor = token.end() + separator.end()
    if not references:
        return None
    selected = set()
    for reference in references:
        files = [row for row in targets if row["file_path"] == reference]
        if files:
            selected.update(int(row["id"]) for row in files)
            continue
        matches = (resolve_member(reference) if resolve_member is not None else
                   [row for row in targets if row["owner_name"] and
                    f'{row["owner_name"]}.{row["symbol"]}' == reference])
        if len(matches) == 1:
            selected.add(int(matches[0]["id"]))
    return sorted(selected)
