# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .models import Project
from .semantic_adapters import adapter_for
from .semantic_models import SemanticBatch
from .semantic_provider_process import configured_provider, run_external_provider
from .semantic_provider_protocol import ProviderFailure


@dataclass(frozen=True)
class SemanticSelection:
    batch: SemanticBatch
    telemetry: dict[str, Any]


def run_semantic_adapter(
    project: Project,
    language: str,
    files: list[Path],
    mode: str = "auto",
    environ: Mapping[str, str] | None = None,
) -> SemanticSelection:
    if mode not in {"auto", "external", "static"}:
        raise ValueError(f"unsupported semantic provider mode: {mode}")
    static_adapter = adapter_for(language)
    if not static_adapter:
        raise ValueError(f"no semantic adapter registered for {language}")
    provider_configured = bool(configured_provider(language, environ))
    if mode == "static" or (mode == "auto" and not provider_configured):
        batch = static_adapter.index(project, files)
        return SemanticSelection(batch, static_telemetry(language, provider_configured, mode))
    try:
        batch, metadata = run_external_provider(project, language, files, environ)
        return SemanticSelection(batch, {
            "language": language,
            "mode": mode,
            "status": "exact",
            "selected": "external",
            "provider_configured": True,
            **metadata,
        })
    except ProviderFailure as exc:
        if mode == "external":
            raise
        batch = static_adapter.index(project, files)
        telemetry = static_telemetry(language, True, mode)
        telemetry.update({"status": "fallback", "fallback_reason": exc.code, "diagnostic": exc.detail})
        return SemanticSelection(batch, telemetry)


def static_telemetry(language: str, provider_configured: bool, mode: str) -> dict[str, Any]:
    return {
        "language": language,
        "mode": mode,
        "status": "static",
        "selected": "static",
        "provider_configured": provider_configured,
        "duration_ms": 0.0,
        "output_bytes": 0,
    }
