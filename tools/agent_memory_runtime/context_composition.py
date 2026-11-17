# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations
from functools import partial

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
        partial(limited_context, defer_render_accounting=True, defer_lifecycle_accounting=True, defer_output_loop_accounting=True, defer_command_accounting=True, defer_record_loop_accounting=True, defer_archive_create_write_accounting=True, defer_cache_scan_accounting=True, defer_command_table_accounting=True, defer_divider_accounting=True, defer_gesture_accounting=True, defer_touch_index_accounting=True, defer_vertical_accounting=True, defer_sql_slot_accounting=True),
        path_context,
    )
