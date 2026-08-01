# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Project
from .query_fielded_retrieval import (
    fielded_passage_rankings,
    passage_candidate_refs,
)
from .query_method_evidence import (
    method_evidence_focus_terms,
    qualifying_method_evidence_ids,
)
from .query_rank_fusion import RankFusionPort


LEGACY_SERVING_CHANNELS = {"method_body_fts"}


@dataclass(frozen=True)
class FieldedServingCandidates:
    lanes: dict[str, list[int]]
    audit: dict[str, Any]


def fielded_serving_candidates(
    conn: Any,
    project: Project,
    query: str,
    limit: int,
    source_type: str | None,
    rank_fusion: RankFusionPort,
) -> FieldedServingCandidates:
    if not source_type:
        return FieldedServingCandidates({}, {})
    fielded = fielded_passage_rankings(conn, project, query, limit, source_type)
    qualify_method_body(conn, project, query, source_type, fielded.rankings)
    fused = rank_fusion.fuse(fielded.rankings, limit)
    ordered = [item.record_id for item in fused.candidates]
    lanes = {
        channel: ids
        for channel, ids in fielded.rankings.items()
        if channel not in LEGACY_SERVING_CHANNELS
    }
    return FieldedServingCandidates(lanes, {
        **fielded.audit,
        "mode": "serving",
        "serving_candidates_changed": False,
        "serving_channels": sorted(lanes),
        "rank_fusion": fused.audit(),
        "candidate_fusion": {
            str(item.record_id): item.audit() for item in fused.candidates
        },
        "candidate_refs": passage_candidate_refs(
            conn, project, source_type, ordered, fielded.rankings
        ),
    })


def qualify_method_body(
    conn: Any,
    project: Project,
    query: str,
    source_type: str,
    rankings: dict[str, list[int]],
) -> None:
    if source_type != "code_symbol":
        return
    terms = method_evidence_focus_terms(query)
    candidates = rankings.get("method_body_fts", [])
    rankings["method_body_fts"] = (
        qualifying_method_evidence_ids(conn, project, candidates, terms)
        if len(terms) >= 2 else []
    )
