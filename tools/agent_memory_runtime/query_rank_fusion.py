# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence


@dataclass(frozen=True)
class RankContribution:
    channel: str
    rank: int
    weight: float
    score: float

    def audit(self) -> dict[str, object]:
        return {
            "channel": self.channel,
            "rank": self.rank,
            "weight": self.weight,
            "score": round(self.score, 8),
        }


@dataclass(frozen=True)
class FusedCandidate:
    record_id: int
    score: float
    best_rank: int
    contributions: tuple[RankContribution, ...]

    def audit(self) -> dict[str, object]:
        return {
            "provider": "reciprocal_rank_fusion/v1",
            "score": round(self.score, 8),
            "best_rank": self.best_rank,
            "channel_count": len(self.contributions),
            "contributions": [item.audit() for item in self.contributions],
        }


@dataclass(frozen=True)
class RankFusionBatch:
    provider: str
    candidates: tuple[FusedCandidate, ...]
    channel_counts: dict[str, int]
    rank_constant: int

    def audit(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "rank_constant": self.rank_constant,
            "channel_count": len(self.channel_counts),
            "channel_counts": dict(self.channel_counts),
            "fused_candidate_count": len(self.candidates),
        }


class RankFusionPort(Protocol):
    def fuse(
        self,
        rankings: Mapping[str, Sequence[int]],
        limit: int,
    ) -> RankFusionBatch:
        ...


class ReciprocalRankFusion:
    """Fuse bounded rankings without comparing channel-local raw scores."""

    provider = "reciprocal_rank_fusion/v1"

    def __init__(
        self,
        rank_constant: int = 60,
        channel_weights: Mapping[str, float] | None = None,
        default_weight: float = 1.0,
    ) -> None:
        if rank_constant < 1:
            raise ValueError("rank_constant must be positive")
        if default_weight <= 0:
            raise ValueError("default_weight must be positive")
        self.rank_constant = rank_constant
        self.channel_weights = dict(channel_weights or {})
        self.default_weight = default_weight

    def fuse(
        self,
        rankings: Mapping[str, Sequence[int]],
        limit: int,
    ) -> RankFusionBatch:
        channel_counts = {
            channel: len(unique_ids(record_ids))
            for channel, record_ids in rankings.items()
        }
        if limit <= 0:
            return RankFusionBatch(
                self.provider, (), channel_counts, self.rank_constant
            )

        contributions: dict[int, list[RankContribution]] = {}
        first_positions: dict[int, tuple[int, int]] = {}
        for channel_index, (channel, record_ids) in enumerate(rankings.items()):
            weight = self.weight_for(channel)
            if weight <= 0:
                continue
            for rank, record_id in enumerate(unique_ids(record_ids), start=1):
                score = weight / (self.rank_constant + rank)
                contributions.setdefault(record_id, []).append(
                    RankContribution(channel, rank, weight, score)
                )
                first_positions.setdefault(record_id, (channel_index, rank))

        candidates = [
            FusedCandidate(
                record_id=record_id,
                score=sum(item.score for item in items),
                best_rank=min(item.rank for item in items),
                contributions=tuple(items),
            )
            for record_id, items in contributions.items()
        ]
        candidates.sort(
            key=lambda item: (
                -item.score,
                -len(item.contributions),
                item.best_rank,
                first_positions[item.record_id],
                item.record_id,
            )
        )
        return RankFusionBatch(
            provider=self.provider,
            candidates=tuple(candidates[:limit]),
            channel_counts=channel_counts,
            rank_constant=self.rank_constant,
        )

    def weight_for(self, channel: str) -> float:
        if channel in self.channel_weights:
            return float(self.channel_weights[channel])
        prefix = channel.split(":", 1)[0]
        return float(self.channel_weights.get(prefix, self.default_weight))


def unique_ids(record_ids: Sequence[int]) -> list[int]:
    result: list[int] = []
    seen: set[int] = set()
    for value in record_ids:
        record_id = int(value)
        if record_id <= 0 or record_id in seen:
            continue
        seen.add(record_id)
        result.append(record_id)
    return result
