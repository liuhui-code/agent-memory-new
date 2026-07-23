# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .code_wiki_design_edges import normalized_stem
from .code_wiki_extractors import extract_arkts_reference_symbols
from .code_wiki_imports import relative_project_path, resolve_arkts_router_targets, resolve_js_imports
from .models import Project


FILE_COLUMNS = "id, file_path, language"
CODE_EXTENSIONS = (".ets", ".ts", ".js", ".py", ".dart", ".swift")
MODULE_MARKERS = ("oh-package.json5", "build-profile.json5", "package.json", "pyproject.toml")
TEST_SUFFIXES = ("", "test", "tests", "spec", "specs", ".test", ".spec", "-test", "-spec", "_test", "_spec")
SQL_CHUNK_SIZE = 300


def load_rebuild_files(
    conn: sqlite3.Connection,
    project: Project,
    scoped_files: list[sqlite3.Row],
    scoped_paths: set[str],
    symbols: list[sqlite3.Row],
) -> list[sqlite3.Row]:
    """Load only file rows that can participate in a scoped graph rebuild."""
    if not scoped_paths:
        return conn.execute(
            f"SELECT {FILE_COLUMNS} FROM code_files WHERE project_id = ?",
            (project.project_id,),
        ).fetchall()

    selected = {int(row["id"]): row for row in scoped_files}
    exact_paths = {str(row["file_path"]) for row in symbols}
    route_names: set[str] = set()
    test_stems = {normalized_stem(str(row["file_path"])) for row in scoped_files}
    for row in scoped_files:
        path = str(row["file_path"])
        exact_paths.update(marker_paths(path))
        if row["language"] != "ArkTS":
            continue
        source = project.root / path
        try:
            content = source.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for target in resolve_js_imports(project, source, content, [".ets", ".ts", ".js"]):
            exact_paths.add(relative_project_path(project, target))
        for target in resolve_arkts_router_targets(project, source, content):
            exact_paths.add(relative_project_path(project, target))
        route_names.update(
            name for name, kind in extract_arkts_reference_symbols(content) if kind == "route"
        )

    add_exact_rows(conn, project.project_id, exact_paths, selected)
    suffixes = route_suffixes(route_names) | test_suffixes(test_stems)
    add_suffix_rows(conn, project.project_id, suffixes, selected)
    add_exact_rows(
        conn,
        project.project_id,
        {marker for row in selected.values() for marker in marker_paths(str(row["file_path"]))},
        selected,
    )
    return [selected[key] for key in sorted(selected)]


def add_exact_rows(
    conn: sqlite3.Connection,
    project_id: str,
    paths: set[str],
    selected: dict[int, sqlite3.Row],
) -> None:
    ordered = sorted(path for path in paths if path)
    for chunk in chunks(ordered):
        rows = conn.execute(
            f"SELECT {FILE_COLUMNS} FROM code_files WHERE project_id = ? "
            f"AND file_path IN ({','.join('?' for _ in chunk)})",
            (project_id, *chunk),
        ).fetchall()
        selected.update({int(row["id"]): row for row in rows})


def add_suffix_rows(
    conn: sqlite3.Connection,
    project_id: str,
    suffixes: set[str],
    selected: dict[int, sqlite3.Row],
) -> None:
    expected = {suffix.lower() for suffix in suffixes}
    for chunk in chunks(sorted(fts_terms(expected)), 80):
        match = "file_path:(" + " OR ".join(f'"{term}"' for term in chunk) + ")"
        rows = conn.execute(
            f"SELECT cf.{FILE_COLUMNS.replace(', ', ', cf.')} "
            "FROM code_file_fts fts JOIN code_files cf ON cf.id = fts.rowid "
            "WHERE code_file_fts MATCH ? AND fts.project_id = ?",
            (match, project_id),
        ).fetchall()
        selected.update({
            int(row["id"]): row
            for row in rows
            if path_has_suffix(str(row["file_path"]), expected)
        })


def fts_terms(suffixes: set[str]) -> set[str]:
    return {
        " ".join(re.findall(r"[a-z0-9_$]+", Path(suffix).stem.lower()))
        for suffix in suffixes
        if Path(suffix).stem
    }


def path_has_suffix(file_path: str, suffixes: set[str]) -> bool:
    normalized = file_path.lower()
    return normalized in suffixes or any(normalized.endswith(f"/{suffix}") for suffix in suffixes)


def route_suffixes(names: set[str]) -> set[str]:
    return {
        f"{name.lower()}{extension}"
        for name in names
        for extension in (".ets", ".ts", ".js")
    }


def test_suffixes(stems: set[str]) -> set[str]:
    return {
        f"{stem.lower()}{suffix}{extension}"
        for stem in stems if stem
        for suffix in TEST_SUFFIXES
        for extension in CODE_EXTENSIONS
    }


def marker_paths(file_path: str) -> set[str]:
    parent = Path(file_path).parent
    directories = (parent, *parent.parents)
    return {
        (directory / marker).as_posix()
        for directory in directories
        for marker in MODULE_MARKERS
        if directory != Path(".")
    } | set(MODULE_MARKERS)


def chunks(items: list[str], size: int = SQL_CHUNK_SIZE) -> list[list[str]]:
    return [items[index:index + size] for index in range(0, len(items), size)]
