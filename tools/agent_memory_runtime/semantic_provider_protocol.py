# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .models import Project
from .semantic_models import MAX_FILES, SEMANTIC_SCHEMA, SemanticBatch, source_digest, symbol_key


PROVIDER_REQUEST_SCHEMA = "semantic-provider-request/v1"
PROVIDER_RESULT_SCHEMA = "semantic-provider-result/v1"
PROVIDER_TIMEOUT_SECONDS = 20
PROVIDER_MAX_OUTPUT_BYTES = 16 * 1024 * 1024
PROVIDER_MAX_STDERR_BYTES = 32 * 1024


class ProviderFailure(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail[:500]


def provider_env_name(language: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", language).strip("_").upper()
    return f"AGENT_MEMORY_SEMANTIC_PROVIDER_{normalized}"


def build_provider_request(project: Project, language: str, files: list[Path]) -> dict[str, Any]:
    if len(set(files)) > MAX_FILES:
        raise ProviderFailure("request_too_large", f"provider request exceeds {MAX_FILES} files")
    requested: list[dict[str, str]] = []
    for path in sorted(set(item.resolve() for item in files)):
        relative = safe_project_path(project, path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        requested.append({"path": relative, "digest": source_digest(text)})
    material = json.dumps({"language": language, "files": requested}, sort_keys=True, separators=(",", ":"))
    request_id = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return {
        "schema_version": PROVIDER_REQUEST_SCHEMA,
        "request_id": request_id,
        "semantic_schema": SEMANTIC_SCHEMA,
        "language": language,
        "project_root": str(project.root),
        "files": requested,
        "limits": {
            "timeout_seconds": PROVIDER_TIMEOUT_SECONDS,
            "max_output_bytes": PROVIDER_MAX_OUTPUT_BYTES,
        },
    }


def validate_provider_result(request: dict[str, Any], value: Any) -> tuple[SemanticBatch, dict[str, Any]]:
    if not isinstance(value, dict) or value.get("schema_version") != PROVIDER_RESULT_SCHEMA:
        raise ProviderFailure("invalid_schema", "provider returned an unsupported result schema")
    if value.get("request_id") != request["request_id"]:
        raise ProviderFailure("request_mismatch", "provider result request_id does not match")
    provider = value.get("provider")
    if not isinstance(provider, dict):
        raise ProviderFailure("invalid_provider", "provider metadata must be an object")
    provider_id = require_text(provider, "id")
    provider_version = require_text(provider, "version")
    toolchain = str(provider.get("toolchain") or "unspecified")[:160]
    raw_batch = value.get("batch")
    if not isinstance(raw_batch, dict):
        raise ProviderFailure("invalid_batch", "provider result requires a semantic batch")
    try:
        batch = SemanticBatch.from_dict(raw_batch)
    except (TypeError, ValueError) as exc:
        raise ProviderFailure("invalid_batch", str(exc)) from exc
    if batch.language != request["language"]:
        raise ProviderFailure("language_mismatch", "provider batch language does not match request")
    if batch.adapter_id != provider_id or batch.adapter_version != provider_version:
        raise ProviderFailure("identity_mismatch", "provider and batch adapter identities differ")
    expected = {item["path"]: item["digest"] for item in request["files"]}
    if batch.source_digests != expected:
        raise ProviderFailure("stale_source", "provider source digests do not match requested files")
    validate_exact_batch(batch, set(expected))
    return batch, {
        "provider_id": provider_id,
        "provider_version": provider_version,
        "toolchain": toolchain,
        "capabilities": list(batch.capabilities),
    }


def validate_exact_batch(batch: SemanticBatch, requested_paths: set[str]) -> None:
    entity_keys = {entity.key for entity in batch.entities}
    valid_sources = entity_keys | {f"file:{path}" for path in requested_paths}
    for path in batch.source_digests:
        validate_requested_path(path, requested_paths)
    for entity in batch.entities:
        validate_requested_path(entity.file_path, requested_paths)
        expected_key = symbol_key(batch.language, entity.file_path, entity.qualified_name, entity.signature)
        if entity.key != expected_key:
            raise ProviderFailure("unstable_symbol_key", f"non-deterministic symbol key: {entity.qualified_name}")
        if entity.evidence_class != "exact":
            raise ProviderFailure("non_exact_evidence", "external exact provider emitted a non-exact entity")
    for relation in batch.relations:
        if relation.source_key not in valid_sources:
            raise ProviderFailure("unknown_source", f"provider relation has unknown source: {relation.source_key}")
        if relation.target_file_path:
            validate_safe_relative_path(relation.target_file_path)
        if relation.evidence_class != "exact":
            raise ProviderFailure("non_exact_evidence", "external exact provider emitted a non-exact relation")


def safe_project_path(project: Project, path: Path) -> str:
    try:
        relative = path.relative_to(project.root).as_posix()
    except ValueError as exc:
        raise ProviderFailure("unsafe_path", f"provider file is outside project: {path}") from exc
    validate_safe_relative_path(relative)
    return relative


def validate_requested_path(value: str, allowed: set[str]) -> None:
    validate_safe_relative_path(value)
    if value not in allowed:
        raise ProviderFailure("unsafe_path", f"provider returned an unrequested source path: {value}")


def validate_safe_relative_path(value: str) -> None:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ProviderFailure("unsafe_path", f"provider returned an unsafe relative path: {value}")


def require_text(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ProviderFailure("invalid_provider", f"provider metadata requires {key}")
    return item.strip()[:160]
