# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from time import monotonic
from typing import Any, Mapping

from .models import Project
from .semantic_models import SemanticBatch
from .semantic_provider_protocol import (
    PROVIDER_MAX_OUTPUT_BYTES,
    PROVIDER_MAX_STDERR_BYTES,
    PROVIDER_TIMEOUT_SECONDS,
    ProviderFailure,
    build_provider_request,
    provider_env_name,
    validate_provider_result,
)


def configured_provider(language: str, environ: Mapping[str, str] | None = None) -> str | None:
    values = environ if environ is not None else os.environ
    raw = str(values.get(provider_env_name(language)) or "").strip()
    return raw or None


def resolve_provider_executable(language: str, environ: Mapping[str, str] | None = None) -> str | None:
    configured = configured_provider(language, environ)
    if not configured:
        return None
    if any(character in configured for character in ("\n", "\r", "\0")):
        raise ProviderFailure("invalid_executable", "provider executable contains invalid characters")
    candidate = Path(configured).expanduser()
    resolved = str(candidate.resolve()) if candidate.is_absolute() or candidate.parent != Path(".") else shutil.which(configured)
    if not resolved or not Path(resolved).is_file() or not os.access(resolved, os.X_OK):
        raise ProviderFailure("provider_unavailable", f"provider executable is unavailable: {configured}")
    return resolved


def run_external_provider(
    project: Project,
    language: str,
    files: list[Path],
    environ: Mapping[str, str] | None = None,
    timeout_seconds: int = PROVIDER_TIMEOUT_SECONDS,
    max_output_bytes: int = PROVIDER_MAX_OUTPUT_BYTES,
) -> tuple[SemanticBatch, dict[str, Any]]:
    executable = resolve_provider_executable(language, environ)
    if not executable:
        raise ProviderFailure("provider_not_configured", f"no external provider configured for {language}")
    request = build_provider_request(project, language, files)
    request_bytes = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    child_env = os.environ.copy()
    if environ is not None:
        child_env.update(environ)
    started = monotonic()
    try:
        process = subprocess.run(
            [executable], input=request_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=project.root, env=child_env, timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProviderFailure("provider_timeout", f"provider exceeded {timeout_seconds}s timeout") from exc
    except OSError as exc:
        raise ProviderFailure("provider_spawn_failed", str(exc)) from exc
    duration_ms = round((monotonic() - started) * 1000, 3)
    stderr = process.stderr[:PROVIDER_MAX_STDERR_BYTES].decode("utf-8", errors="replace")
    if process.returncode:
        raise ProviderFailure("provider_exit", f"provider exited {process.returncode}: {stderr}")
    if len(process.stdout) > max_output_bytes:
        raise ProviderFailure("provider_output_too_large", f"provider output exceeds {max_output_bytes} bytes")
    try:
        value = json.loads(process.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderFailure("invalid_json", "provider stdout is not one JSON document") from exc
    batch, metadata = validate_provider_result(request, value)
    metadata.update({
        "executable": executable,
        "duration_ms": duration_ms,
        "output_bytes": len(process.stdout),
        "stderr": stderr,
        "request_id": request["request_id"],
    })
    return batch, metadata
