# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .models import Project
from .semantic_ecma import index_ecma_files
from .semantic_models import SemanticBatch


class LanguageAdapter(Protocol):
    adapter_id: str
    adapter_version: str
    language: str
    capabilities: tuple[str, ...]

    def index(self, project: Project, files: list[Path]) -> SemanticBatch: ...


class ArkTSSemanticAdapter:
    adapter_id = "arkts-static"
    adapter_version = "1.1"
    language = "ArkTS"
    capabilities = (
        "definitions", "references", "calls", "types", "inheritance",
        "state_flow", "callbacks", "async_flow", "api_boundaries", "mechanisms",
    )

    def index(self, project: Project, files: list[Path]) -> SemanticBatch:
        return index_ecma_files(project, files, self, state_annotations=True)


class TypeScriptSemanticAdapter:
    adapter_id = "typescript-static"
    adapter_version = "1.1"
    language = "TypeScript"
    capabilities = (
        "definitions", "references", "calls", "types", "inheritance",
        "callbacks", "async_flow", "api_boundaries", "mechanisms",
    )

    def index(self, project: Project, files: list[Path]) -> SemanticBatch:
        return index_ecma_files(project, files, self, state_annotations=False)


ADAPTERS: dict[str, LanguageAdapter] = {
    "ArkTS": ArkTSSemanticAdapter(),
    "TypeScript": TypeScriptSemanticAdapter(),
}


def adapter_for(language: str) -> LanguageAdapter | None:
    return ADAPTERS.get(language)


def registered_adapter_manifest() -> list[dict[str, object]]:
    return [
        {
            "adapter_id": adapter.adapter_id,
            "adapter_version": adapter.adapter_version,
            "language": adapter.language,
            "capabilities": list(adapter.capabilities),
        }
        for adapter in sorted(ADAPTERS.values(), key=lambda item: item.language)
    ]
