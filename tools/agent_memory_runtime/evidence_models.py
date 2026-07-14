# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class GoalPlan:
    goal: str
    query: str
    query_scope: str
    subqueries: tuple[str, ...]
    retrieval_lanes: tuple[str, ...]
    source_weights: dict[str, float]
    required_evidence: tuple[str, ...]
    max_items: int = 20
    max_rounds: int = 3
    novelty_threshold: float = 0.15

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["retrieval_lanes"] = list(self.retrieval_lanes)
        data["subqueries"] = list(self.subqueries)
        data["required_evidence"] = list(self.required_evidence)
        return data


@dataclass
class EvidenceItem:
    evidence_id: str
    source: str
    kind: str
    record_id: int | None
    title: str
    summary: str
    location: str | None
    authority: str
    original_score: float
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)
    score_components: dict[str, float] = field(default_factory=dict)
    penalties: dict[str, float] = field(default_factory=dict)
    final_score: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw", None)
        data["original_score"] = round(self.original_score, 3)
        data["final_score"] = round(self.final_score, 3)
        data["score_components"] = {
            key: round(value, 3) for key, value in self.score_components.items()
        }
        data["penalties"] = {
            key: round(value, 3) for key, value in self.penalties.items() if value
        }
        return data
