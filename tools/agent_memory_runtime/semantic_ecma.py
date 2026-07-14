# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Project
from .semantic_models import MAX_GAPS, SemanticBatch, SemanticEntity, SemanticRelation, source_digest, symbol_key


CONTAINER_RE = re.compile(
    r"^\s*(export\s+)?(?:default\s+)?(class|struct|interface)\s+([A-Za-z_$][\w$]*)"
    r"(?:\s+extends\s+([A-Za-z_$][\w$]*))?(?:[^\n{]*?\s+implements\s+([^\n{]+))?"
)
METHOD_RE = re.compile(
    r"^\s*(?:(public|private|protected)\s+)?(override\s+)?(async\s+)?"
    r"([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*(?::\s*([^\s{]+))?\s*\{"
)
FUNCTION_RE = re.compile(
    r"^\s*(export\s+)?(?:default\s+)?(async\s+)?function\s+"
    r"([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*(?::\s*([^\s{]+))?\s*\{"
)
STATE_RE = re.compile(r"@(?:State|Prop|Link|Provide|Consume|ObjectLink|Local|Param)\s+([A-Za-z_$][\w$]*)")
FIELD_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|readonly|static)\s+)*([A-Za-z_$][\w$]*)\s*:\s*([A-Za-z_$][\w$<>,.? ]*)"
)
IMPORT_RE = re.compile(r"(?m)^\s*import\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]")
CONTROL_NAMES = {"if", "for", "while", "switch", "catch"}


@dataclass
class Container:
    name: str
    kind: str
    start: int
    end: int
    exported: bool
    extends: str | None
    implements: list[str]
    entity: SemanticEntity


@dataclass
class CallableBlock:
    owner: str | None
    start: int
    end: int
    entity: SemanticEntity
    override: bool = False


@dataclass
class ParsedFile:
    path: str
    text: str
    digest: str
    entities: list[SemanticEntity]
    relations: list[SemanticRelation]
    gaps: list[dict[str, str]]


@dataclass(frozen=True)
class ParsedFileContext:
    fields_by_owner: dict[str, dict[str, str]]
    state_names_by_owner: dict[str, tuple[str, ...]]
    imported_paths: dict[str, str | None]


def index_ecma_files(
    project: Project,
    files: list[Path],
    adapter: Any,
    state_annotations: bool,
) -> SemanticBatch:
    parsed = [parse_file(project, path, adapter.language, state_annotations) for path in sorted(set(files))]
    batch = SemanticBatch(
        adapter_id=adapter.adapter_id,
        adapter_version=adapter.adapter_version,
        language=adapter.language,
        capabilities=list(adapter.capabilities),
        source_digests={item.path: item.digest for item in parsed},
        entities=[entity for item in parsed for entity in item.entities],
        relations=[relation for item in parsed for relation in item.relations],
        gaps=bounded_gaps([gap for item in parsed for gap in item.gaps]),
    )
    return batch.validate()


def bounded_gaps(gaps: list[dict[str, str]]) -> list[dict[str, str]]:
    return gaps[:MAX_GAPS]


def parse_file(project: Project, path: Path, language: str, state_annotations: bool) -> ParsedFile:
    text = path.read_text(encoding="utf-8", errors="ignore")
    rel_path = path.relative_to(project.root).as_posix()
    lines = text.splitlines()
    entities: list[SemanticEntity] = []
    relations: list[SemanticRelation] = []
    gaps: list[dict[str, str]] = []
    containers = parse_containers(lines, language, rel_path)
    entities.extend(container.entity for container in containers)
    callables: list[CallableBlock] = []
    for container in containers:
        methods, states = parse_container_members(lines, language, rel_path, container, state_annotations)
        callables.extend(methods)
        entities.extend(block.entity for block in methods)
        entities.extend(states)
        relations.extend(inheritance_relations(container, methods))
    top_level = parse_top_level_functions(lines, language, rel_path, containers)
    callables.extend(top_level)
    entities.extend(block.entity for block in top_level)
    imports = parse_imports(project, path, text, language)
    by_qualified = {entity.qualified_name: entity for entity in entities}
    by_name = unique_entity_names(entities)
    context = build_file_context(lines, containers, entities, imports)
    for entity in entities:
        if entity.exported:
            relations.append(relation(f"file:{rel_path}", "exposes_api", entity.key, entity.start_line, 0.95, "exported symbol"))
    for name, alias, target_path in imports:
        relations.append(SemanticRelation(
            source_key=f"file:{rel_path}", relation="consumes_api", target_name=name,
            target_file_path=target_path, line=1, confidence=0.9,
            detail=f"imports {name} as {alias}",
        ))
    for block in callables:
        relations.extend(callable_relations(lines, block, context, by_qualified, by_name, gaps))
    return ParsedFile(
        path=rel_path,
        text=text,
        digest=source_digest(text),
        entities=dedupe_entities(entities),
        relations=dedupe_relations(relations),
        gaps=gaps,
    )


def parse_containers(lines: list[str], language: str, file_path: str) -> list[Container]:
    result: list[Container] = []
    for index, line in enumerate(lines):
        match = CONTAINER_RE.match(line)
        if not match:
            continue
        exported, raw_kind, name, extends, implements = match.groups()
        end = block_end(lines, index)
        kind = "component" if raw_kind == "struct" and language == "ArkTS" else raw_kind
        signature = f"{raw_kind} {name}"
        entity = make_entity(language, file_path, name, kind, name, signature, index + 1, end + 1, bool(exported))
        result.append(Container(
            name=name, kind=kind, start=index, end=end, exported=bool(exported), extends=extends,
            implements=[item.strip() for item in (implements or "").split(",") if item.strip()],
            entity=entity,
        ))
    return result


def parse_container_members(
    lines: list[str],
    language: str,
    file_path: str,
    container: Container,
    state_annotations: bool,
) -> tuple[list[CallableBlock], list[SemanticEntity]]:
    methods: list[CallableBlock] = []
    states: list[SemanticEntity] = []
    index = container.start + 1
    while index < container.end:
        line = lines[index]
        method = METHOD_RE.match(line)
        if method and method.group(4) not in CONTROL_NAMES:
            visibility, override, async_value, name, params, return_type = method.groups()
            end = min(block_end(lines, index), container.end)
            qualified = f"{container.name}.{name}"
            signature = callable_signature(name, params, return_type, bool(async_value))
            exported = container.exported and visibility != "private"
            entity = make_entity(language, file_path, name, "function", qualified, signature, index + 1, end + 1, exported)
            methods.append(CallableBlock(container.name, index, end, entity, bool(override)))
            index = end + 1
            continue
        if state_annotations:
            state = STATE_RE.search(line)
            if state:
                name = state.group(1)
                qualified = f"{container.name}.{name}"
                states.append(make_entity(language, file_path, name, "state", qualified, name, index + 1, index + 1, False))
        index += 1
    return methods, states


def parse_top_level_functions(
    lines: list[str],
    language: str,
    file_path: str,
    containers: list[Container],
) -> list[CallableBlock]:
    result: list[CallableBlock] = []
    index = 0
    container_index = 0
    while index < len(lines):
        while container_index < len(containers) and containers[container_index].end < index:
            container_index += 1
        if container_index < len(containers) and containers[container_index].start <= index:
            index = containers[container_index].end + 1
            continue
        match = FUNCTION_RE.match(lines[index])
        if not match:
            index += 1
            continue
        exported, async_value, name, params, return_type = match.groups()
        end = block_end(lines, index)
        signature = callable_signature(name, params, return_type, bool(async_value))
        entity = make_entity(language, file_path, name, "function", name, signature, index + 1, end + 1, bool(exported))
        result.append(CallableBlock(None, index, end, entity))
        index = end + 1
    return result


def inheritance_relations(container: Container, methods: list[CallableBlock]) -> list[SemanticRelation]:
    result: list[SemanticRelation] = []
    if container.extends:
        result.append(SemanticRelation(
            source_key=container.entity.key, relation="extends", target_name=container.extends,
            target_qualified_name=container.extends, line=container.start + 1, confidence=0.9,
            detail=f"{container.name} extends {container.extends}",
        ))
    for name in container.implements:
        result.append(SemanticRelation(
            source_key=container.entity.key, relation="implements", target_name=name,
            target_qualified_name=name, line=container.start + 1, confidence=0.9,
            detail=f"{container.name} implements {name}",
        ))
    if container.extends:
        for method in methods:
            if method.override:
                result.append(SemanticRelation(
                    source_key=method.entity.key, relation="overrides", target_name=method.entity.name,
                    target_qualified_name=f"{container.extends}.{method.entity.name}",
                    line=method.start + 1, confidence=0.9, detail="explicit override",
                ))
    return result


def callable_relations(
    lines: list[str],
    block: CallableBlock,
    context: ParsedFileContext,
    by_qualified: dict[str, SemanticEntity],
    by_name: dict[str, SemanticEntity],
    gaps: list[dict[str, str]],
) -> list[SemanticRelation]:
    result: list[SemanticRelation] = []
    body = "\n".join(lines[block.start:block.end + 1])
    fields = context.fields_by_owner.get(block.owner or "", {})
    imported_paths = context.imported_paths
    local_prefix = f"{block.owner}." if block.owner else ""
    for name in set(re.findall(r"\bthis\.([A-Za-z_$][\w$]*)\s*\(", body)):
        target = by_qualified.get(local_prefix + name)
        if target:
            result.append(relation(block.entity.key, "calls", target.key, block.start + 1, 0.95, "local method call"))
    typed_calls = re.findall(r"\b(?:this\.)?([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)\s*\(", body)
    for field_name, method_name in typed_calls:
        type_name = fields.get(field_name)
        if not type_name or field_name == "this":
            continue
        result.append(SemanticRelation(
            source_key=block.entity.key, relation="calls", target_name=method_name,
            target_qualified_name=f"{type_name}.{method_name}", target_file_path=imported_paths.get(type_name),
            line=block.start + 1, confidence=0.9, detail=f"typed field call through {field_name}",
        ))
    if block.owner:
        for name in context.state_names_by_owner.get(block.owner, ()):
            target = by_qualified.get(local_prefix + name)
            if not target:
                continue
            if re.search(rf"\bthis\.{re.escape(name)}\s*(?:=|\+=|-=|\+\+|--)", body):
                result.append(relation(block.entity.key, "writes_state", target.key, block.start + 1, 0.95, "state assignment"))
            if re.search(rf"\bthis\.{re.escape(name)}\b(?!\s*(?:=|\+=|-=|\+\+|--))", body):
                result.append(relation(block.entity.key, "reads_state", target.key, block.start + 1, 0.9, "state read"))
    callbacks = set(re.findall(r"\.(?:onClick|onChange|onSubmit|onTouch)\s*\([^)]*\bthis\.([A-Za-z_$][\w$]*)", body))
    for name in callbacks:
        target = by_qualified.get(local_prefix + name)
        if target:
            result.append(relation(block.entity.key, "registers_callback", target.key, block.start + 1, 0.9, "callback registration"))
    for awaited in re.findall(r"\bawait\s+(?:this\.)?([A-Za-z_$][\w$]*)\s*\(", body):
        target = by_qualified.get(local_prefix + awaited) or by_name.get(awaited)
        if target:
            result.append(relation(block.entity.key, "awaits", target.key, block.start + 1, 0.95, "await expression"))
        else:
            gaps.append({"kind": "unresolved_await_target", "file_path": block.entity.file_path, "symbol": awaited})
    typed_awaits = re.findall(
        r"\bawait\s+(?:this\.)?([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)\s*\(", body
    )
    for field_name, method_name in typed_awaits:
        type_name = fields.get(field_name)
        if not type_name:
            gaps.append({
                "kind": "unresolved_await_target", "file_path": block.entity.file_path,
                "symbol": f"{field_name}.{method_name}",
            })
            continue
        result.append(SemanticRelation(
            source_key=block.entity.key, relation="awaits", target_name=method_name,
            target_qualified_name=f"{type_name}.{method_name}", target_file_path=imported_paths.get(type_name),
            line=block.start + 1, confidence=0.9, detail=f"typed awaited call through {field_name}",
        ))
    return result


def build_file_context(
    lines: list[str],
    containers: list[Container],
    entities: list[SemanticEntity],
    imports: list[tuple[str, str, str | None]],
) -> ParsedFileContext:
    fields_by_owner = {
        container.name: container_fields(lines, container)
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
    )


def parse_imports(project: Project, path: Path, text: str, language: str) -> list[tuple[str, str, str | None]]:
    result: list[tuple[str, str, str | None]] = []
    extensions = [".ets", ".ts", ".js"] if language == "ArkTS" else [".ts", ".tsx", ".js"]
    for block, module in IMPORT_RE.findall(text):
        target_path = resolve_relative_module(project, path, module, extensions)
        for raw in block.split(","):
            parts = re.split(r"\s+as\s+", raw.strip())
            if parts and parts[0]:
                result.append((parts[0], parts[-1], target_path))
    return result


def resolve_relative_module(project: Project, path: Path, module: str, extensions: list[str]) -> str | None:
    if not module.startswith("."):
        return None
    base = (path.parent / module).resolve()
    candidates = [base.with_suffix(ext) for ext in extensions]
    candidates.extend(base / f"index{ext}" for ext in extensions)
    for candidate in candidates:
        if candidate.exists():
            try:
                return candidate.relative_to(project.root).as_posix()
            except ValueError:
                return None
    return None


def container_fields(lines: list[str], container: Container | None) -> dict[str, str]:
    if not container:
        return {}
    result: dict[str, str] = {}
    for line in lines[container.start + 1:container.end]:
        match = FIELD_RE.match(line)
        if match and "(" not in line.split(":", 1)[0]:
            result[match.group(1)] = re.split(r"[<,?. ]", match.group(2).strip())[0]
    return result


def block_end(lines: list[str], start: int) -> int:
    depth = 0
    opened = False
    for index in range(start, len(lines)):
        depth += lines[index].count("{") - lines[index].count("}")
        opened = opened or "{" in lines[index]
        if opened and depth <= 0:
            return index
    return start


def callable_signature(name: str, params: str, return_type: str | None, async_value: bool) -> str:
    prefix = "async " if async_value else ""
    normalized_params = re.sub(r"\s+", " ", params.strip())
    return f"{prefix}{name}({normalized_params}):{return_type or 'unknown'}"


def make_entity(
    language: str,
    file_path: str,
    name: str,
    kind: str,
    qualified_name: str,
    signature: str,
    start_line: int,
    end_line: int,
    exported: bool,
) -> SemanticEntity:
    return SemanticEntity(
        key=symbol_key(language, file_path, qualified_name, signature), file_path=file_path,
        name=name, kind=kind, qualified_name=qualified_name, signature=signature,
        start_line=start_line, end_line=end_line, exported=exported,
    )


def relation(source: str, kind: str, target: str, line: int, confidence: float, detail: str) -> SemanticRelation:
    return SemanticRelation(
        source_key=source, relation=kind, target_key=target, line=line,
        confidence=confidence, detail=detail,
    )


def unique_entity_names(entities: list[SemanticEntity]) -> dict[str, SemanticEntity]:
    grouped: dict[str, list[SemanticEntity]] = {}
    for entity in entities:
        grouped.setdefault(entity.name, []).append(entity)
    return {name: values[0] for name, values in grouped.items() if len(values) == 1}


def dedupe_entities(items: list[SemanticEntity]) -> list[SemanticEntity]:
    return list({item.key: item for item in items}.values())


def dedupe_relations(items: list[SemanticRelation]) -> list[SemanticRelation]:
    result: dict[tuple[str, str, str, str], SemanticRelation] = {}
    for item in items:
        target = item.target_key or item.target_qualified_name or item.target_name or ""
        result[(item.source_key, item.relation, target, item.target_file_path or "")] = item
    return list(result.values())
