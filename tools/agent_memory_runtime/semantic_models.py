# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any


SEMANTIC_SCHEMA = "semantic-index/v1"
EVIDENCE_CLASSES = {"exact", "static", "heuristic", "inferred"}
MAX_FILES = 5000
MAX_ENTITIES = 50000
MAX_RELATIONS = 100000
MAX_MECHANISMS = 100000
MAX_GAPS = 1000
MECHANISM_KINDS = {
    "operation", "guard", "resource_bound", "callback_binding",
    "platform_predicate", "persistence_read", "persistence_write",
}


@dataclass(frozen=True)
class SemanticEntity:
    key: str
    file_path: str
    name: str
    kind: str
    qualified_name: str
    signature: str
    start_line: int
    end_line: int
    exported: bool = False
    evidence_class: str = "static"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticRelation:
    source_key: str
    relation: str
    target_key: str | None = None
    target_name: str | None = None
    target_qualified_name: str | None = None
    target_file_path: str | None = None
    line: int | None = None
    confidence: float = 0.9
    evidence_class: str = "static"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticMechanism:
    source_key: str
    kind: str
    terms: list[str]
    line: int
    confidence: float = 0.9
    evidence_class: str = "static"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticBatch:
    adapter_id: str
    adapter_version: str
    language: str
    capabilities: list[str]
    source_digests: dict[str, str]
    entities: list[SemanticEntity] = field(default_factory=list)
    relations: list[SemanticRelation] = field(default_factory=list)
    mechanisms: list[SemanticMechanism] = field(default_factory=list)
    gaps: list[dict[str, str]] = field(default_factory=list)
    schema_version: str = SEMANTIC_SCHEMA

    def validate(self) -> "SemanticBatch":
        if self.schema_version != SEMANTIC_SCHEMA:
            raise ValueError(f"unsupported semantic schema: {self.schema_version}")
        if not self.adapter_id or not self.adapter_version or not self.language:
            raise ValueError("semantic batch requires adapter id, version, and language")
        if len(self.source_digests) > MAX_FILES:
            raise ValueError(f"semantic batch exceeds {MAX_FILES} files")
        if (len(self.entities) > MAX_ENTITIES or len(self.relations) > MAX_RELATIONS
                or len(self.mechanisms) > MAX_MECHANISMS):
            raise ValueError("semantic batch exceeds entity, relation, or mechanism limits")
        if len(self.gaps) > MAX_GAPS:
            raise ValueError(f"semantic batch exceeds {MAX_GAPS} gaps")
        entities_by_key = {entity.key: entity for entity in self.entities}
        keys = set(entities_by_key)
        if len(keys) != len(self.entities):
            raise ValueError("semantic entity keys must be unique")
        for entity in self.entities:
            validate_entity(entity)
        for relation in self.relations:
            validate_relation(relation, keys)
        for mechanism in self.mechanisms:
            validate_mechanism(mechanism, entities_by_key)
        self.capabilities = sorted(set(self.capabilities))
        self.entities.sort(key=lambda item: (item.file_path, item.start_line, item.key))
        self.relations.sort(key=lambda item: (item.source_key, item.relation, item.target_key or item.target_qualified_name or "", item.line or 0))
        self.mechanisms.sort(key=lambda item: (item.source_key, item.line, item.kind, item.terms))
        self.gaps = self.gaps[:MAX_GAPS]
        return self

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "adapter": {"id": self.adapter_id, "version": self.adapter_version, "language": self.language},
            "capabilities": self.capabilities,
            "source_digests": dict(sorted(self.source_digests.items())),
            "entities": [item.to_dict() for item in self.entities],
            "relations": [item.to_dict() for item in self.relations],
            "mechanisms": [item.to_dict() for item in self.mechanisms],
            "gaps": self.gaps,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SemanticBatch":
        if not isinstance(value, dict) or value.get("schema_version") != SEMANTIC_SCHEMA:
            raise ValueError("unsupported or malformed semantic batch")
        adapter = value.get("adapter")
        if not isinstance(adapter, dict):
            raise ValueError("semantic batch adapter must be an object")
        entities = [SemanticEntity(**item) for item in require_object_list(value.get("entities"), "entities")]
        relations = [SemanticRelation(**item) for item in require_object_list(value.get("relations"), "relations")]
        mechanisms = [
            SemanticMechanism(**item)
            for item in optional_object_list(value.get("mechanisms"), "mechanisms")
        ]
        batch = cls(
            adapter_id=str(adapter.get("id") or ""),
            adapter_version=str(adapter.get("version") or ""),
            language=str(adapter.get("language") or ""),
            capabilities=require_string_list(value.get("capabilities"), "capabilities"),
            source_digests=require_string_map(value.get("source_digests"), "source_digests"),
            entities=entities,
            relations=relations,
            mechanisms=mechanisms,
            gaps=require_object_list(value.get("gaps"), "gaps"),
        )
        return batch.validate()


def validate_entity(entity: SemanticEntity) -> None:
    if not all((entity.key, entity.file_path, entity.name, entity.kind, entity.qualified_name)):
        raise ValueError("semantic entity identity fields must be non-empty")
    if entity.start_line < 1 or entity.end_line < entity.start_line:
        raise ValueError(f"invalid semantic entity span: {entity.key}")
    if entity.evidence_class not in EVIDENCE_CLASSES:
        raise ValueError(f"invalid entity evidence class: {entity.evidence_class}")


def validate_relation(relation: SemanticRelation, local_keys: set[str]) -> None:
    if not relation.source_key or not relation.relation:
        raise ValueError("semantic relation requires source key and relation")
    if not relation.target_key and not relation.target_name and not relation.target_qualified_name:
        raise ValueError("semantic relation requires a target key or lookup hint")
    if relation.target_key and relation.target_key.startswith("symbol:"):
        if relation.target_key not in local_keys and not re.fullmatch(r"symbol:[0-9a-f]{24}", relation.target_key):
            raise ValueError(f"semantic relation has an invalid external symbol key: {relation.target_key}")
    if relation.evidence_class not in EVIDENCE_CLASSES or not 0.0 <= relation.confidence <= 1.0:
        raise ValueError("semantic relation has invalid evidence class or confidence")


def validate_mechanism(
    mechanism: SemanticMechanism,
    local_entities: dict[str, SemanticEntity],
) -> None:
    entity = local_entities.get(mechanism.source_key)
    if entity is None:
        raise ValueError("semantic mechanism source must be a local entity")
    if entity.kind not in {"function", "method"}:
        raise ValueError("semantic mechanism source must be callable")
    if mechanism.kind not in MECHANISM_KINDS:
        raise ValueError(f"unsupported semantic mechanism: {mechanism.kind}")
    if mechanism.line < 1 or not 0.0 <= mechanism.confidence <= 1.0:
        raise ValueError("semantic mechanism has invalid line or confidence")
    if not entity.start_line <= mechanism.line <= entity.end_line:
        raise ValueError("semantic mechanism line must be inside its source entity")
    if mechanism.evidence_class not in EVIDENCE_CLASSES:
        raise ValueError("semantic mechanism has invalid evidence class")
    if not mechanism.terms or len(mechanism.terms) > 16:
        raise ValueError("semantic mechanism requires 1..16 terms")
    if any(not isinstance(term, str) or not term or len(term) > 64 for term in mechanism.terms):
        raise ValueError("semantic mechanism terms must be bounded strings")
    if not isinstance(mechanism.detail, str) or len(mechanism.detail) > 240:
        raise ValueError("semantic mechanism detail must be a bounded string")


def symbol_key(language: str, file_path: str, qualified_name: str, signature: str) -> str:
    identity = f"{language}:{file_path}::{qualified_name}|{signature}"
    return "symbol:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def source_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def require_object_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"semantic batch {label} must be an object list")
    return list(value)


def optional_object_list(value: Any, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    return require_object_list(value, label)


def require_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"semantic batch {label} must be a string list")
    return list(value)


def require_string_map(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or not all(isinstance(key, str) and isinstance(item, str) for key, item in value.items()):
        raise ValueError(f"semantic batch {label} must be a string map")
    return dict(value)
