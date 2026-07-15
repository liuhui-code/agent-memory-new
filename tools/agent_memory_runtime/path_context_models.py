# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PathBounds:
    max_depth: int = 6
    max_nodes: int = 80
    max_edges: int = 160
    max_raw_paths_per_seed: int = 20
    max_returned_paths: int = 5
    max_same_entry_paths: int = 2
    cycle_visit_limit: int = 1

    def to_dict(self) -> dict[str, int]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class NodeRef:
    entity_type: str
    entity_id: int

    @property
    def key(self) -> str:
        return f"{self.entity_type}:{self.entity_id}"


@dataclass(frozen=True)
class GraphSnapshot:
    project_id: str
    graph_revision: int


@dataclass(frozen=True)
class GraphNode:
    ref: NodeRef
    kind: str
    name: str
    qualified_name: str
    file_path: str
    symbol_type: str = ""
    language: str = ""
    start_line: int | None = None
    end_line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.ref.key,
            "entity_type": self.ref.entity_type,
            "entity_id": self.ref.entity_id,
            "kind": self.kind,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file_path": self.file_path,
            "symbol_type": self.symbol_type,
            "language": self.language,
            "source_span": {"start_line": self.start_line, "end_line": self.end_line},
        }


@dataclass(frozen=True)
class GraphEdge:
    edge_id: int
    source: NodeRef
    target: NodeRef
    relation: str
    evidence_class: str
    evidence_kind: str
    extractor_version: str
    source_revision: str
    confidence: float
    ambiguity: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source": self.source.key,
            "target": self.target.key,
            "relation": self.relation,
            "evidence_class": self.evidence_class,
            "evidence_kind": self.evidence_kind,
            "extractor_version": self.extractor_version,
            "source_revision": self.source_revision,
            "confidence": round(self.confidence, 3),
            "ambiguity": self.ambiguity,
        }


@dataclass(frozen=True)
class LogAnchorMatch:
    log_id: int
    message_template: str
    logger: str
    event_name: str
    file_path: str
    function: str
    line: int | None
    match_kind: str
    anchor_match_score: float

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class AnchorResolution:
    activated: bool
    reason: str
    matches: tuple[LogAnchorMatch, ...] = ()
    candidate_count: int = 0


@dataclass(frozen=True)
class PathSeed:
    seed_id: str
    anchor: LogAnchorMatch
    emitter: GraphNode
    graph_revision: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_id": self.seed_id,
            "log_statement_id": self.anchor.log_id,
            "message_template": self.anchor.message_template,
            "logger": self.anchor.logger,
            "event_name": self.anchor.event_name,
            "emitter": self.emitter.to_dict(),
            "source_revision": self.graph_revision,
            "match_kind": self.anchor.match_kind,
            "anchor_match_score": round(self.anchor.anchor_match_score, 3),
        }


@dataclass(frozen=True)
class EntryPoint:
    category: str
    score: float
    reason: str


@dataclass(frozen=True)
class RawPath:
    seed: PathSeed
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    entry: EntryPoint
    complete: bool
    truncated: bool = False


@dataclass(frozen=True)
class ExpectedLogAnchor:
    log_id: int
    node_id: str
    message_template: str
    logger: str
    event_name: str
    file_path: str
    function: str
    line: int | None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class PathCandidate:
    path_id: str
    raw_path: RawPath
    structural_score: float
    score_components: dict[str, float]
    expected_logs: tuple[ExpectedLogAnchor, ...] = ()
    uncertainty: tuple[str, ...] = ()
    missing_segments: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        path = self.raw_path
        return {
            "path_id": self.path_id,
            "seed_id": path.seed.seed_id,
            "entry": {
                "node": path.nodes[0].to_dict(),
                "category": path.entry.category,
                "reason": path.entry.reason,
            },
            "emitter": path.nodes[-1].to_dict(),
            "nodes": [node.to_dict() for node in path.nodes],
            "edges": [edge.to_dict() for edge in path.edges],
            "expected_log_anchors": [item.to_dict() for item in self.expected_logs],
            "structural_score": round(self.structural_score, 3),
            "score_components": self.score_components,
            "uncertainty": list(self.uncertainty),
            "missing_segments": list(self.missing_segments),
            "source_revision": path.seed.graph_revision,
            "complete": path.complete,
            "truncated": path.truncated,
        }


@dataclass(frozen=True)
class GraphExpansion:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: tuple[GraphEdge, ...] = ()
