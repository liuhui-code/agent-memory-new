# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from .code_wiki_component_flow import extract_component_property_bindings
from .models import Project


def insert_design_edges(
    conn: sqlite3.Connection,
    project: Project,
    scoped_files: list[sqlite3.Row],
    all_files: list[sqlite3.Row],
    symbols: list[sqlite3.Row],
    timestamp: str,
) -> None:
    file_ids = {str(row["file_path"]): int(row["id"]) for row in all_files}
    symbols_by_name: dict[str, list[sqlite3.Row]] = {}
    symbols_by_file: dict[str, dict[str, sqlite3.Row]] = {}
    for row in symbols:
        symbols_by_name.setdefault(str(row["symbol"]), []).append(row)
        symbols_by_file.setdefault(str(row["file_path"]), {})[str(row["symbol"])] = row
    config_ids = {
        str(row["file_path"]): int(row["id"])
        for row in all_files if row["language"] == "HarmonyOS Config"
    }
    ability_configs = {
        str(row["symbol"]): config_ids[str(row["file_path"])]
        for row in symbols
        if row["symbol_type"] == "ability" and str(row["file_path"]) in config_ids
    }
    emitted: set[tuple[str, int, str, str, int]] = set()
    for row in scoped_files:
        if row["language"] != "ArkTS":
            continue
        path = str(row["file_path"])
        source_id = int(row["id"])
        text = read_source(project, path)
        if text is None:
            continue
        insert_component_edges(conn, project, source_id, path, text, symbols_by_name, timestamp, emitted)
        insert_service_edges(conn, project, source_id, path, text, symbols_by_name, timestamp, emitted)
        insert_event_edges(conn, project, source_id, path, text, symbols_by_name, symbols_by_file, timestamp, emitted)
        insert_semantic_edges(conn, project, source_id, path, text, symbols_by_name, symbols_by_file, timestamp, emitted)
        insert_config_edges(conn, project, source_id, path, text, ability_configs, timestamp, emitted)
    insert_test_edges(conn, project, scoped_files, all_files, file_ids, timestamp, emitted)


def read_source(project: Project, path: str) -> str | None:
    try:
        return (project.root / path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def insert_component_edges(
    conn: sqlite3.Connection,
    project: Project,
    source_id: int,
    source_path: str,
    text: str,
    symbols_by_name: dict[str, list[sqlite3.Row]],
    timestamp: str,
    emitted: set[tuple[str, int, str, str, int]],
) -> None:
    names = set(re.findall(r"(?m)^\s*([A-Z][A-Za-z0-9_$]*)\s*\(", text))
    for name in names:
        targets = [row for row in symbols_by_name.get(name, []) if row["symbol_type"] == "component"]
        target = unique_target(targets)
        if target:
            insert_edge(
                conn, project.project_id, "code_file", source_id, "renders_component",
                "code_symbol", int(target["id"]), f"{source_path} renders {name}", 0.75,
                timestamp, emitted,
            )
    for binding in extract_component_property_bindings(text):
        targets = [
            row for row in symbols_by_name.get(binding.component, [])
            if row["symbol_type"] == "component"
        ]
        target = unique_target(targets)
        if target:
            properties = ", ".join(binding.properties[:8])
            insert_edge(
                conn, project.project_id, "code_file", source_id, "passes_property",
                "code_symbol", int(target["id"]),
                f"{source_path} passes {properties} to {binding.component}", 0.85,
                timestamp, emitted,
            )


def insert_service_edges(
    conn: sqlite3.Connection,
    project: Project,
    source_id: int,
    source_path: str,
    text: str,
    symbols_by_name: dict[str, list[sqlite3.Row]],
    timestamp: str,
    emitted: set[tuple[str, int, str, str, int]],
) -> None:
    pattern = r"(?:\bnew\s+|:\s*)([A-Z][A-Za-z0-9_$]*(?:Service|Repository|Store|Manager|Client))\b"
    for name in set(re.findall(pattern, text)):
        targets = [row for row in symbols_by_name.get(name, []) if row["symbol_type"] in {"class", "component"}]
        target = unique_target(targets)
        if target:
            insert_edge(
                conn, project.project_id, "code_file", source_id, "uses_service",
                "code_symbol", int(target["id"]), f"{source_path} uses {name}", 0.75,
                timestamp, emitted,
            )


def insert_event_edges(
    conn: sqlite3.Connection,
    project: Project,
    source_id: int,
    source_path: str,
    text: str,
    symbols_by_name: dict[str, list[sqlite3.Row]],
    symbols_by_file: dict[str, dict[str, sqlite3.Row]],
    timestamp: str,
    emitted: set[tuple[str, int, str, str, int]],
) -> None:
    local = symbols_by_file.get(source_path, {})
    for event_name in set(re.findall(r"\bthis\.(on[A-Z][A-Za-z0-9_$]*)\s*\(", text)):
        target = local.get(event_name)
        if target and target["symbol_type"] == "event":
            insert_edge(
                conn, project.project_id, "code_file", source_id, "dispatches_event",
                "code_symbol", int(target["id"]), f"{source_path} dispatches {event_name}",
                0.8, timestamp, emitted,
            )
    bindings = re.findall(r"\b(on[A-Z][A-Za-z0-9_$]*)\s*:\s*(?:this\.)?([A-Za-z_$][A-Za-z0-9_$]*)", text)
    for event_name, handler in bindings:
        target = unique_target([row for row in symbols_by_name.get(event_name, []) if row["symbol_type"] == "event"])
        if target:
            insert_edge(
                conn, project.project_id, "code_file", source_id, "handles_event",
                "code_symbol", int(target["id"]), f"{source_path} binds {handler} to {event_name}",
                0.7, timestamp, emitted,
            )


def insert_config_edges(
    conn: sqlite3.Connection,
    project: Project,
    source_id: int,
    source_path: str,
    text: str,
    ability_configs: dict[str, int],
    timestamp: str,
    emitted: set[tuple[str, int, str, str, int]],
) -> None:
    declared = set(re.findall(r"\bclass\s+([A-Za-z_$][A-Za-z0-9_$]*)", text))
    for ability in declared:
        target_id = ability_configs.get(ability)
        if target_id:
            insert_edge(
                conn, project.project_id, "code_file", source_id, "configured_by",
                "code_file", target_id, f"{source_path} configured by {ability}",
                0.8, timestamp, emitted,
            )


def insert_semantic_edges(
    conn: sqlite3.Connection,
    project: Project,
    source_id: int,
    source_path: str,
    text: str,
    symbols_by_name: dict[str, list[sqlite3.Row]],
    symbols_by_file: dict[str, dict[str, sqlite3.Row]],
    timestamp: str,
    emitted: set[tuple[str, int, str, str, int]],
) -> None:
    local = symbols_by_file.get(source_path, {})
    for state in [row for row in local.values() if row["symbol_type"] == "state"]:
        name = str(state["symbol"])
        if re.search(rf"\bthis\.{re.escape(name)}\s*(?:=|\+=|-=|\+\+|--)", text):
            emit_file_symbol(conn, project, source_id, "writes_state", state, source_path, 0.85, timestamp, emitted)
        read_pattern = rf"\bthis\.{re.escape(name)}\b(?!\s*(?:=|\+=|-=|\+\+|--))"
        if re.search(read_pattern, text):
            emit_file_symbol(conn, project, source_id, "reads_state", state, source_path, 0.8, timestamp, emitted)
    for name in set(re.findall(r"\bthis\.([A-Za-z_$][A-Za-z0-9_$]*)\s*\(", text)):
        target = local.get(name)
        if target and target["symbol_type"] == "function":
            emit_file_symbol(conn, project, source_id, "calls", target, source_path, 0.85, timestamp, emitted)
    for name in set(re.findall(r"\.(?:onClick|onChange|onSubmit|onTouch)\s*\([^)]*\bthis\.([A-Za-z_$][A-Za-z0-9_$]*)", text)):
        target = local.get(name)
        if target and target["symbol_type"] == "function":
            emit_file_symbol(conn, project, source_id, "registers_callback", target, source_path, 0.8, timestamp, emitted)
    exported = re.findall(r"(?m)^\s*export\s+(?:default\s+)?(?:class|struct|function)\s+([A-Za-z_$][A-Za-z0-9_$]*)", text)
    for name in set(exported):
        target = local.get(name)
        if target:
            emit_file_symbol(conn, project, source_id, "exposes_api", target, source_path, 0.9, timestamp, emitted)
    imported = re.findall(r"(?m)^\s*import\s*\{([^}]+)\}\s*from\s*['\"]", text)
    for block in imported:
        for raw_name in block.split(","):
            name = raw_name.strip().split(" as ", 1)[0].strip()
            target = unique_target(symbols_by_name.get(name, []))
            if target:
                emit_file_symbol(conn, project, source_id, "consumes_api", target, source_path, 0.85, timestamp, emitted)
    for source_name, target_name in re.findall(
        r"\bclass\s+([A-Za-z_$][A-Za-z0-9_$]*)[^\n{]*\bimplements\s+([A-Za-z_$][A-Za-z0-9_$]*)", text
    ):
        source = local.get(source_name)
        target = unique_target([row for row in symbols_by_name.get(target_name, []) if row["file_path"] != source_path])
        if source and target:
            insert_edge(conn, project.project_id, "code_symbol", int(source["id"]), "implements", "code_symbol",
                        int(target["id"]), f"{source_name} implements {target_name}", 0.85, timestamp, emitted)
    for name in set(re.findall(r"(?m)^\s*override\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(", text)):
        source = local.get(name)
        target = unique_target([row for row in symbols_by_name.get(name, []) if row["file_path"] != source_path])
        if source and target:
            insert_edge(conn, project.project_id, "code_symbol", int(source["id"]), "overrides", "code_symbol",
                        int(target["id"]), f"{source_path} overrides {name}", 0.75, timestamp, emitted)


def emit_file_symbol(
    conn: sqlite3.Connection,
    project: Project,
    source_id: int,
    relation: str,
    target: sqlite3.Row,
    source_path: str,
    confidence: float,
    timestamp: str,
    emitted: set[tuple[str, int, str, str, int]],
) -> None:
    insert_edge(
        conn, project.project_id, "code_file", source_id, relation, "code_symbol", int(target["id"]),
        f"{source_path} {relation} {target['symbol']}", confidence, timestamp, emitted,
    )


def insert_test_edges(
    conn: sqlite3.Connection,
    project: Project,
    scoped_files: list[sqlite3.Row],
    all_files: list[sqlite3.Row],
    file_ids: dict[str, int],
    timestamp: str,
    emitted: set[tuple[str, int, str, str, int]],
) -> None:
    code_rows = [row for row in all_files if is_code_language(str(row["language"] or ""))]
    tests = [row for row in code_rows if is_test_path(str(row["file_path"]))]
    production = [row for row in code_rows if not is_test_path(str(row["file_path"]))]
    scoped_paths = {str(row["file_path"]) for row in scoped_files}
    module_markers = module_marker_paths(all_files)
    tests_by_key: dict[tuple[str, str], list[sqlite3.Row]] = {}
    for test in tests:
        path = str(test["file_path"])
        key = (module_root(path, module_markers), normalized_stem(path))
        tests_by_key.setdefault(key, []).append(test)
    production_by_key: dict[tuple[str, str], list[sqlite3.Row]] = {}
    for source in production:
        source_path = str(source["file_path"])
        key = (module_root(source_path, module_markers), normalized_stem(source_path))
        production_by_key.setdefault(key, []).append(source)
    for key, sources in production_by_key.items():
        if len(sources) != 1 or len(key[1]) < 3:
            continue
        source = sources[0]
        source_path = str(source["file_path"])
        for test in tests_by_key.get(key, []):
            test_path = str(test["file_path"])
            if source_path not in scoped_paths and test_path not in scoped_paths:
                continue
            insert_edge(
                conn, project.project_id, "code_file", int(source["id"]), "tested_by",
                "code_file", file_ids[test_path], f"{source_path} tested by {test_path}",
                0.75, timestamp, emitted,
            )


def normalized_stem(path: str) -> str:
    stem = Path(path).stem.lower()
    return re.sub(r"(?:[._-]?(?:test|tests|spec|specs))$", "", stem)


def is_test_path(path: str) -> bool:
    parts = {part.lower() for part in Path(path).parts[:-1]}
    if parts & {"test", "tests", "ohostest", "unittest", "uitest"}:
        return True
    stem = Path(path).stem
    return bool(re.search(r"(?:^|[._-])(?:test|spec)s?$|(?:test|spec)s?$", stem, re.IGNORECASE))


def is_code_language(language: str) -> bool:
    return language in {"ArkTS", "TypeScript", "JavaScript", "Python", "Dart", "Swift"}


def module_marker_paths(rows: list[sqlite3.Row]) -> set[str]:
    markers = {"oh-package.json5", "build-profile.json5", "package.json", "pyproject.toml"}
    roots = {
        Path(str(row["file_path"])).parent.as_posix()
        for row in rows
        if Path(str(row["file_path"])).name.lower() in markers
    }
    return {"" if root == "." else root for root in roots}


def module_root(path: str, markers: set[str]) -> str:
    candidate = Path(path).parent
    for parent in (candidate, *candidate.parents):
        normalized = "" if parent == Path(".") else parent.as_posix()
        if normalized in markers:
            return normalized
    return ""


def unique_target(rows: list[sqlite3.Row]) -> sqlite3.Row | None:
    return rows[0] if len(rows) == 1 else None


def insert_edge(
    conn: sqlite3.Connection,
    project_id: str,
    source_type: str,
    source_id: int,
    relation: str,
    target_type: str,
    target_id: int,
    evidence: str,
    confidence: float,
    timestamp: str,
    emitted: set[tuple[str, int, str, str, int]],
) -> None:
    key = (source_type, source_id, relation, target_type, target_id)
    if key in emitted:
        return
    emitted.add(key)
    conn.execute(
        """
        INSERT INTO memory_edges(
          project_id, source_type, source_id, relation, target_type,
          target_id, evidence, confidence, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (project_id, source_type, source_id, relation, target_type, target_id, evidence, confidence, timestamp),
    )
