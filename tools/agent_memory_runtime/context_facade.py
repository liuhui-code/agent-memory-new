# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import Project
from .index_freshness import filter_fresh_path_context
from .path_context_facade import PathContextFacade


class ContextFacade:
    """Stable context entry that composes independent retrieval lanes."""

    def __init__(
        self,
        project: Project,
        base_context: Callable[[Project, str, str | None], dict[str, Any]],
        path_context: PathContextFacade,
    ) -> None:
        self.project = project
        self.base_context = base_context
        self.path_context = path_context

    def execute(self, query: str, explicit_intent: str | None = None) -> dict[str, Any]:
        result = self.base_context(self.project, query, explicit_intent)
        path_payload = self.path_context.build(query)
        freshness = result.get("source_freshness") or {}
        path_payload, freshness = filter_fresh_path_context(
            self.project, path_payload, freshness
        )
        from .query_render_selection import RenderContext, enrich_render_context, render_context_view
        if isinstance(result, RenderContext):
            pending = getattr(result, '_pending_accounting', False) is True
            result._pending_accounting = False
            result = enrich_render_context(result, query, path_payload, freshness)
            if pending:
                adopted, _ = render_context_view(result)
                from .query_results import record_context_use, record_query_miss_if_empty
                record_context_use(self.project, adopted)
                record_query_miss_if_empty(self.project, "context", query, adopted)
            return result
        from .query_lifecycle_log_context import LifecycleLogContext, enrich_lifecycle_log_context
        if isinstance(result, LifecycleLogContext):
            pending = getattr(result, '_pending_accounting', False) is True
            result._pending_accounting = False
            result = enrich_lifecycle_log_context(result, query, path_payload, freshness)
            if pending:
                from .query_results import record_context_use, record_query_miss_if_empty
                record_context_use(self.project, dict(result))
                record_query_miss_if_empty(self.project, 'context', query, dict(result))
            return result
        from .query_lifecycle_selection import LifecycleContext, enrich_lifecycle_context, lifecycle_context_view
        if isinstance(result, LifecycleContext):
            pending = getattr(result, '_pending_accounting', False) is True
            result._pending_accounting = False
            result = enrich_lifecycle_context(result, query, path_payload, freshness)
            if pending:
                adopted, _ = lifecycle_context_view(result)
                from .query_results import record_context_use, record_query_miss_if_empty
                record_context_use(self.project, adopted)
                record_query_miss_if_empty(self.project, "context", query, adopted)
            return result
        from .query_output_loop_selection import OutputLoopContext, enrich_output_loop_context, output_loop_context_view
        if isinstance(result, OutputLoopContext):
            pending = getattr(result, '_pending_accounting', False) is True
            result._pending_accounting = False
            result = enrich_output_loop_context(result, query, path_payload, freshness)
            if pending:
                adopted, _ = output_loop_context_view(result)
                from .query_results import record_context_use, record_query_miss_if_empty
                record_context_use(self.project, adopted)
                record_query_miss_if_empty(self.project, "context", query, adopted)
            return result
        from .query_command_selection import CommandContext, enrich_command_context, command_context_view
        if isinstance(result, CommandContext):
            pending = getattr(result, '_pending_accounting', False) is True
            result._pending_accounting = False
            result = enrich_command_context(result, query, path_payload, freshness)
            if pending:
                adopted, _ = command_context_view(result)
                from .query_results import record_context_use, record_query_miss_if_empty
                record_context_use(self.project, adopted)
                record_query_miss_if_empty(self.project, "context", query, adopted)
            return result
        from .query_cache_scan_selection import CacheScanContext, enrich_cache_scan_context, cache_scan_context_view
        if isinstance(result, CacheScanContext):
            pending = getattr(result, '_pending_accounting', False) is True
            result._pending_accounting = False
            result = enrich_cache_scan_context(result, query, path_payload, freshness)
            if pending:
                adopted, _ = cache_scan_context_view(result)
                from .query_results import record_context_use, record_query_miss_if_empty
                record_context_use(self.project, adopted)
                record_query_miss_if_empty(self.project, "context", query, adopted)
            return result
        from .query_record_loop_selection import RecordLoopContext, enrich_record_loop, accounting_record_loop
        if isinstance(result, RecordLoopContext):
            pending = getattr(result, '_pending_accounting', False) is True
            result._pending_accounting = False
            result = enrich_record_loop(result, query, path_payload, freshness)
            if pending:
                adopted = accounting_record_loop(result) if isinstance(result, RecordLoopContext) else result
                from .query_results import record_context_use, record_query_miss_if_empty
                record_context_use(self.project, adopted)
                record_query_miss_if_empty(self.project, "context", query, adopted)
            return result
        from .query_archive_create_write_selection import ArchiveCreateWriteContext, enrich_archive_create_write, accounting_archive_create_write
        if isinstance(result, ArchiveCreateWriteContext):
            pending = getattr(result, '_pending_accounting', False) is True
            result._pending_accounting = False
            result = enrich_archive_create_write(result, query, path_payload, freshness)
            if pending:
                adopted = accounting_archive_create_write(result) if isinstance(result, ArchiveCreateWriteContext) else result
                from .query_results import record_context_use, record_query_miss_if_empty
                record_context_use(self.project, adopted)
                record_query_miss_if_empty(self.project, "context", query, adopted)
            return result
        from .query_command_table_selection import CommandTableContext, enrich_command_table, accounting_command_table
        if isinstance(result, CommandTableContext):
            pending = getattr(result, '_pending_accounting', False) is True
            result._pending_accounting = False
            result = enrich_command_table(result, query, path_payload, freshness)
            if pending:
                adopted = accounting_command_table(result) if isinstance(result, CommandTableContext) else result
                from .query_results import record_context_use, record_query_miss_if_empty
                record_context_use(self.project, adopted)
                record_query_miss_if_empty(self.project, "context", query, adopted)
            return result
        from .query_ui_divider_selection import DividerContext, enrich_divider, accounting_divider
        if isinstance(result, DividerContext):
            pending = getattr(result, '_pending_accounting', False) is True
            result._pending_accounting = False
            result = enrich_divider(result, query, path_payload, freshness)
            if pending:
                adopted = accounting_divider(result) if isinstance(result, DividerContext) else result
                from .query_results import record_context_use, record_query_miss_if_empty
                record_context_use(self.project, adopted)
                record_query_miss_if_empty(self.project, "context", query, adopted)
            return result
        result["source_freshness"] = freshness
        handoff = result.setdefault("query_handoff", {})
        handoff["path_context"] = path_payload
        return result
