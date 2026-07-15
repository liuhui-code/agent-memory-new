# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Protocol, Sequence

from .path_context_models import (
    AnchorResolution,
    EntryPoint,
    ExpectedLogAnchor,
    GraphExpansion,
    GraphNode,
    GraphSnapshot,
    NodeRef,
    PathBounds,
    PathCandidate,
    PathSeed,
    RawPath,
)


class LogAnchorResolver(Protocol):
    def resolve(self, query: str) -> AnchorResolution: ...


class ProgramGraphReader(Protocol):
    def snapshot(self) -> GraphSnapshot: ...

    def emitters(self, log_ids: Sequence[int]) -> dict[int, tuple[GraphNode, ...]]: ...

    def predecessors(self, node_refs: Sequence[NodeRef], relations: set[str]) -> GraphExpansion: ...

    def nearby_logs(self, node_refs: Sequence[NodeRef]) -> dict[str, tuple[ExpectedLogAnchor, ...]]: ...


class EntryPointPolicy(Protocol):
    def classify(self, node: GraphNode) -> EntryPoint | None: ...


class CallPathSearchStrategy(Protocol):
    def search(
        self,
        seed: PathSeed,
        graph: ProgramGraphReader,
        entry_policy: EntryPointPolicy,
        bounds: PathBounds,
    ) -> Sequence[RawPath]: ...


class CallPathRankingPolicy(Protocol):
    def rank(
        self,
        paths: Sequence[RawPath],
        expected_logs: dict[str, tuple[ExpectedLogAnchor, ...]],
        bounds: PathBounds,
    ) -> Sequence[PathCandidate]: ...
