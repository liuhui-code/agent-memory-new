# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from .context_facade import ContextFacade
from .models import Project
from .path_anchor_sqlite import SQLiteLogAnchorResolver
from .path_context_facade import PathContextFacade
from .path_entry_policy import ArkTSEntryPointPolicy, CompositeEntryPointPolicy, GenericEntryPointPolicy
from .path_graph_sqlite import SQLiteProgramGraphReader
from .path_ranking import StructuralCallPathRankingPolicy
from .path_search import BoundedReverseCallPathSearch
from .query import limited_context


def build_context_facade(
    project: Project,
    enable_passage_shadow: bool = False,
) -> ContextFacade:
    path_context = PathContextFacade(
        anchor_resolver=SQLiteLogAnchorResolver(project),
        graph_reader=SQLiteProgramGraphReader(project),
        entry_policy=CompositeEntryPointPolicy(ArkTSEntryPointPolicy(), GenericEntryPointPolicy()),
        search_strategy=BoundedReverseCallPathSearch(),
        ranking_policy=StructuralCallPathRankingPolicy(),
    )
    return ContextFacade(
        project,
        lambda current, query: limited_context(
            current, query, enable_passage_shadow=enable_passage_shadow
        ),
        path_context,
    )
