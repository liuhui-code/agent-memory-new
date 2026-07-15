# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from .path_context_models import NodeRef, PathBounds, PathSeed, RawPath
from .path_context_ports import (
    CallPathRankingPolicy,
    CallPathSearchStrategy,
    EntryPointPolicy,
    LogAnchorResolver,
    ProgramGraphReader,
)


class PathContextFacade:
    def __init__(
        self,
        anchor_resolver: LogAnchorResolver,
        graph_reader: ProgramGraphReader,
        entry_policy: EntryPointPolicy,
        search_strategy: CallPathSearchStrategy,
        ranking_policy: CallPathRankingPolicy,
        bounds: PathBounds | None = None,
    ) -> None:
        self.anchor_resolver = anchor_resolver
        self.graph_reader = graph_reader
        self.entry_policy = entry_policy
        self.search_strategy = search_strategy
        self.ranking_policy = ranking_policy
        self.bounds = bounds or PathBounds()

    def build(self, query: str) -> dict[str, object]:
        resolution = self.anchor_resolver.resolve(query)
        if not resolution.activated:
            return inactive_payload(resolution.reason, resolution.candidate_count, self.bounds)

        snapshot = self.graph_reader.snapshot()
        emitters = self.graph_reader.emitters([match.log_id for match in resolution.matches])
        seeds = [
            PathSeed(
                seed_id=f"log_{match.log_id}_emitter_{emitter.ref.entity_id}",
                anchor=match,
                emitter=emitter,
                graph_revision=snapshot.graph_revision,
            )
            for match in resolution.matches
            for emitter in emitters.get(match.log_id, ())
        ]
        raw_paths: list[RawPath] = []
        for seed in seeds:
            raw_paths.extend(
                self.search_strategy.search(seed, self.graph_reader, self.entry_policy, self.bounds)
            )
        node_refs = unique_path_refs(raw_paths)
        expected_logs = self.graph_reader.nearby_logs(node_refs)
        candidates = self.ranking_policy.rank(raw_paths, expected_logs, self.bounds)
        missing_emitters = [match.log_id for match in resolution.matches if not emitters.get(match.log_id)]
        return {
            "schema_version": "log-anchored-path-context/v1",
            "activated": True,
            "activation_reason": resolution.reason,
            "candidate_count": resolution.candidate_count,
            "graph_revision": snapshot.graph_revision,
            "seeds": [seed.to_dict() for seed in seeds],
            "path_candidates": [candidate.to_dict() for candidate in candidates],
            "gaps": {
                "anchors_without_emitters": missing_emitters,
                "no_reconstructable_path": bool(seeds and not candidates),
            },
            "bounds": self.bounds.to_dict(),
            "lane_isolation": lane_isolation(),
            "agent_usage": {
                "purpose": "compare candidate paths with the user's temporary log order and current source",
                "runtime_reads_temporary_logs": False,
                "runtime_selects_root_cause": False,
            },
        }


def inactive_payload(reason: str, candidate_count: int, bounds: PathBounds) -> dict[str, object]:
    return {
        "schema_version": "log-anchored-path-context/v1",
        "activated": False,
        "activation_reason": reason,
        "candidate_count": candidate_count,
        "seeds": [],
        "path_candidates": [],
        "gaps": {},
        "bounds": bounds.to_dict(),
        "lane_isolation": lane_isolation(),
    }


def lane_isolation() -> dict[str, str]:
    return {
        "log_anchor": "code_log_statements identity fields only",
        "program_path": "current active code graph edges only",
        "semantic_correction": "annotation in base context; cannot create or rank paths",
        "experience": "advisory in base context; cannot create or rank paths",
    }


def unique_path_refs(paths: list[RawPath]) -> list[NodeRef]:
    return list({node.ref.key: node.ref for path in paths for node in path.nodes}.values())
