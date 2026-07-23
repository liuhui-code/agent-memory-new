from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import PurePosixPath
from typing import Any, Protocol

from .models import Project
from .query_behavior_concepts import behavior_marker_terms
from .query_hierarchical_owners import load_one_hop_owners
from .records import row_dict
from .storage import connect
from .text import json_list, query_tokens, score_weighted_fields, unique_list


CALLABLE_TYPES = ("function", "method")
MAX_FILES = 8
MAX_FILES_PER_DIRECTORY = 2
MAX_FILE_CALLABLE_POOL = 128
MAX_GRAPH_SEEDS = 6
MAX_GRAPH_OWNERS = 16
MAX_CALLABLES = 12
MAX_CALLABLES_PER_FILE = 2
MAX_SOURCE_RANGES = 8
EXPRESSION_RADIUS = 2


class HierarchicalLocalizerPort(Protocol):
    def localize(
        self,
        project: Project,
        query: str,
        matches: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class SQLiteHierarchicalLocalizer:
    """Bounded shadow locator: fused files -> callables -> evidence ranges."""

    def localize(
        self,
        project: Project,
        query: str,
        matches: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        files = select_file_candidates(matches.get("wiki_matches") or [], MAX_FILES)
        if not files:
            return empty_localization()
        direct_symbols = direct_symbol_candidates(matches.get("wiki_matches") or [], files)
        rows = load_file_callables(project, [item["file_path"] for item in files])
        candidates = attach_candidate_metadata(rows, files, direct_symbols)
        initial = rank_callables(candidates, query)
        graph_seeds = select_graph_seeds(initial, MAX_GRAPH_SEEDS)
        owners = load_one_hop_owners(
            project, [item["id"] for item in graph_seeds], MAX_GRAPH_OWNERS,
        )
        ranked = rank_callables([*candidates, *owners], query)
        selected = select_diverse_callables(ranked, MAX_CALLABLES)
        ranges = valid_source_ranges(selected, query)
        return {
            "schema_version": "agent-hierarchical-localization/v1",
            "provider": "sqlite_hierarchical_localizer/v1",
            "mode": "shadow",
            "serving_candidates_changed": False,
            "limits": localization_limits(),
            "stage_counts": {
                "file_candidates": len(files),
                "file_callable_pool": len(candidates),
                "graph_seed_count": len(graph_seeds),
                "graph_owner_pool": len(owners),
                "selected_callables": len(selected),
                "selected_ranges": len(ranges),
            },
            "file_candidates": files,
            "graph_seeds": [compact_callable(item) for item in graph_seeds],
            "graph_owner_candidates": [compact_callable(item) for item in owners],
            "callable_candidates": [compact_callable(item) for item in selected],
            "source_ranges": ranges,
        }


def empty_localization() -> dict[str, Any]:
    return {
        "schema_version": "agent-hierarchical-localization/v1",
        "provider": "sqlite_hierarchical_localizer/v1",
        "mode": "shadow",
        "serving_candidates_changed": False,
        "limits": localization_limits(),
        "stage_counts": {
            "file_candidates": 0,
            "file_callable_pool": 0,
            "graph_seed_count": 0,
            "graph_owner_pool": 0,
            "selected_callables": 0,
            "selected_ranges": 0,
        },
        "file_candidates": [],
        "graph_seeds": [],
        "graph_owner_candidates": [],
        "callable_candidates": [],
        "source_ranges": [],
    }


def localization_limits() -> dict[str, int]:
    return {
        "files": MAX_FILES,
        "file_callable_pool": MAX_FILE_CALLABLE_POOL,
        "graph_seeds": MAX_GRAPH_SEEDS,
        "graph_owners": MAX_GRAPH_OWNERS,
        "callables": MAX_CALLABLES,
        "source_ranges": MAX_SOURCE_RANGES,
    }


def select_file_candidates(
    items: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for rank, item in enumerate(items, start=1):
        if item.get("kind") not in {"file", "symbol"} or item.get("graph_depth"):
            continue
        path = str(item.get("file_path") or "")
        if not path:
            continue
        candidate = grouped.setdefault(path, {
            "file_path": path,
            "score": 0.0,
            "first_rank": rank,
            "record_ids": [],
            "direct_symbol_ids": [],
            "match_reasons": [],
            "recall_lanes": [],
        })
        score = float(item.get("score") or 0.0)
        candidate["score"] = max(float(candidate["score"]), score)
        candidate["first_rank"] = min(int(candidate["first_rank"]), rank)
        record_id = int(item.get("id") or 0)
        if record_id > 0 and record_id not in candidate["record_ids"]:
            candidate["record_ids"].append(record_id)
        if item.get("kind") == "symbol" and record_id > 0:
            candidate["direct_symbol_ids"].append(record_id)
        candidate["match_reasons"] = unique_list([
            *candidate["match_reasons"],
            *(str(value) for value in item.get("match_reasons") or []),
        ])
        candidate["recall_lanes"] = unique_list([
            *candidate["recall_lanes"],
            *(str(value) for value in item.get("recall_lanes") or []),
        ])
    ordered = sorted(
        grouped.values(),
        key=lambda item: (-float(item["score"]), int(item["first_rank"]), item["file_path"]),
    )
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    directories: dict[str, int] = {}
    for item in ordered:
        directory = str(PurePosixPath(item["file_path"]).parent)
        if directories.get(directory, 0) >= MAX_FILES_PER_DIRECTORY:
            deferred.append(item)
            continue
        selected.append(item)
        directories[directory] = directories.get(directory, 0) + 1
        if len(selected) >= limit:
            return selected
    selected.extend(deferred[: max(0, limit - len(selected))])
    return selected[:limit]


def direct_symbol_candidates(
    items: list[dict[str, Any]],
    files: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    allowed_paths = {str(item["file_path"]) for item in files}
    result: dict[int, dict[str, Any]] = {}
    for item in items:
        if item.get("kind") != "symbol" or item.get("graph_depth"):
            continue
        record_id = int(item.get("id") or 0)
        if record_id <= 0 or str(item.get("file_path") or "") not in allowed_paths:
            continue
        result[record_id] = item
    return result


def load_file_callables(project: Project, file_paths: list[str]) -> list[dict[str, Any]]:
    if not file_paths:
        return []
    placeholders = ",".join("?" for _ in file_paths)
    type_placeholders = ",".join("?" for _ in CALLABLE_TYPES)
    with connect(project) as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM code_symbols
            WHERE project_id = ? AND file_path IN ({placeholders})
              AND symbol_type IN ({type_placeholders})
            ORDER BY file_path, start_line, id
            LIMIT ?
            """,
            (project.project_id, *file_paths, *CALLABLE_TYPES, MAX_FILE_CALLABLE_POOL),
        ).fetchall()
    return [row_dict(row) for row in rows]


def attach_candidate_metadata(
    rows: list[dict[str, Any]],
    files: list[dict[str, Any]],
    direct_symbols: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    file_ranks = {str(item["file_path"]): index for index, item in enumerate(files, start=1)}
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        direct = direct_symbols.get(int(item["id"]))
        item["file_rank"] = file_ranks.get(str(item.get("file_path") or ""), MAX_FILES + 1)
        item["direct_score"] = float(direct.get("score") or 0.0) if direct else 0.0
        item["direct_match_reasons"] = list(direct.get("match_reasons") or []) if direct else []
        item["direct_recall_lanes"] = list(direct.get("recall_lanes") or []) if direct else []
        item["graph_depth"] = 0
        result.append(item)
    return result


def select_graph_seeds(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_ids: set[int] = set()
    evidence_first = [
        item for item in items
        if float(item.get("direct_score") or 0.0) > 0 or item.get("mechanism_hits")
        or "exact_symbol" in (item.get("localization_reasons") or [])
    ]
    evidence_first.sort(key=graph_seed_priority)
    for item in [*evidence_first, *items]:
        record_id = int(item.get("id") or 0)
        if record_id <= 0 or record_id in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(record_id)
        if len(selected) >= limit:
            break
    return selected


def graph_seed_priority(item: dict[str, Any]) -> tuple[float, int, int, float, int]:
    reasons = set(item.get("localization_reasons") or [])
    return (
        -float(item.get("direct_score") or 0.0),
        -int("exact_symbol" in reasons),
        -len(item.get("mechanism_hits") or []),
        -float(item.get("localization_score") or 0.0),
        int(item.get("id") or 0),
    )


def rank_callables(items: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    terms = query_tokens(query)
    expanded_terms = set(terms)
    scored: list[dict[str, Any]] = []
    for item in dedupe_callables(items):
        lexical, reasons = score_weighted_fields(
            query,
            terms,
            expanded_terms,
            [
                ("symbol", str(item.get("symbol") or ""), 4.0),
                ("business_terms", " ".join(json_list(item.get("business_terms"))), 4.0),
                ("business_summary", str(item.get("business_summary") or ""), 3.0),
                ("summary", str(item.get("summary") or ""), 1.5),
                ("method_evidence", str(item.get("method_evidence") or ""), 2.0),
                ("string_evidence", str(item.get("string_evidence") or ""), 2.5),
            ],
            [("exact_symbol", str(item.get("symbol") or ""), 12.0)],
        )
        mechanism_hits = matching_mechanisms(item.get("mechanism_evidence"), query)
        score = lexical + min(9.0, float(item.get("direct_score") or 0.0) * 0.18)
        score += max(0, MAX_FILES + 1 - int(item.get("file_rank") or MAX_FILES + 1))
        if mechanism_hits:
            score += min(9.0, 3.0 * len(mechanism_hits[0]["matched_terms"]))
            reasons.append("semantic_mechanism")
        if item.get("graph_depth"):
            score += 3.0 + float(item.get("graph_confidence") or 0.0) * 3.0
            reasons.extend(f"graph_owner:{value}" for value in item.get("graph_relations") or [])
        if item.get("start_line") and item.get("end_line"):
            score += 0.5
            reasons.append("source_locatable")
        item["localization_score"] = round(score, 3)
        item["localization_reasons"] = unique_list([
            *reasons,
            *(str(value) for value in item.get("direct_match_reasons") or []),
        ])
        item["mechanism_hits"] = mechanism_hits
        scored.append(item)
    return sorted(
        scored,
        key=lambda item: (
            -float(item["localization_score"]),
            int(item.get("graph_depth") or 0),
            str(item.get("file_path") or ""),
            int(item.get("start_line") or 0),
            int(item.get("id") or 0),
        ),
    )


def dedupe_callables(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chosen: dict[int, dict[str, Any]] = {}
    for item in items:
        record_id = int(item.get("id") or 0)
        if record_id <= 0:
            continue
        current = chosen.get(record_id)
        if current is None or int(item.get("graph_depth") or 0) < int(current.get("graph_depth") or 0):
            chosen[record_id] = item
    return list(chosen.values())


def select_diverse_callables(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    path_counts: dict[str, int] = {}
    for item in items:
        path = str(item.get("file_path") or "")
        if path_counts.get(path, 0) >= MAX_CALLABLES_PER_FILE:
            deferred.append(item)
            continue
        selected.append(item)
        path_counts[path] = path_counts.get(path, 0) + 1
        if len(selected) >= limit:
            return selected
    selected.extend(deferred[: max(0, limit - len(selected))])
    return selected[:limit]


def matching_mechanisms(payload: Any, query: str) -> list[dict[str, Any]]:
    try:
        records = json.loads(str(payload or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(records, list):
        return []
    expected = set(query_tokens(query)) | set(behavior_marker_terms(query))
    matches: list[dict[str, Any]] = []
    for item in records:
        if not isinstance(item, dict) or not isinstance(item.get("line"), int):
            continue
        kind = str(item.get("kind") or "")
        terms = {kind, kind.replace("_", "")}
        terms.update(str(value) for value in item.get("terms") or [] if str(value))
        matched = sorted(expected & {value.casefold() for value in terms})
        if matched:
            matches.append({
                "line": int(item["line"]),
                "kind": kind,
                "matched_terms": matched,
                "detail": str(item.get("detail") or ""),
            })
    return sorted(matches, key=lambda item: (-len(item["matched_terms"]), item["line"], item["kind"]))


def compact_callable(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol_id": item.get("id"),
        "file_path": item.get("file_path"),
        "symbol": item.get("symbol"),
        "qualified_name": item.get("qualified_name"),
        "start_line": item.get("start_line"),
        "end_line": item.get("end_line"),
        "score": item.get("localization_score"),
        "reasons": item.get("localization_reasons") or [],
        "graph_depth": item.get("graph_depth"),
        "graph_relations": item.get("graph_relations") or [],
        "recall_lanes": item.get("direct_recall_lanes") or [],
    }


def source_range(item: dict[str, Any], query: str) -> dict[str, Any]:
    start = int(item.get("start_line") or 0)
    end = int(item.get("end_line") or 0)
    base = {
        "symbol_id": item.get("id"),
        "file_path": item.get("file_path"),
        "symbol": item.get("symbol"),
        "callable_start_line": start,
        "callable_end_line": end,
    }
    hits = matching_mechanisms(item.get("mechanism_evidence"), query)
    if hits and start > 0 and end >= start:
        hit = hits[0]
        line = min(end, max(start, int(hit["line"])))
        return {
            **base,
            "start_line": max(start, line - EXPRESSION_RADIUS),
            "end_line": min(end, line + EXPRESSION_RADIUS),
            "selection_reason": "semantic_mechanism_window",
            "mechanism_kind": hit["kind"],
            "mechanism_terms": hit["matched_terms"],
        }
    return {
        **base,
        "start_line": start,
        "end_line": end,
        "selection_reason": "callable_symbol_range",
    }


def valid_source_ranges(items: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    for item in items:
        candidate = source_range(item, query)
        start = int(candidate.get("start_line") or 0)
        end = int(candidate.get("end_line") or 0)
        if start <= 0 or end < start:
            continue
        ranges.append(candidate)
        if len(ranges) >= MAX_SOURCE_RANGES:
            break
    return ranges
