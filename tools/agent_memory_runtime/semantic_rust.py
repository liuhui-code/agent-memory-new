# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from pathlib import Path

from .models import Project
from .rust_source import LIMITATION, rust_declarations
from .semantic_models import MAX_GAPS, SemanticBatch, SemanticEntity, source_digest, symbol_key


class RustSemanticAdapter:
    adapter_id = "rust-static"
    adapter_version = "1.0"
    language = "Rust"
    capabilities = ("definitions",)

    def index(self, project: Project, files: list[Path]) -> SemanticBatch:
        digests: dict[str, str] = {}
        entities: list[SemanticEntity] = []
        gaps = [{"kind": "rust_source_only", "detail": LIMITATION}]
        for path in sorted(set(files)):
            try:
                relative = path.resolve().relative_to(project.root.resolve()).as_posix()
                text = path.read_bytes().decode("utf-8")
            except UnicodeError:
                gaps.append({"kind": "rust_invalid_utf8", "file_path": relative})
                continue
            except (OSError, ValueError):
                continue
            digests[relative] = source_digest(text)
            for declaration in rust_declarations(text):
                entities.append(SemanticEntity(
                    key=symbol_key(self.language, relative, declaration.name, declaration.signature),
                    file_path=relative,
                    name=declaration.name,
                    kind=declaration.kind,
                    qualified_name=declaration.qualified_name,
                    signature=declaration.signature,
                    start_line=declaration.start_line,
                    end_line=declaration.end_line,
                    owner_name=declaration.owner_name,
                    owner_kind="source_scope" if declaration.owner_name else "",
                    evidence_class="static",
                ))
        return SemanticBatch(
            adapter_id=self.adapter_id, adapter_version=self.adapter_version,
            language=self.language, capabilities=list(self.capabilities),
            source_digests=digests, entities=entities,
            gaps=gaps[:MAX_GAPS],
        ).validate()
