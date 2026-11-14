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
        result["source_freshness"] = freshness
        handoff = result.setdefault("query_handoff", {})
        handoff["path_context"] = path_payload
        return result
