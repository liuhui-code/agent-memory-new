# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from .semantic_models import (
    MAX_GAPS, MAX_RELATIONS, SemanticBatch, SemanticEntity, SemanticRelation,
)
from .source_call_scanner import call_argument_count


MAX_DISPATCH_CANDIDATES = 8
MAX_HIERARCHY_DEPTH = 4
DISPATCH_RELATIONS = {"calls", "awaits"}
HIERARCHY_RELATIONS = {"extends", "implements"}


@dataclass(frozen=True)
class DispatchCatalog:
    entities_by_qualified: dict[str, SemanticEntity]
    dispatch_methods: dict[tuple[str, str, int | None], list[SemanticEntity]]
    parent_types: set[str]


def build_dispatch_catalog(batches: list[SemanticBatch]) -> DispatchCatalog:
    entities = [item for batch in batches for item in batch.entities]
    relations = [item for batch in batches for item in batch.relations]
    entities_by_key = {item.key: item for item in entities}
    methods = _methods_by_owner_and_name(entities)
    parents = _parent_types(relations, entities_by_key)
    return DispatchCatalog(
        entities_by_qualified={item.qualified_name: item for item in entities},
        dispatch_methods=_dispatch_methods(methods, parents),
        parent_types={parent for values in parents.values() for parent in values},
    )


def expand_dispatch_candidates(
    batch: SemanticBatch,
    catalog: DispatchCatalog | None = None,
) -> SemanticBatch:
    catalog = catalog or build_dispatch_catalog([batch])
    entities_by_key = {item.key: item for item in batch.entities}
    existing_keys = {_relation_key(item) for item in batch.relations}
    expanded: list[SemanticRelation] = []
    emitted = 0
    source_relations = list(batch.relations)
    for index, relation in enumerate(source_relations):
        candidates = _relation_candidates(relation, catalog.dispatch_methods)
        contract = _dispatch_contract_relation(
            relation, candidates, catalog.parent_types, catalog.entities_by_qualified,
        )
        expanded.append(relation)
        reserved = len(source_relations) - index - 1
        available = max(0, MAX_RELATIONS - len(expanded) - reserved)
        if contract and _relation_key(contract) not in existing_keys and available:
            expanded.append(contract)
            existing_keys.add(_relation_key(contract))
            available -= 1
        selected, truncated = _select_candidate_relations(
            relation, candidates, existing_keys,
            min(MAX_DISPATCH_CANDIDATES, available),
        )
        expanded.extend(selected)
        existing_keys.update(_relation_key(item) for item in selected)
        emitted += len(selected)
        if truncated and len(batch.gaps) < MAX_GAPS:
            source = entities_by_key.get(relation.source_key)
            batch.gaps.append({
                "kind": "dispatch_candidates_truncated",
                "file_path": source.file_path if source else "",
                "symbol": relation.target_qualified_name or relation.target_name or "unknown",
            })
    if emitted:
        batch.capabilities.append("dispatch_candidates")
    batch.relations = _dedupe_relations(expanded)
    return batch


def expand_dispatch_candidates_across_batches(batches: list[SemanticBatch]) -> None:
    by_language: dict[str, list[SemanticBatch]] = defaultdict(list)
    for batch in batches:
        if batch.adapter_id in {"arkts-static", "typescript-static"}:
            by_language[batch.language].append(batch)
    for language_batches in by_language.values():
        for batch in language_batches:
            _reset_dispatch_projection(batch)
        catalog = build_dispatch_catalog(language_batches)
        for batch in language_batches:
            expand_dispatch_candidates(batch, catalog).validate()


def _reset_dispatch_projection(batch: SemanticBatch) -> None:
    batch.relations = [
        item for item in batch.relations
        if item.relation != "dispatches_via"
        and not (
            item.evidence_class == "inferred"
            and item.detail.startswith("bounded CHA dispatch candidate:")
        )
    ]
    batch.capabilities = [item for item in batch.capabilities if item != "dispatch_candidates"]
    batch.gaps = [item for item in batch.gaps if item.get("kind") != "dispatch_candidates_truncated"]


def _dispatch_contract_relation(
    source: SemanticRelation,
    candidates: list[SemanticEntity],
    parent_types: set[str],
    entities_by_qualified: dict[str, SemanticEntity],
) -> SemanticRelation | None:
    qualified = source.target_qualified_name or ""
    receiver, separator, _method = qualified.rpartition(".")
    receiver_entity = entities_by_qualified.get(receiver)
    known_parent = receiver in parent_types
    if source.relation not in DISPATCH_RELATIONS or not separator:
        return None
    if not candidates and not known_parent and getattr(receiver_entity, "kind", "") != "interface":
        return None
    return SemanticRelation(
        source_key=source.source_key,
        relation="dispatches_via",
        target_key=receiver_entity.key if receiver_entity else None,
        target_name=receiver.rsplit(".", 1)[-1],
        target_qualified_name=receiver,
        target_file_path=receiver_entity.file_path if receiver_entity else source.target_file_path,
        line=source.line,
        confidence=0.8,
        evidence_class="static",
        detail=f"static receiver type for {qualified}",
    )


def _methods_by_owner_and_name(
    entities: list[SemanticEntity],
) -> dict[tuple[str, str], list[SemanticEntity]]:
    result: dict[tuple[str, str], list[SemanticEntity]] = defaultdict(list)
    for entity in entities:
        if entity.kind in {"function", "method"} and entity.owner_name:
            result[(entity.owner_name, entity.name)].append(entity)
    return result


def _parent_types(
    relations: list[SemanticRelation],
    entities_by_key: dict[str, SemanticEntity],
) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for relation in relations:
        if relation.relation not in HIERARCHY_RELATIONS:
            continue
        source = entities_by_key.get(relation.source_key)
        parent = relation.target_qualified_name or relation.target_name
        if source and parent:
            result[source.name].add(parent)
    return result


def _dispatch_methods(
    methods: dict[tuple[str, str], list[SemanticEntity]],
    parents: dict[str, set[str]],
) -> dict[tuple[str, str, int | None], list[SemanticEntity]]:
    result: dict[tuple[str, str, int | None], list[SemanticEntity]] = defaultdict(list)
    for (owner, name), owner_methods in methods.items():
        for ancestor in _ancestor_types(owner, parents):
            for method in owner_methods:
                arity = call_argument_count(method.signature)
                result[(ancestor, name, None)].append(method)
                if arity is not None:
                    result[(ancestor, name, arity)].append(method)
    return {
        key: sorted(
            {item.key: item for item in values}.values(),
            key=lambda item: (item.file_path, item.qualified_name, item.signature),
        )
        for key, values in result.items()
    }


def _relation_candidates(
    relation: SemanticRelation,
    dispatch_methods: dict[tuple[str, str, int | None], list[SemanticEntity]],
) -> list[SemanticEntity]:
    if relation.relation not in DISPATCH_RELATIONS or not relation.target_qualified_name:
        return []
    receiver, separator, method_name = relation.target_qualified_name.rpartition(".")
    if not separator or not receiver or not method_name:
        return []
    arity = _relation_arity(relation)
    return dispatch_methods.get((receiver, method_name, arity), [])


def _select_candidate_relations(
    source: SemanticRelation,
    candidates: list[SemanticEntity],
    existing_keys: set[tuple[str, str, str, str]],
    limit: int,
) -> tuple[list[SemanticRelation], bool]:
    selected: list[SemanticRelation] = []
    for candidate in candidates:
        item = _candidate_relation(source, candidate)
        if _relation_key(item) in existing_keys:
            continue
        if len(selected) >= limit:
            return selected, True
        selected.append(item)
    return selected, False


def _ancestor_types(owner: str, parents: dict[str, set[str]]) -> set[str]:
    frontier = [(owner, 0)]
    visited: set[str] = set()
    ancestors: set[str] = set()
    while frontier:
        current, depth = frontier.pop()
        if current in visited or depth >= MAX_HIERARCHY_DEPTH:
            continue
        visited.add(current)
        for parent in parents.get(current, set()):
            ancestors.add(parent)
            frontier.append((parent, depth + 1))
    return ancestors


def _relation_arity(relation: SemanticRelation) -> int | None:
    match = re.search(r"\barity=(\d+)\b", relation.detail)
    return int(match.group(1)) if match else None


def _candidate_relation(
    source: SemanticRelation,
    target: SemanticEntity,
) -> SemanticRelation:
    receiver = (source.target_qualified_name or "").rpartition(".")[0]
    return SemanticRelation(
        source_key=source.source_key,
        relation=source.relation,
        target_key=target.key,
        target_name=target.name,
        target_qualified_name=target.qualified_name,
        target_file_path=target.file_path,
        line=source.line,
        confidence=min(source.confidence, 0.55),
        evidence_class="inferred",
        detail=f"bounded CHA dispatch candidate: {target.owner_name} is a subtype of {receiver}",
    )


def _dedupe_relations(relations: list[SemanticRelation]) -> list[SemanticRelation]:
    result: dict[tuple[str, str, str, str], SemanticRelation] = {}
    for item in relations:
        result[_relation_key(item)] = item
    return list(result.values())


def _relation_key(item: SemanticRelation) -> tuple[str, str, str, str]:
    target = item.target_key or item.target_qualified_name or item.target_name or ""
    return item.source_key, item.relation, target, item.target_file_path or ""
