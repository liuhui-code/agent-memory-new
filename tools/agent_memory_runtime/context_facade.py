# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import Project
from .path_context_facade import PathContextFacade


class ContextFacade:
    """Stable context entry that composes independent retrieval lanes."""

    def __init__(
        self,
        project: Project,
        base_context: Callable[[Project, str], dict[str, Any]],
        path_context: PathContextFacade,
    ) -> None:
        self.project = project
        self.base_context = base_context
        self.path_context = path_context

    def execute(self, query: str) -> dict[str, Any]:
        result = self.base_context(self.project, query)
        path_payload = self.path_context.build(query)
        handoff = result.setdefault("query_handoff", {})
        handoff["path_context"] = path_payload
        return result
