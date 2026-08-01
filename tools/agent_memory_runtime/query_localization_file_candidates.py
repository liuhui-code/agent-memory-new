# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from .query_behavior_concepts import behavior_marker_terms
from .text import terms_from_text, unique_list


MAX_FILES_PER_DIRECTORY = 2
MAX_STRUCTURAL_FILE_RESERVATIONS = 3
MAX_IDENTITY_FILE_RESERVATIONS = 3
IDENTITY_REASONS = {
    "exact_file_path",
    "exact_identifier",
    "exact_path_segment",
    "exact_symbol",
}


def select_file_candidates(
    items: list[dict[str, Any]],
    limit: int,
    query: str,
) -> list[dict[str, Any]]:
    """Blend heterogeneous evidence into a bounded file candidate set."""
    behavior_markers = set(behavior_marker_terms(query))
    ordered = grouped_file_candidates(items, behavior_markers)
    if limit <= 0:
        return []
    behavior_query = bool(behavior_markers)
    identity = identity_reservations(ordered, limit) if behavior_query else []
    reserved = structural_reservations(ordered, behavior_query, limit)
    selected, deferred = select_with_directory_limit(
        [*identity, *reserved, *ordered],
        limit,
    )
    if len(selected) < limit:
        selected.extend(deferred[: limit - len(selected)])
    selected_paths = {str(item["file_path"]) for item in selected[:limit]}
    return [item for item in ordered if str(item["file_path"]) in selected_paths]


def grouped_file_candidates(
    items: list[dict[str, Any]],
    behavior_markers: set[str],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for rank, item in enumerate(items, start=1):
        if item.get("kind") not in {"file", "symbol"} or item.get("graph_depth"):
            continue
        path = str(item.get("file_path") or "")
        if not path:
            continue
        candidate = grouped.setdefault(path, new_file_candidate(path, rank))
        merge_file_candidate(candidate, item, rank, behavior_markers)
    return sorted(
        grouped.values(),
        key=lambda item: (
            -float(item["score"]),
            int(item["first_rank"]),
            str(item["file_path"]),
        ),
    )


def new_file_candidate(path: str, rank: int) -> dict[str, Any]:
    return {
        "file_path": path,
        "score": 0.0,
        "first_rank": rank,
        "record_ids": [],
        "direct_symbol_ids": [],
        "match_reasons": [],
        "recall_lanes": [],
        "structural_coverage": 0,
    }


def merge_file_candidate(
    candidate: dict[str, Any],
    item: dict[str, Any],
    rank: int,
    behavior_markers: set[str],
) -> None:
    score = float(item.get("score") or 0.0)
    candidate["score"] = max(float(candidate["score"]), score)
    candidate["first_rank"] = min(int(candidate["first_rank"]), rank)
    record_id = int(item.get("id") or 0)
    if record_id > 0 and record_id not in candidate["record_ids"]:
        candidate["record_ids"].append(record_id)
    if (
        item.get("kind") == "symbol"
        and record_id > 0
        and record_id not in candidate["direct_symbol_ids"]
    ):
        candidate["direct_symbol_ids"].append(record_id)
    candidate["match_reasons"] = unique_list([
        *candidate["match_reasons"],
        *(str(value) for value in item.get("match_reasons") or []),
    ])
    candidate["recall_lanes"] = unique_list([
        *candidate["recall_lanes"],
        *(str(value) for value in item.get("recall_lanes") or []),
    ])
    candidate["structural_coverage"] = max(
        int(candidate["structural_coverage"]),
        structural_coverage(item, behavior_markers),
    )


def structural_coverage(
    item: dict[str, Any],
    behavior_markers: set[str],
) -> int:
    reasons = {str(value) for value in item.get("match_reasons") or []}
    if not reasons & {"semantic_behavior", "structural_behavior"}:
        return 0
    evidence = " ".join(str(item.get(key) or "") for key in (
        "file_path",
        "summary",
        "method_evidence",
    ))
    indexed = {term.casefold() for term in terms_from_text(evidence)}
    marker_coverage = len(behavior_markers & indexed)
    return max(
        marker_coverage,
        int(item.get("semantic_behavior_coverage") or 0),
    )


def structural_reservations(
    ordered: list[dict[str, Any]],
    behavior_query: bool,
    limit: int,
) -> list[dict[str, Any]]:
    if not behavior_query:
        return []
    candidates = [
        item for item in ordered
        if int(item.get("structural_coverage") or 0) > 0
    ]
    candidates.sort(key=lambda item: (
        -int(item["structural_coverage"]),
        -float(item["score"]),
        int(item["first_rank"]),
        str(item["file_path"]),
    ))
    return candidates[: min(limit, MAX_STRUCTURAL_FILE_RESERVATIONS)]


def identity_reservations(
    ordered: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    candidates = [
        item for item in ordered
        if IDENTITY_REASONS & set(item.get("match_reasons") or [])
    ]
    return candidates[: min(limit, MAX_IDENTITY_FILE_RESERVATIONS)]


def select_with_directory_limit(
    items: list[dict[str, Any]],
    limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    selected_paths: set[str] = set()
    deferred_paths: set[str] = set()
    directories: dict[str, int] = {}
    for item in items:
        path = str(item["file_path"])
        if path in selected_paths or path in deferred_paths:
            continue
        directory = str(PurePosixPath(path).parent)
        if directories.get(directory, 0) >= MAX_FILES_PER_DIRECTORY:
            deferred.append(item)
            deferred_paths.add(path)
            continue
        selected.append(item)
        selected_paths.add(path)
        directories[directory] = directories.get(directory, 0) + 1
        if len(selected) >= limit:
            break
    return selected, deferred
