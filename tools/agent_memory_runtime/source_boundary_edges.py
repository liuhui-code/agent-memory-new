# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Iterable, TypeVar

from .models import Project
from .source_static_extractors import build_target_ranges


NATIVE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
SQL_CHUNK_SIZE = 300
T = TypeVar("T")


def insert_source_boundary_edges(
    conn: sqlite3.Connection,
    project: Project,
    scoped_files: list[sqlite3.Row],
    _candidate_files: list[sqlite3.Row],
    timestamp: str,
) -> None:
    paths_by_language = scoped_paths_by_language(scoped_files)
    arkts_paths = set(paths_by_language.get("ArkTS", []))
    native_paths = set(paths_by_language.get("C/C++", []))
    build_paths = set(paths_by_language.get("Build Artifact", []))
    config_paths = set(paths_by_language.get("HarmonyOS Config", []))

    modules = modules_for_arkts_paths(project, arkts_paths)
    cmake_paths = {path for path in build_paths if is_cmake(path)}
    cmake_paths.update(ancestor_cmake_paths(conn, project.project_id, native_paths))
    cmake_paths.update(symbol_file_paths(
        conn, project.project_id, "build_target", modules,
    ))
    native_targets = cmake_native_targets(project, cmake_paths)
    modules.update(native_targets)
    arkts_paths.update(symbol_file_paths(
        conn,
        project.project_id,
        "native_module",
        {f"lib{module}.so" for module in modules} | {f"{module}.so" for module in modules},
    ))

    package_names = packages_for_config_paths(project, config_paths)
    package_names.update(build_packages(project, build_paths))
    config_paths.update(symbol_file_paths(
        conn, project.project_id, "hnp_package", package_names,
    ))
    build_paths.update(symbol_file_paths(
        conn, project.project_id, "build_target", package_names,
    ))

    needed_paths = arkts_paths | config_paths | build_paths | cmake_paths
    needed_paths.update(
        source for targets in native_targets.values() for source, _config in targets
    )
    file_ids = code_file_ids(conn, project.project_id, needed_paths)
    rows: list[tuple[object, ...]] = []
    emitted = existing_edge_keys(conn, project.project_id, set(file_ids.values()))
    append_native_edges(
        rows, emitted, project, arkts_paths, native_targets, file_ids, timestamp,
    )
    append_package_edges(
        rows, emitted, project, config_paths, build_paths, file_ids, timestamp,
    )
    conn.executemany(
        """
        INSERT INTO memory_edges(
          project_id, source_type, source_id, relation, target_type,
          target_id, evidence, confidence, created_at
        ) VALUES (?, 'code_file', ?, ?, 'code_file', ?, ?, ?, ?)
        """,
        rows,
    )


def append_native_edges(
    rows: list[tuple[object, ...]],
    emitted: set[tuple[int, str, int]],
    project: Project,
    arkts_paths: set[str],
    native_targets: dict[str, list[tuple[str, str]]],
    file_ids: dict[str, int],
    timestamp: str,
) -> None:
    for source_path in sorted(arkts_paths):
        source_id = file_ids.get(source_path)
        if source_id is None:
            continue
        for module in native_imports(read_source(project, source_path)):
            for target_path, config_path in native_targets.get(module, []):
                target_id = file_ids.get(target_path)
                config_id = file_ids.get(config_path)
                if target_id is None or config_id is None:
                    continue
                add_edge(
                    rows, emitted, project.project_id, source_id, "imports", target_id,
                    f"{source_path} imports lib{module}.so via {config_path}", 0.9, timestamp,
                )
                add_edge(
                    rows, emitted, project.project_id, target_id, "configured_by", config_id,
                    f"{target_path} configured by {config_path}", 0.85, timestamp,
                )


def append_package_edges(
    rows: list[tuple[object, ...]],
    emitted: set[tuple[int, str, int]],
    project: Project,
    config_paths: set[str],
    build_paths: set[str],
    file_ids: dict[str, int],
    timestamp: str,
) -> None:
    targets = build_package_targets(project, build_paths)
    for source_path in sorted(config_paths):
        source_id = file_ids.get(source_path)
        if source_id is None:
            continue
        for package in hnp_packages(read_source(project, source_path)):
            matches = targets.get(package, [])
            if len(matches) != 1 or matches[0] not in file_ids:
                continue
            add_edge(
                rows, emitted, project.project_id, source_id, "configured_by",
                file_ids[matches[0]], f"{source_path} declares {package} built by {matches[0]}",
                0.85, timestamp,
            )


def scoped_paths_by_language(rows: list[sqlite3.Row]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(str(row["language"]), []).append(str(row["file_path"]))
    return grouped


def symbol_file_paths(
    conn: sqlite3.Connection,
    project_id: str,
    symbol_type: str,
    names: Iterable[str],
) -> set[str]:
    result: set[str] = set()
    ordered = sorted({name for name in names if name})
    for chunk in chunks(ordered):
        rows = conn.execute(
            f"SELECT DISTINCT file_path FROM code_symbols WHERE project_id = ? "
            f"AND symbol_type = ? AND symbol IN ({','.join('?' for _ in chunk)})",
            (project_id, symbol_type, *chunk),
        ).fetchall()
        result.update(str(row["file_path"]) for row in rows)
    return result


def ancestor_cmake_paths(
    conn: sqlite3.Connection,
    project_id: str,
    native_paths: set[str],
) -> set[str]:
    candidates = {
        (parent / "CMakeLists.txt").as_posix()
        for path in native_paths
        for parent in (Path(path).parent, *Path(path).parents)
    }
    return set(code_file_ids(conn, project_id, candidates))


def code_file_ids(
    conn: sqlite3.Connection, project_id: str, paths: Iterable[str],
) -> dict[str, int]:
    result: dict[str, int] = {}
    ordered = sorted({path for path in paths if path})
    for chunk in chunks(ordered):
        rows = conn.execute(
            f"SELECT id, file_path FROM code_files WHERE project_id = ? "
            f"AND file_path IN ({','.join('?' for _ in chunk)})",
            (project_id, *chunk),
        ).fetchall()
        result.update({str(row["file_path"]): int(row["id"]) for row in rows})
    return result


def existing_edge_keys(
    conn: sqlite3.Connection, project_id: str, file_ids: set[int],
) -> set[tuple[int, str, int]]:
    result: set[tuple[int, str, int]] = set()
    for chunk in chunks(sorted(file_ids)):
        rows = conn.execute(
            f"SELECT source_id, relation, target_id FROM memory_edges "
            f"WHERE project_id = ? AND valid_to IS NULL "
            f"AND source_type = 'code_file' AND target_type = 'code_file' "
            f"AND relation IN ('imports', 'configured_by') "
            f"AND source_id IN ({','.join('?' for _ in chunk)})",
            (project_id, *chunk),
        ).fetchall()
        result.update(
            (int(row["source_id"]), str(row["relation"]), int(row["target_id"]))
            for row in rows
        )
    return result


def cmake_native_targets(
    project: Project, cmake_paths: set[str],
) -> dict[str, list[tuple[str, str]]]:
    targets: dict[str, list[tuple[str, str]]] = {}
    pattern = re.compile(r"add_library\s*\(\s*([A-Za-z0-9_.+-]+)\s+(.*?)\)", re.I | re.S)
    for config_path in sorted(cmake_paths):
        for match in pattern.finditer(read_source(project, config_path)):
            module = normalize_module(match.group(1))
            for token in re.findall(r"[^\s()]+", match.group(2)):
                if Path(token).suffix.casefold() not in NATIVE_SUFFIXES:
                    continue
                source = (Path(config_path).parent / token).as_posix()
                if (project.root / source).is_file():
                    targets.setdefault(module, []).append((source, config_path))
    return targets


def build_package_targets(project: Project, paths: set[str]) -> dict[str, list[str]]:
    targets: dict[str, list[str]] = {}
    for path in sorted(paths):
        for item in build_target_ranges(read_source(project, path)):
            name = str(item["symbol"])
            if name.endswith((".hnp", ".hap", ".har")):
                targets.setdefault(name, []).append(path)
    return targets


def build_packages(project: Project, paths: set[str]) -> set[str]:
    return set(build_package_targets(project, paths))


def modules_for_arkts_paths(project: Project, paths: set[str]) -> set[str]:
    return {
        module for path in paths for module in native_imports(read_source(project, path))
    }


def packages_for_config_paths(project: Project, paths: set[str]) -> set[str]:
    return {package for path in paths for package in hnp_packages(read_source(project, path))}


def native_imports(text: str) -> list[str]:
    specs = re.findall(r"(?m)^\s*import\s+\w+\s+from\s+['\"]([^'\"]+\.so)['\"]", text)
    return list(dict.fromkeys(normalize_module(spec) for spec in specs))


def hnp_packages(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r'"package"\s*:\s*"([^"\n]+\.hnp)"', text)))


def normalize_module(value: str) -> str:
    name = Path(value).name.removesuffix(".so")
    return name[3:] if name.startswith("lib") else name


def is_cmake(path: str) -> bool:
    return Path(path).name.casefold() == "cmakelists.txt"


def read_source(project: Project, path: str) -> str:
    try:
        return (project.root / path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def chunks(items: list[T]) -> list[list[T]]:
    return [items[index:index + SQL_CHUNK_SIZE] for index in range(0, len(items), SQL_CHUNK_SIZE)]


def add_edge(
    rows: list[tuple[object, ...]],
    emitted: set[tuple[int, str, int]],
    project_id: str,
    source_id: int,
    relation: str,
    target_id: int,
    evidence: str,
    confidence: float,
    timestamp: str,
) -> None:
    key = (source_id, relation, target_id)
    if key in emitted:
        return
    emitted.add(key)
    rows.append((project_id, source_id, relation, target_id, evidence, confidence, timestamp))
