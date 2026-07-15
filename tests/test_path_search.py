# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.path_context_models import (
    EntryPoint,
    GraphEdge,
    GraphExpansion,
    GraphNode,
    LogAnchorMatch,
    NodeRef,
    PathBounds,
    PathSeed,
    RawPath,
)
from tools.agent_memory_runtime.path_ranking import StructuralCallPathRankingPolicy
from tools.agent_memory_runtime.path_search import BoundedReverseCallPathSearch


def node(identifier: int, name: str) -> GraphNode:
    return GraphNode(NodeRef("code_symbol", identifier), "symbol", name, name, "src/Test.ets", language="ArkTS")


def edge(identifier: int, source: GraphNode, target: GraphNode) -> GraphEdge:
    return GraphEdge(
        identifier,
        source.ref,
        target.ref,
        "calls",
        "static",
        "static_call",
        "test:v1",
        "1",
        0.9,
    )


class FakeGraph:
    def __init__(self, edges: list[GraphEdge], nodes: list[GraphNode]) -> None:
        self.edges = edges
        self.nodes = {item.ref.key: item for item in nodes}
        self.predecessor_calls: list[tuple[str, ...]] = []

    def predecessors(self, node_refs: list[NodeRef], relations: set[str]) -> GraphExpansion:
        keys = {item.key for item in node_refs}
        self.predecessor_calls.append(tuple(sorted(keys)))
        selected = tuple(item for item in self.edges if item.target.key in keys and item.relation in relations)
        refs = {item.source.key for item in selected} | {item.target.key for item in selected}
        return GraphExpansion({key: self.nodes[key] for key in refs}, selected)


class NameEntryPolicy:
    def classify(self, candidate: GraphNode) -> EntryPoint | None:
        if candidate.name.startswith("entry"):
            return EntryPoint("event_handler", 1.0, "test entry")
        return None


class PathSearchTests(unittest.TestCase):
    def seed(self, emitter: GraphNode) -> PathSeed:
        anchor = LogAnchorMatch(1, "failed", "Test", "failed", "src/Test.ets", emitter.name, 1, "exact", 1.0)
        return PathSeed("seed", anchor, emitter, 1)

    def test_frontier_is_loaded_once_per_depth_not_once_per_path(self) -> None:
        emitter = node(1, "emit")
        left = node(2, "left")
        right = node(3, "right")
        entry_left = node(4, "entryLeft")
        entry_right = node(5, "entryRight")
        graph = FakeGraph(
            [edge(1, left, emitter), edge(2, right, emitter), edge(3, entry_left, left), edge(4, entry_right, right)],
            [emitter, left, right, entry_left, entry_right],
        )

        paths = BoundedReverseCallPathSearch().search(
            self.seed(emitter), graph, NameEntryPolicy(), PathBounds(max_depth=4)
        )

        self.assertEqual(2, len(paths))
        self.assertEqual(2, len(graph.predecessor_calls))
        self.assertEqual((left.ref.key, right.ref.key), graph.predecessor_calls[1])

    def test_depth_bound_returns_explicit_truncated_candidate(self) -> None:
        emitter = node(1, "emit")
        middle = node(2, "middle")
        far = node(3, "far")
        graph = FakeGraph([edge(1, middle, emitter), edge(2, far, middle)], [emitter, middle, far])

        paths = BoundedReverseCallPathSearch().search(
            self.seed(emitter), graph, NameEntryPolicy(), PathBounds(max_depth=1)
        )

        self.assertEqual(1, len(paths))
        self.assertTrue(paths[0].truncated)
        self.assertFalse(paths[0].complete)
        self.assertEqual("depth bound reached", paths[0].entry.reason)

    def test_cycle_is_not_reentered(self) -> None:
        emitter = node(1, "emit")
        middle = node(2, "middle")
        graph = FakeGraph([edge(1, middle, emitter), edge(2, emitter, middle)], [emitter, middle])

        paths = BoundedReverseCallPathSearch().search(
            self.seed(emitter), graph, NameEntryPolicy(), PathBounds(max_depth=6)
        )

        self.assertEqual(1, len(paths))
        self.assertFalse(paths[0].complete)
        self.assertLessEqual(len(graph.predecessor_calls), 2)

    def test_ranking_deduplicates_same_nodes_and_keeps_specific_relation(self) -> None:
        emitter = node(1, "emit")
        entry_node = node(2, "entryPage")
        seed = self.seed(emitter)
        entry = EntryPoint("lifecycle", 1.0, "test entry")
        call_edge = edge(1, entry_node, emitter)
        await_edge = GraphEdge(**{**call_edge.__dict__, "edge_id": 2, "relation": "awaits"})
        paths = [
            RawPath(seed, (entry_node, emitter), (call_edge,), entry, True),
            RawPath(seed, (entry_node, emitter), (await_edge,), entry, True),
        ]

        ranked = StructuralCallPathRankingPolicy().rank(paths, {}, PathBounds())

        self.assertEqual(1, len(ranked))
        self.assertEqual("awaits", ranked[0].raw_path.edges[0].relation)


if __name__ == "__main__":
    unittest.main()
