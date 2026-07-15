# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable
from typing import Sequence

from .path_context_models import ExpectedLogAnchor, PathBounds, PathCandidate, RawPath


EVIDENCE_WEIGHTS = {"exact": 1.0, "static": 0.85, "heuristic": 0.5, "inferred": 0.3}
RELATION_SPECIFICITY = {
    "awaits": 1.0,
    "registers_callback": 0.95,
    "handles_callback": 0.95,
    "dispatches_event": 0.9,
    "handles_event": 0.9,
    "routes_to": 0.85,
    "calls": 0.7,
    "uses_service": 0.6,
}


class StructuralCallPathRankingPolicy:
    """Rank only graph structure and provenance; memory is intentionally absent."""

    def rank(
        self,
        paths: Sequence[RawPath],
        expected_logs: dict[str, tuple[ExpectedLogAnchor, ...]],
        bounds: PathBounds,
    ) -> Sequence[PathCandidate]:
        candidates = deduplicate_candidates([build_candidate(path, expected_logs) for path in paths])
        candidates.sort(
            key=lambda item: (
                item.structural_score,
                item.raw_path.complete,
                -len(item.raw_path.edges),
                item.path_id,
            ),
            reverse=True,
        )
        selected: list[PathCandidate] = []
        entry_counts: dict[str, int] = defaultdict(int)
        seeds_with_known_entries = {
            item.raw_path.seed.seed_id
            for item in candidates
            if item.raw_path.entry.category != "unknown_entry"
        }
        for candidate in candidates:
            if (
                candidate.raw_path.entry.category == "unknown_entry"
                and candidate.raw_path.seed.seed_id in seeds_with_known_entries
            ):
                continue
            entry_key = candidate.raw_path.nodes[0].ref.key
            if entry_counts[entry_key] >= bounds.max_same_entry_paths:
                continue
            selected.append(candidate)
            entry_counts[entry_key] += 1
            if len(selected) >= bounds.max_returned_paths:
                break
        return tuple(selected)


def build_candidate(
    path: RawPath,
    expected_logs: dict[str, tuple[ExpectedLogAnchor, ...]],
) -> PathCandidate:
    evidence = edge_evidence_score(path)
    confidence = sum(edge.confidence for edge in path.edges) / max(1, len(path.edges))
    compactness = 1.0 / (1.0 + max(0, len(path.edges) - 1) * 0.12)
    relation_specificity = edge_relation_specificity(path)
    completeness = 1.0 if path.complete else 0.35
    ambiguity_penalty = sum(bool(edge.ambiguity) for edge in path.edges) / max(1, len(path.edges))
    truncation_penalty = 0.2 if path.truncated else 0.0
    score = (
        0.24 * evidence
        + 0.18 * confidence
        + 0.2 * path.entry.score
        + 0.12 * compactness
        + 0.12 * completeness
        + 0.14 * relation_specificity
        - 0.15 * ambiguity_penalty
        - truncation_penalty
    )
    logs = deduplicate_logs(
        item
        for node in path.nodes
        for item in expected_logs.get(node.ref.key, ())
    )
    uncertainty = []
    if not path.complete:
        uncertainty.append("entry point is not present in the current graph")
    if path.truncated:
        uncertainty.append("search stopped at a configured resource bound")
    if ambiguity_penalty:
        uncertainty.append("one or more graph edges have ambiguous targets")
    missing = () if path.complete else (path.entry.reason,)
    return PathCandidate(
        path_id=path_identity(path),
        raw_path=path,
        structural_score=max(0.0, min(1.0, score)),
        score_components={
            "edge_evidence": round(evidence, 3),
            "edge_confidence": round(confidence, 3),
            "entry_point": round(path.entry.score, 3),
            "compactness": round(compactness, 3),
            "relation_specificity": round(relation_specificity, 3),
            "completeness": round(completeness, 3),
            "ambiguity_penalty": round(ambiguity_penalty, 3),
            "truncation_penalty": round(truncation_penalty, 3),
        },
        expected_logs=logs,
        uncertainty=tuple(uncertainty),
        missing_segments=missing,
    )


def edge_evidence_score(path: RawPath) -> float:
    if not path.edges:
        return 1.0
    return sum(EVIDENCE_WEIGHTS.get(edge.evidence_class, 0.25) for edge in path.edges) / len(path.edges)


def edge_relation_specificity(path: RawPath) -> float:
    if not path.edges:
        return 0.5
    return sum(RELATION_SPECIFICITY.get(edge.relation, 0.5) for edge in path.edges) / len(path.edges)


def deduplicate_candidates(candidates: list[PathCandidate]) -> list[PathCandidate]:
    selected: dict[tuple[str, tuple[str, ...]], PathCandidate] = {}
    for candidate in candidates:
        path = candidate.raw_path
        key = (path.seed.seed_id, tuple(node.ref.key for node in path.nodes))
        current = selected.get(key)
        if current is None or candidate.structural_score > current.structural_score:
            selected[key] = candidate
    return list(selected.values())


def path_identity(path: RawPath) -> str:
    source = f"{path.seed.seed_id}|{'|'.join(node.ref.key for node in path.nodes)}"
    return "path_" + hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def deduplicate_logs(items: Iterable[ExpectedLogAnchor]) -> tuple[ExpectedLogAnchor, ...]:
    result: dict[int, ExpectedLogAnchor] = {}
    for item in items:
        result[item.log_id] = item
    return tuple(result.values())
