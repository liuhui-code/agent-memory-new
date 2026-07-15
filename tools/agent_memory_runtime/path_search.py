# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from .path_context_models import EntryPoint, GraphEdge, GraphNode, PathBounds, PathSeed, RawPath
from .path_context_ports import EntryPointPolicy, ProgramGraphReader


PROGRAM_PATH_RELATIONS = {
    "awaits",
    "calls",
    "dispatches_event",
    "handles_callback",
    "handles_event",
    "registers_callback",
    "routes_to",
    "uses_service",
}


@dataclass(frozen=True)
class _SearchState:
    nodes_reverse: tuple[GraphNode, ...]
    edges_reverse: tuple[GraphEdge, ...]


class BoundedReverseCallPathSearch:
    """Find callers in bounded breadth-first layers from a log emitter."""

    def search(
        self,
        seed: PathSeed,
        graph: ProgramGraphReader,
        entry_policy: EntryPointPolicy,
        bounds: PathBounds,
    ) -> Sequence[RawPath]:
        initial = _SearchState((seed.emitter,), ())
        terminal = entry_policy.classify(seed.emitter)
        if terminal:
            return (materialize(seed, initial, terminal, complete=True),)

        frontier = [initial]
        results: list[RawPath] = []
        seen_nodes = {seed.emitter.ref.key}
        observed_edges: set[int] = set()

        for depth in range(bounds.max_depth):
            if not frontier or len(results) >= bounds.max_raw_paths_per_seed:
                break
            expansion = graph.predecessors(
                [state.nodes_reverse[-1].ref for state in frontier],
                PROGRAM_PATH_RELATIONS,
            )
            incoming = group_incoming(expansion.edges)
            next_frontier: list[_SearchState] = []
            for state in frontier:
                current = state.nodes_reverse[-1]
                edges = incoming.get(current.ref.key, ())
                if not edges:
                    results.append(incomplete_path(seed, state, "no known caller"))
                    continue
                for edge in edges:
                    if len(observed_edges) >= bounds.max_edges:
                        results.append(incomplete_path(seed, state, "edge bound reached", truncated=True))
                        break
                    observed_edges.add(edge.edge_id)
                    predecessor = expansion.nodes.get(edge.source.key)
                    if predecessor is None:
                        continue
                    if path_visits(state, predecessor) >= bounds.cycle_visit_limit:
                        continue
                    if predecessor.ref.key not in seen_nodes and len(seen_nodes) >= bounds.max_nodes:
                        results.append(incomplete_path(seed, state, "node bound reached", truncated=True))
                        continue
                    seen_nodes.add(predecessor.ref.key)
                    candidate = _SearchState(
                        state.nodes_reverse + (predecessor,),
                        state.edges_reverse + (edge,),
                    )
                    entry = entry_policy.classify(predecessor)
                    if entry:
                        results.append(materialize(seed, candidate, entry, complete=True))
                    elif depth + 1 >= bounds.max_depth:
                        results.append(incomplete_path(seed, candidate, "depth bound reached", truncated=True))
                    else:
                        next_frontier.append(candidate)
                    if len(results) + len(next_frontier) >= bounds.max_raw_paths_per_seed:
                        break
                if len(results) + len(next_frontier) >= bounds.max_raw_paths_per_seed:
                    break
            frontier = next_frontier[: bounds.max_raw_paths_per_seed]

        if not results:
            results.append(incomplete_path(seed, initial, "no reconstructable path"))
        return tuple(results[: bounds.max_raw_paths_per_seed])


def group_incoming(edges: Sequence[GraphEdge]) -> dict[str, tuple[GraphEdge, ...]]:
    grouped: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in edges:
        grouped[edge.target.key].append(edge)
    return {
        key: tuple(sorted(items, key=lambda item: (item.confidence, -item.edge_id), reverse=True))
        for key, items in grouped.items()
    }


def path_visits(state: _SearchState, node: GraphNode) -> int:
    return sum(item.ref.key == node.ref.key for item in state.nodes_reverse)


def materialize(
    seed: PathSeed,
    state: _SearchState,
    entry: EntryPoint,
    complete: bool,
    truncated: bool = False,
) -> RawPath:
    return RawPath(
        seed=seed,
        nodes=tuple(reversed(state.nodes_reverse)),
        edges=tuple(reversed(state.edges_reverse)),
        entry=entry,
        complete=complete,
        truncated=truncated,
    )


def incomplete_path(seed: PathSeed, state: _SearchState, reason: str, truncated: bool = False) -> RawPath:
    return materialize(
        seed,
        state,
        EntryPoint("unknown_entry", 0.2, reason),
        complete=False,
        truncated=truncated,
    )
