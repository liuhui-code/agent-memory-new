# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from pathlib import Path

from .models import Project
from .semantic_models import SemanticBatch, SemanticEntity, SemanticRelation, source_digest, symbol_key
from .source_static_extractors import build_target_ranges, native_callable_ranges


class StaticSourceSemanticAdapter:
    def __init__(self, adapter_id: str, language: str, kind: str) -> None:
        self.adapter_id = adapter_id
        self.adapter_version = "1.0"
        self.language = language
        self.kind = kind
        self.capabilities = ("definitions", "calls") if kind == "native" else ("definitions",)

    def index(self, project: Project, files: list[Path]) -> SemanticBatch:
        digests: dict[str, str] = {}
        entities: list[SemanticEntity] = []
        pending_calls: list[tuple[str, str, int]] = []
        emitted_keys: set[str] = set()
        for path in sorted(set(files)):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                relative = path.resolve().relative_to(project.root.resolve()).as_posix()
            except (OSError, ValueError):
                continue
            digests[relative] = source_digest(text)
            ranges = native_callable_ranges(text) if self.kind == "native" else build_target_ranges(text)
            lines = text.splitlines()
            for item in ranges:
                kind = str(item.get("kind") or "function")
                key = unique_symbol_key(
                    self.language,
                    relative,
                    str(item["qualified_name"]),
                    str(item["signature"]),
                    int(item["start_line"]),
                    emitted_keys,
                )
                emitted_keys.add(key)
                entities.append(SemanticEntity(
                    key=key,
                    file_path=relative,
                    name=item["symbol"],
                    kind=kind,
                    qualified_name=item["qualified_name"],
                    signature=item["signature"],
                    start_line=item["start_line"],
                    end_line=item["end_line"],
                    evidence_class="static",
                ))
                if self.kind == "native":
                    body = "\n".join(lines[item["start_line"] - 1:item["end_line"]])
                    for target in native_calls(body):
                        pending_calls.append((key, target, item["start_line"]))
        local_names = {entity.name for entity in entities}
        relations = [
            SemanticRelation(
                source_key=source,
                relation="calls",
                target_name=target,
                line=line,
                confidence=0.7,
                evidence_class="static",
                detail=f"static call to {target}",
            )
            for source, target, line in pending_calls
            if target in local_names
        ]
        return SemanticBatch(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            language=self.language,
            capabilities=list(self.capabilities),
            source_digests=digests,
            entities=entities,
            relations=relations,
        ).validate()


def native_calls(text: str) -> list[str]:
    blocked = {"catch", "for", "if", "return", "sizeof", "switch", "while"}
    return list(dict.fromkeys(
        name for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", text)
        if name not in blocked
    ))


def unique_symbol_key(
    language: str,
    file_path: str,
    qualified_name: str,
    signature: str,
    start_line: int,
    emitted: set[str],
) -> str:
    key = symbol_key(language, file_path, qualified_name, signature)
    if key not in emitted:
        return key
    return symbol_key(
        language, file_path, qualified_name, f"{signature}@{start_line}",
    )
