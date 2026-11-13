# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from .semantic_models import SemanticEntity
if TYPE_CHECKING:
    from .semantic_ecma import Container
from .ecma_field_scope import collect_field_types
from .ecma_import_alias import alias_bindings
from .ecma_typed_import_alias import typed_alias_bindings

@dataclass(frozen=True)
class ParsedFileContext:
    fields_by_owner: dict[str, dict[str, str]]
    state_names_by_owner: dict[str, tuple[str, ...]]
    imported_paths: dict[str, str | None]
    imported_aliases: dict[str, str | None]
    typed_alias_fields: dict[str, dict[str, tuple[str, str]]]

def build_context(
    lines: list[str],
    containers: list[Container],
    entities: list[SemanticEntity],
    imports: list[tuple[str, str, str | None]],
    field_re,
) -> ParsedFileContext:
    fields_by_owner = {
        container.name: collect_field_types(lines, container, field_re)
        for container in containers
    }
    state_names: dict[str, list[str]] = {}
    for entity in entities:
        if entity.kind != "state" or "." not in entity.qualified_name:
            continue
        owner, _separator, _name = entity.qualified_name.partition(".")
        state_names.setdefault(owner, []).append(entity.name)
    return ParsedFileContext(
        fields_by_owner=fields_by_owner,
        state_names_by_owner={owner: tuple(names) for owner, names in state_names.items()},
        imported_paths={alias: path for _name, alias, path in imports},
        imported_aliases=alias_bindings(imports),
        typed_alias_fields=typed_alias_bindings(lines, containers, fields_by_owner, imports),
    )
