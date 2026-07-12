# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from .models import CODE_EXTENSIONS, IGNORE_DIRS, Project
from .query import collect_matches, record_query_miss_if_empty
from .records import output, row_dict
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .text import json_list, json_list_text, score_text, terms_from_text, unique_list

FOLLOWUP_FILE_LIMIT = 5
FOLLOWUP_SYMBOL_LIMIT = 5
FOLLOWUP_LOG_LIMIT = 5


def should_skip_dir(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def language_for(path: Path) -> str | None:
    return CODE_EXTENSIONS.get(path.suffix.lower())


def summarize_file(path: Path, language: str) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if language == "Markdown":
        heading = next((line.lstrip("#").strip() for line in lines if line.startswith("#")), "")
        return heading or f"Markdown file with {len(lines)} non-empty lines"
    if language == "ArkTS":
        symbols = extract_symbols(path, language)
        components = [name for name, kind in symbols if kind == "component"]
        routes = [name for name, kind in symbols if kind == "route"]
        resources = [name for name, kind in symbols if kind == "resource"]
        parts = [f"ArkTS file with {len(lines)} non-empty lines"]
        if components:
            parts.append("components: " + ", ".join(sorted(set(components))[:5]))
        if routes:
            parts.append("routes: " + ", ".join(sorted(set(routes))[:5]))
        if resources:
            parts.append("resources: " + ", ".join(sorted(set(resources))[:5]))
        return "; ".join(parts)
    if language == "HarmonyOS Config":
        symbols = extract_symbols(path, language)
        grouped: dict[str, list[str]] = {}
        for name, kind in symbols:
            grouped.setdefault(kind, []).append(name)
        parts = [f"HarmonyOS config with {len(lines)} non-empty lines"]
        for kind in ("ability", "permission", "dependency", "page_profile"):
            names = grouped.get(kind, [])
            if names:
                parts.append(f"{kind}s: " + ", ".join(sorted(set(names))[:5]))
        return "; ".join(parts)
    return f"{language} file with {len(lines)} non-empty lines"


def summarize_symbol(file_path: str, symbol: str, symbol_type: str | None, language: str) -> str:
    kind = symbol_type or "symbol"
    if language == "ArkTS":
        if kind == "component":
            return f"ArkTS component {symbol} declared in {file_path}"
        if kind == "route":
            return f"ArkTS route target {symbol} referenced by {file_path}"
        if kind == "resource":
            return f"ArkTS resource {symbol} referenced by {file_path}"
        if kind == "function":
            return f"ArkTS function or lifecycle method {symbol} in {file_path}"
        if kind == "class":
            return f"ArkTS class {symbol} declared in {file_path}"
    if language == "HarmonyOS Config":
        return f"HarmonyOS {kind} {symbol} configured in {file_path}"
    return f"{kind} {symbol} in {file_path}"


def extract_symbols(path: Path, language: str) -> list[tuple[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    symbols: list[tuple[str, str]] = []
    patterns: list[tuple[str, str]]
    if language == "Python":
        patterns = [(r"^\s*def\s+([A-Za-z_]\w*)\s*\(", "function"), (r"^\s*class\s+([A-Za-z_]\w*)", "class")]
    elif language in {"TypeScript", "JavaScript"}:
        patterns = [
            (r"^\s*function\s+([A-Za-z_$][\w$]*)\s*\(", "function"),
            (r"^\s*class\s+([A-Za-z_$][\w$]*)", "class"),
            (r"^\s*const\s+([A-Za-z_$][\w$]*)\s*=", "const"),
        ]
    elif language == "ArkTS":
        patterns = [
            (r"^\s*(?:export\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", "function"),
            (r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", "class"),
            (r"^\s*(?:export\s+)?struct\s+([A-Za-z_$][\w$]*)", "component"),
            (r"^\s*(?:private\s+|public\s+|protected\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::\s*[^ {]+)?\s*\{", "function"),
        ]
    elif language == "Dart":
        patterns = [
            (r"^\s*class\s+([A-Za-z_]\w*)", "class"),
            (r"^\s*(?:Future<[^>]+>|void|Widget)\s+([A-Za-z_]\w*)\s*\(", "function"),
        ]
    elif language == "Swift":
        patterns = [
            (r"^\s*class\s+([A-Za-z_]\w*)", "class"),
            (r"^\s*struct\s+([A-Za-z_]\w*)", "struct"),
            (r"^\s*func\s+([A-Za-z_]\w*)\s*\(", "function"),
        ]
    elif language == "Markdown":
        patterns = [(r"^(#{1,6})\s+(.+)$", "heading")]
    elif language == "HarmonyOS Config":
        return extract_harmonyos_config_symbols(text)
    else:
        patterns = []
    for line in text.splitlines():
        for pattern, kind in patterns:
            match = re.search(pattern, line)
            if match:
                if language == "Markdown":
                    name = match.group(2).strip()
                else:
                    name = match.group(1).strip()
                if name in {"if", "for", "while", "switch", "catch"}:
                    continue
                symbols.append((name, kind))
    if language == "ArkTS":
        symbols.extend(extract_arkts_reference_symbols(text))
    return symbols


def extract_arkts_reference_symbols(text: str) -> list[tuple[str, str]]:
    symbols: list[tuple[str, str]] = []
    for match in re.finditer(r"@(State|Prop|Link|Provide)\s+([A-Za-z_][A-Za-z0-9_]*)", text):
        symbols.append((match.group(2), "state"))
    for match in re.finditer(
        r"\brouter\.(?:pushUrl|replaceUrl)\s*\(\s*\{[^}]*\burl\s*:\s*['\"]([^'\"]+)['\"]",
        text,
        re.DOTALL,
    ):
        symbols.append((match.group(1), "route"))
    for match in re.finditer(r"\$r\s*\(\s*['\"]([^'\"]+)['\"]", text):
        symbols.append((match.group(1), "resource"))
    return symbols


def extract_harmonyos_config_symbols(text: str) -> list[tuple[str, str]]:
    symbols: list[tuple[str, str]] = []
    for match in re.finditer(r'"name"\s*:\s*"([^"]+)"', text):
        name = match.group(1)
        if "permission." in name:
            symbols.append((name, "permission"))
        elif name.endswith("Ability"):
            symbols.append((name, "ability"))
    for block_name in ("dependencies", "devDependencies", "overrides"):
        block_match = re.search(rf'"{block_name}"\s*:\s*\{{(.*?)\}}', text, re.DOTALL)
        if not block_match:
            continue
        for dep in re.finditer(r'"([^"]+)"\s*:', block_match.group(1)):
            symbols.append((dep.group(1), "dependency"))
    for match in re.finditer(r'"pages"\s*:\s*"([^"]+)"', text):
        symbols.append((match.group(1), "page_profile"))
    return symbols


def extract_log_statements(path: Path, language: str) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    logs: list[dict[str, Any]] = []
    current_function: str | None = None
    current_indent = -1
    for line_number, line in enumerate(text.splitlines(), start=1):
        symbol = function_symbol_on_line(line, language)
        if symbol:
            current_function, current_indent = symbol
        elif language == "Python" and current_function:
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())
            if stripped and indent <= current_indent and not stripped.startswith(("#", "@")):
                current_function = None
                current_indent = -1
        log = log_statement_on_line(line, language)
        if not log:
            continue
        log["line"] = line_number
        log["function"] = current_function
        log["raw_statement"] = line.strip()
        logs.append(log)
    return logs


def function_symbol_on_line(line: str, language: str) -> tuple[str, int] | None:
    indent = len(line) - len(line.lstrip())
    if language == "Python":
        match = re.match(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", line)
        return (match.group(1), indent) if match else None
    if language in {"TypeScript", "JavaScript"}:
        patterns = [
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
            r"^\s*(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(",
            r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)",
        ]
    elif language == "ArkTS":
        patterns = [
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
            r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)",
            r"^\s*(?:export\s+)?struct\s+([A-Za-z_$][\w$]*)",
            r"^\s*(?:private\s+|public\s+|protected\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::\s*[^ {]+)?\s*\{",
        ]
    elif language == "Dart":
        patterns = [
            r"^\s*(?:Future<[^>]+>|void|Widget|String|int|bool|double)\s+([A-Za-z_]\w*)\s*\(",
            r"^\s*class\s+([A-Za-z_]\w*)",
        ]
    elif language == "Swift":
        patterns = [
            r"^\s*func\s+([A-Za-z_]\w*)\s*\(",
            r"^\s*(?:class|struct)\s+([A-Za-z_]\w*)",
        ]
    else:
        patterns = []
    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            name = match.group(1)
            if name in {"if", "for", "while", "switch", "catch"}:
                continue
            return name, indent
    return None


def log_statement_on_line(line: str, language: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "//")):
        return None
    patterns: list[tuple[str, str, str]]
    if language == "Python":
        patterns = [
            (r"\bprint\s*\((.*)\)", "print", "print"),
            (r"\b(logging|logger)\.(debug|info|warning|warn|error|exception)\s*\((.*)\)", "", ""),
        ]
    elif language in {"TypeScript", "JavaScript"}:
        patterns = [
            (r"\bconsole\.(log|info|warn|error|debug)\s*\((.*)\)", "console", ""),
            (r"\blogger\.(log|info|warn|error|debug)\s*\((.*)\)", "logger", ""),
        ]
    elif language == "ArkTS":
        patterns = [
            (r"\bconsole\.(log|info|warn|error|debug)\s*\((.*)\)", "console", ""),
            (r"\blogger\.(log|info|warn|error|debug)\s*\((.*)\)", "logger", ""),
            (r"\bhilog\.(debug|info|warn|error|fatal)\s*\((.*)\)", "hilog", ""),
        ]
    elif language == "Dart":
        patterns = [
            (r"\bprint\s*\((.*)\)", "print", "print"),
            (r"\bdebugPrint\s*\((.*)\)", "debugPrint", "debug"),
            (r"\blog\s*\((.*)\)", "log", "log"),
        ]
    elif language == "Swift":
        patterns = [
            (r"\bprint\s*\((.*)\)", "print", "print"),
            (r"\bNSLog\s*\((.*)\)", "NSLog", "log"),
            (r"\bos_log\s*\((.*)\)", "os_log", "log"),
            (r"\blogger\.(debug|info|warning|error)\s*\((.*)\)", "logger", ""),
        ]
    else:
        return None
    for pattern, logger_name, fixed_level in patterns:
        match = re.search(pattern, stripped)
        if not match:
            continue
        if language == "Python" and logger_name == "":
            logger = match.group(1)
            level = match.group(2)
            args_text = match.group(3)
        elif language in {"TypeScript", "JavaScript", "ArkTS"}:
            logger = logger_name
            level = match.group(1)
            args_text = match.group(2)
        elif language == "Swift" and logger_name == "logger":
            logger = logger_name
            level = match.group(1)
            args_text = match.group(2)
        else:
            logger = logger_name
            level = fixed_level
            args_text = match.group(1)
        return {
            "level": "warning" if level == "warn" else level,
            "logger": logger,
            "message_template": message_template_for_args(logger, args_text),
        }
    return None


def message_template_for_args(logger: str, args_text: str) -> str:
    literals = string_literals(args_text)
    if logger == "hilog" and len(literals) >= 2:
        return literals[1]
    if literals:
        return literals[0]
    return args_text.strip()


def string_literals(text: str) -> list[str]:
    return [match.group(2) for match in re.finditer(r"""(['"])(.*?)(?<!\\)\1""", text)]


def wiki_index(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, args.source)
    files = collect_project_files(source_project)
    stats = write_wiki_index(source_project, files, replace=True)
    record_learn_scope(
        project,
        source_project.root,
        "project",
        "replace",
        files,
        target_path=".",
    )
    print(f"wiki index updated ({parse_stats_summary(stats)})")


def collect_project_files(project: Project) -> list[Path]:
    files_to_index: list[Path] = []
    for root, dirs, files in os.walk(project.root):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        if should_skip_dir(root_path.relative_to(project.root) if root_path != project.root else Path("")):
            continue
        for filename in files:
            path = root_path / filename
            rel = path.relative_to(project.root)
            if should_skip_dir(rel):
                continue
            if language_for(path):
                files_to_index.append(path)
    return files_to_index


def collect_path_files(project: Project, target: Path) -> list[Path]:
    if not target.exists():
        raise SystemExit(f"path does not exist: {target}")
    if target.is_file():
        return [target] if language_for(target) else []
    files_to_index: list[Path] = []
    for root, dirs, files in os.walk(target):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        rel_root = root_path.relative_to(project.root)
        if should_skip_dir(rel_root):
            continue
        for filename in files:
            path = root_path / filename
            rel = path.relative_to(project.root)
            if should_skip_dir(rel):
                continue
            if language_for(path):
                files_to_index.append(path)
    return files_to_index


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_file_snapshot(project: Project, files: list[Path]) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted({item.resolve() for item in files}):
        try:
            rel = str(path.relative_to(project.root))
        except ValueError:
            continue
        if not path.exists() or not path.is_file():
            continue
        snapshot[rel] = file_sha256(path)
    return snapshot


def learn_scope_key(
    scope_type: str,
    source_root: Path,
    target_path: str | None = None,
    entry_path: str | None = None,
    depth: int | None = None,
) -> str:
    raw = json.dumps(
        {
            "scope_type": scope_type,
            "source_root": str(source_root),
            "target_path": target_path or "",
            "entry_path": entry_path or "",
            "depth": depth,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def record_learn_scope(
    project: Project,
    source_root: Path,
    scope_type: str,
    mode: str,
    files: list[Path],
    *,
    target_path: str | None = None,
    entry_path: str | None = None,
    depth: int | None = None,
) -> int:
    ts = now_iso()
    snapshot = build_file_snapshot(project, files)
    scope_key = learn_scope_key(
        scope_type,
        source_root,
        target_path=target_path,
        entry_path=entry_path,
        depth=depth,
    )
    with connect(project) as conn:
        conn.execute(
            """
            INSERT INTO learn_scopes(
              project_id, scope_key, scope_type, source_root, target_path, entry_path,
              depth, mode, file_snapshot, file_count, status, created_at, updated_at, last_refreshed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
            ON CONFLICT(project_id, scope_key) DO UPDATE SET
              scope_type=excluded.scope_type,
              source_root=excluded.source_root,
              target_path=excluded.target_path,
              entry_path=excluded.entry_path,
              depth=excluded.depth,
              mode=excluded.mode,
              file_snapshot=excluded.file_snapshot,
              file_count=excluded.file_count,
              status='active',
              updated_at=excluded.updated_at,
              last_refreshed_at=excluded.last_refreshed_at
            """,
            (
                project.project_id,
                scope_key,
                scope_type,
                str(source_root),
                target_path,
                entry_path,
                depth,
                mode,
                json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                len(snapshot),
                ts,
                ts,
                ts,
            ),
        )
        row = conn.execute(
            """
            SELECT id
            FROM learn_scopes
            WHERE project_id = ? AND scope_key = ?
            """,
            (project.project_id, scope_key),
        ).fetchone()
        conn.commit()
    return int(row["id"])


def write_wiki_scope(
    project: Project,
    files: list[Path],
    *,
    replace: bool = False,
    retired_relative_files: list[str] | None = None,
) -> dict[str, Any]:
    stats = write_wiki_index(project, files, replace=replace)
    retired = sorted(
        {
            str(item).strip()
            for item in (retired_relative_files or [])
            if str(item).strip()
        }
    )
    if retired:
        with connect(project) as conn:
            retired_ids = scope_node_ids(conn, project.project_id, retired)
            delete_edges_for_scope(conn, project.project_id, retired_ids)
            for file_path in retired:
                conn.execute(
                    "DELETE FROM code_files WHERE project_id = ? AND file_path = ?",
                    (project.project_id, file_path),
                )
                conn.execute(
                    "DELETE FROM code_symbols WHERE project_id = ? AND file_path = ?",
                    (project.project_id, file_path),
                )
                conn.execute(
                    "DELETE FROM code_log_statements WHERE project_id = ? AND file_path = ?",
                    (project.project_id, file_path),
                )
            stats["memory_edges_total"] = conn.execute(
                "SELECT COUNT(*) AS count FROM memory_edges WHERE project_id = ?",
                (project.project_id,),
            ).fetchone()["count"]
            conn.commit()
        stats["retired_files"] = retired
    else:
        stats["retired_files"] = []
    return stats


def load_learn_scopes(project: Project, scope_id: int | None = None) -> list[sqlite3.Row]:
    with connect(project) as conn:
        if scope_id is not None:
            row = conn.execute(
                """
                SELECT *
                FROM learn_scopes
                WHERE project_id = ? AND id = ?
                ORDER BY id
                """,
                (project.project_id, scope_id),
            ).fetchone()
            return [row] if row else []
        return conn.execute(
            """
            SELECT *
            FROM learn_scopes
            WHERE project_id = ? AND status = 'active'
            ORDER BY updated_at DESC, id DESC
            """,
            (project.project_id,),
        ).fetchall()


def write_wiki_index(project: Project, files: list[Path], replace: bool = False) -> dict[str, Any]:
    ts = now_iso()
    unique_files = sorted({path.resolve() for path in files})
    relative_files: list[tuple[Path, Path, str, str]] = []
    for path in unique_files:
        try:
            rel = path.relative_to(project.root)
        except ValueError:
            continue
        if should_skip_dir(rel):
            continue
        language = language_for(path)
        if not language:
            continue
        relative_files.append((path, rel, str(rel), language))

    language_counts: Counter[str] = Counter()
    symbol_type_counts: Counter[str] = Counter()
    log_level_counts: Counter[str] = Counter()
    symbols_by_file: dict[str, list[tuple[str, str]]] = {}
    logs_by_file: dict[str, list[dict[str, Any]]] = {}
    for path, _rel, rel_text, language in relative_files:
        language_counts[language] += 1
        symbols = extract_symbols(path, language)
        logs = extract_log_statements(path, language)
        symbols_by_file[rel_text] = symbols
        logs_by_file[rel_text] = logs
        for _symbol, symbol_type in symbols:
            symbol_type_counts[symbol_type or "symbol"] += 1
        for log in logs:
            log_level_counts[str(log.get("level") or "log")] += 1

    affected_file_paths = [rel_text for _, _, rel_text, _ in relative_files]
    with connect(project) as conn:
        previous_scope_ids = scope_node_ids(conn, project.project_id, affected_file_paths)
        if replace:
            conn.execute("DELETE FROM code_files WHERE project_id = ?", (project.project_id,))
            conn.execute("DELETE FROM code_symbols WHERE project_id = ?", (project.project_id,))
            conn.execute("DELETE FROM code_log_statements WHERE project_id = ?", (project.project_id,))
            conn.execute("DELETE FROM memory_edges WHERE project_id = ?", (project.project_id,))
        else:
            delete_edges_for_scope(conn, project.project_id, previous_scope_ids)
            for _, _, rel_text, _ in relative_files:
                conn.execute(
                    "DELETE FROM code_files WHERE project_id = ? AND file_path = ?",
                    (project.project_id, rel_text),
                )
                conn.execute(
                    "DELETE FROM code_symbols WHERE project_id = ? AND file_path = ?",
                    (project.project_id, rel_text),
                )
                conn.execute(
                    "DELETE FROM code_log_statements WHERE project_id = ? AND file_path = ?",
                    (project.project_id, rel_text),
                )
        for path, _rel, rel_text, language in relative_files:
            summary = summarize_file(path, language)
            conn.execute(
                """
                INSERT INTO code_files(project_id, file_path, summary, language, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project.project_id, rel_text, summary, language, ts),
            )
            for symbol, symbol_type in symbols_by_file.get(rel_text, []):
                summary = summarize_symbol(rel_text, symbol, symbol_type, language)
                conn.execute(
                    """
                    INSERT INTO code_symbols(project_id, file_path, symbol, symbol_type, summary, calls, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (project.project_id, rel_text, symbol, symbol_type, summary, "", ts),
                )
            for log in logs_by_file.get(rel_text, []):
                conn.execute(
                    """
                    INSERT INTO code_log_statements(
                      project_id, file_path, line, function, level, logger,
                      message_template, raw_statement, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project.project_id,
                        rel_text,
                        log.get("line"),
                        log.get("function"),
                        log.get("level"),
                        log.get("logger"),
                        log.get("message_template") or "",
                        log.get("raw_statement"),
                        ts,
                    ),
                )
        rebuild_code_memory_edges(conn, project, scope_file_paths=None if replace else affected_file_paths)
        memory_edges_total = conn.execute(
            "SELECT COUNT(*) AS count FROM memory_edges WHERE project_id = ?",
            (project.project_id,),
        ).fetchone()["count"]
        conn.commit()
    return {
        "files_indexed": len(relative_files),
        "languages": dict(sorted(language_counts.items())),
        "symbols_total": sum(symbol_type_counts.values()),
        "symbols_by_type": dict(sorted(symbol_type_counts.items())),
        "code_logs_total": sum(log_level_counts.values()),
        "code_logs_by_level": dict(sorted(log_level_counts.items())),
        "memory_edges_total": memory_edges_total,
    }


def scope_node_ids(
    conn: sqlite3.Connection,
    project_id: str,
    file_paths: list[str],
) -> dict[str, set[int]]:
    if not file_paths:
        return {"code_file": set(), "code_symbol": set(), "code_log_statement": set()}
    placeholders = ",".join("?" for _ in file_paths)
    file_rows = conn.execute(
        f"""
        SELECT id
        FROM code_files
        WHERE project_id = ? AND file_path IN ({placeholders})
        """,
        (project_id, *file_paths),
    ).fetchall()
    symbol_rows = conn.execute(
        f"""
        SELECT id
        FROM code_symbols
        WHERE project_id = ? AND file_path IN ({placeholders})
        """,
        (project_id, *file_paths),
    ).fetchall()
    log_rows = conn.execute(
        f"""
        SELECT id
        FROM code_log_statements
        WHERE project_id = ? AND file_path IN ({placeholders})
        """,
        (project_id, *file_paths),
    ).fetchall()
    return {
        "code_file": {int(row["id"]) for row in file_rows},
        "code_symbol": {int(row["id"]) for row in symbol_rows},
        "code_log_statement": {int(row["id"]) for row in log_rows},
    }


def delete_edges_for_scope(
    conn: sqlite3.Connection,
    project_id: str,
    scoped_ids: dict[str, set[int]],
) -> None:
    for entity_type, ids in scoped_ids.items():
        if not ids:
            continue
        placeholders = ",".join("?" for _ in ids)
        conn.execute(
            f"""
            DELETE FROM memory_edges
            WHERE project_id = ?
              AND (
                (source_type = ? AND source_id IN ({placeholders}))
                OR
                (target_type = ? AND target_id IN ({placeholders}))
              )
            """,
            (project_id, entity_type, *ids, entity_type, *ids),
        )


def rebuild_code_memory_edges(
    conn: sqlite3.Connection,
    project: Project,
    scope_file_paths: list[str] | None = None,
) -> None:
    ts = now_iso()
    project_id = project.project_id
    files = conn.execute(
        "SELECT id, file_path, language FROM code_files WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    symbols = conn.execute(
        "SELECT id, file_path, symbol, symbol_type FROM code_symbols WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    logs = conn.execute(
        "SELECT id, file_path, function, line FROM code_log_statements WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    file_ids = {row["file_path"]: row["id"] for row in files}
    symbol_ids = {
        (row["file_path"], row["symbol"]): row["id"]
        for row in symbols
    }
    scoped_paths = set(scope_file_paths or [])
    scoped_symbols = [row for row in symbols if not scoped_paths or row["file_path"] in scoped_paths]
    scoped_logs = [row for row in logs if not scoped_paths or row["file_path"] in scoped_paths]
    scoped_files = [row for row in files if not scoped_paths or row["file_path"] in scoped_paths]
    for row in scoped_symbols:
        file_id = file_ids.get(row["file_path"])
        if file_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_file",
                file_id,
                "contains",
                "code_symbol",
                row["id"],
                row["file_path"],
                0.9,
                ts,
            )
    for row in scoped_logs:
        file_id = file_ids.get(row["file_path"])
        evidence = f"{row['file_path']}:{row['line']}" if row["line"] else row["file_path"]
        if file_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_file",
                file_id,
                "contains",
                "code_log_statement",
                row["id"],
                evidence,
                0.9,
                ts,
            )
        function_name = row["function"]
        symbol_id = symbol_ids.get((row["file_path"], function_name)) if function_name else None
        if symbol_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_symbol",
                symbol_id,
                "emits_log",
                "code_log_statement",
                row["id"],
                evidence,
                0.8,
                ts,
            )

    insert_arkts_knowledge_edges(conn, project, scoped_files, symbols, ts)


def insert_arkts_knowledge_edges(
    conn: sqlite3.Connection,
    project: Project,
    files: list[sqlite3.Row],
    symbols: list[sqlite3.Row],
    ts: str,
) -> None:
    file_ids = {row["file_path"]: row["id"] for row in files}
    symbol_ids = {
        (row["file_path"], row["symbol"], row["symbol_type"]): row["id"]
        for row in symbols
    }
    for row in files:
        if row["language"] != "ArkTS":
            continue
        source_rel = row["file_path"]
        source_id = row["id"]
        source_abs = project.root / source_rel
        try:
            text = source_abs.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for target in resolve_js_imports(project, source_abs, text, [".ets", ".ts", ".js"]):
            target_rel = relative_project_path(project, target)
            target_id = file_ids.get(target_rel)
            if target_id:
                insert_memory_edge(
                    conn,
                    project.project_id,
                    "code_file",
                    source_id,
                    "imports",
                    "code_file",
                    target_id,
                    f"{source_rel} -> {target_rel}",
                    0.85,
                    ts,
                )

        for target in resolve_arkts_router_targets(project, source_abs, text):
            target_rel = relative_project_path(project, target)
            target_id = file_ids.get(target_rel)
            if target_id:
                insert_memory_edge(
                    conn,
                    project.project_id,
                    "code_file",
                    source_id,
                    "routes_to",
                    "code_file",
                    target_id,
                    f"{source_rel} -> {target_rel}",
                    0.85,
                    ts,
                )

        for resource, kind in extract_arkts_reference_symbols(text):
            if kind != "resource":
                continue
            symbol_id = symbol_ids.get((source_rel, resource, "resource"))
            if symbol_id:
                insert_memory_edge(
                    conn,
                    project.project_id,
                    "code_file",
                    source_id,
                    "uses_resource",
                    "code_symbol",
                    symbol_id,
                    f"{source_rel} uses {resource}",
                    0.8,
                    ts,
                )

        for state_name, kind in extract_arkts_reference_symbols(text):
            if kind != "state":
                continue
            symbol_id = symbol_ids.get((source_rel, state_name, "state"))
            if symbol_id:
                insert_memory_edge(
                    conn,
                    project.project_id,
                    "code_file",
                    source_id,
                    "defines_state",
                    "code_symbol",
                    symbol_id,
                    f"{source_rel} defines state {state_name}",
                    0.8,
                    ts,
                )


def relative_project_path(project: Project, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.root))
    except ValueError:
        return str(path)
        function_name = row["function"]
        symbol_id = symbol_ids.get((row["file_path"], function_name)) if function_name else None
        if symbol_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_symbol",
                symbol_id,
                "emits_log",
                "code_log_statement",
                row["id"],
                evidence,
                0.8,
                ts,
            )


def insert_memory_edge(
    conn: sqlite3.Connection,
    project_id: str,
    source_type: str,
    source_id: int,
    relation: str,
    target_type: str,
    target_id: int,
    evidence: str,
    confidence: float,
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO memory_edges(
          project_id, source_type, source_id, relation, target_type,
          target_id, evidence, confidence, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            source_type,
            source_id,
            relation,
            target_type,
            target_id,
            evidence,
            confidence,
            created_at,
        ),
    )


def resolve_learning_source(project: Project, raw_source: str | None) -> Path:
    source = Path(raw_source).expanduser() if raw_source else project.root
    if not source.is_absolute():
        source = project.root / source
    source = source.resolve()
    if not source.exists() or not source.is_dir():
        raise SystemExit(f"source must be a directory: {source}")
    return source


def project_for_learning_source(project: Project, raw_source: str | None) -> Project:
    source = resolve_learning_source(project, raw_source)
    return replace(project, root=source, project_name=source.name)


def resolve_target(project: Project, raw_path: str) -> Path:
    target = Path(raw_path).expanduser()
    if not target.is_absolute():
        target = project.root / target
    target = target.resolve()
    try:
        target.relative_to(project.root)
    except ValueError:
        raise SystemExit(f"path must be inside project: {target}")
    return target


def learn_path(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, args.source)
    target = resolve_target(source_project, args.path)
    files = collect_path_files(source_project, target)
    stats = write_wiki_index(source_project, files, replace=args.replace)
    rel_target = str(target.relative_to(source_project.root))
    scope_id = record_learn_scope(
        project,
        source_project.root,
        "path",
        "replace" if args.replace else "merge",
        files,
        target_path=rel_target,
    )
    task = f"Learn path {target.relative_to(source_project.root)} from {source_project.root}"
    mode = "replaced" if args.replace else "merged"
    summary = f"{mode.capitalize()} {len(files)} files from {target.relative_to(source_project.root)}"
    add_episode_from_values(project, task, summary, "learned")
    payload = {
        "source": str(source_project.root),
        "path": rel_target,
        "scope_id": scope_id,
        "mode": "replace" if args.replace else "merge",
        "files": [str(path.relative_to(source_project.root)) for path in sorted(files)],
        "count": len(files),
        "summary": summary,
        "parse_stats": stats,
    }
    semantic_followup = semantic_followup_from_db(source_project, payload["files"])
    if semantic_followup:
        payload["semantic_followup"] = semantic_followup
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_learn_path.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.json:
        output(payload, True)
    else:
        print(f"{summary} ({parse_stats_summary(stats)})")


def parse_stats_summary(stats: dict[str, Any]) -> str:
    return (
        f"parsed files={stats.get('files_indexed', 0)}, "
        f"symbols={stats.get('symbols_total', 0)}, "
        f"logs={stats.get('code_logs_total', 0)}, "
        f"edges={stats.get('memory_edges_total', 0)}"
    )


def has_business_summary(value: Any) -> bool:
    return bool(str(value or "").strip())


def has_business_terms(value: Any) -> bool:
    return bool(json_list(value))


def semantic_quality_report(payload_files: list[dict[str, Any]]) -> dict[str, Any]:
    stats = {
        "files_total": 0,
        "files_with_business_summary": 0,
        "files_with_business_terms": 0,
        "symbols_total": 0,
        "symbols_with_business_summary": 0,
        "symbols_with_business_terms": 0,
        "logs_total": 0,
        "logs_with_business_summary": 0,
        "logs_with_business_terms": 0,
    }
    gaps = {
        "files_missing_business_summary": [],
        "files_missing_business_terms": [],
        "symbols_missing_business_summary": [],
        "symbols_missing_business_terms": [],
        "logs_missing_business_summary": [],
        "logs_missing_business_terms": [],
    }
    for file_item in payload_files:
        if not isinstance(file_item, dict) or not file_item.get("file_path"):
            continue
        file_path = str(file_item["file_path"])
        stats["files_total"] += 1
        if has_business_summary(file_item.get("business_summary")):
            stats["files_with_business_summary"] += 1
        else:
            gaps["files_missing_business_summary"].append(file_path)
        if has_business_terms(file_item.get("business_terms")):
            stats["files_with_business_terms"] += 1
        else:
            gaps["files_missing_business_terms"].append(file_path)

        for symbol_item in file_item.get("symbols") or []:
            if not isinstance(symbol_item, dict) or not symbol_item.get("symbol"):
                continue
            symbol_name = str(symbol_item["symbol"])
            symbol_key = f"{file_path}::{symbol_name}"
            stats["symbols_total"] += 1
            if has_business_summary(symbol_item.get("business_summary")):
                stats["symbols_with_business_summary"] += 1
            else:
                gaps["symbols_missing_business_summary"].append(symbol_key)
            if has_business_terms(symbol_item.get("business_terms")):
                stats["symbols_with_business_terms"] += 1
            else:
                gaps["symbols_missing_business_terms"].append(symbol_key)

        for log_item in file_item.get("logs") or []:
            if not isinstance(log_item, dict) or not log_item.get("message_template"):
                continue
            message_template = str(log_item["message_template"])
            log_key = f"{file_path}::{message_template}"
            stats["logs_total"] += 1
            if has_business_summary(log_item.get("business_summary")):
                stats["logs_with_business_summary"] += 1
            else:
                gaps["logs_missing_business_summary"].append(log_key)
            if has_business_terms(log_item.get("business_terms")):
                stats["logs_with_business_terms"] += 1
            else:
                gaps["logs_missing_business_terms"].append(log_key)
    return {"semantic_stats": stats, "semantic_gaps": gaps}


def semantic_followup_workflow_steps() -> list[str]:
    return [
        "Read the listed files, symbols, and logs in current source.",
        "Fill missing business_summary and business_terms in followup_payload_template.",
        "Write the completed payload with learn-business.",
        "Re-run learn-business, query, or maintain-plan to confirm the semantic gap is reduced.",
    ]


def followup_hint_terms(*values: Any) -> list[str]:
    raw = " ".join(str(value or "") for value in values if str(value or "").strip())
    return unique_list(terms_from_text(raw))


def followup_hint_context(*values: Any) -> list[str]:
    context: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text:
            context.append(text)
    return context


def followup_item_score(path: str, kind: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    lower_path = path.lower()
    if kind == "file":
        if lower_path.endswith(".ets"):
            score += 8
            reasons.append("arkts_page_or_module")
        elif lower_path.endswith(".json5"):
            score += 4
            reasons.append("harmonyos_config")
    elif kind == "log":
        score += 24
        reasons.append("missing_log_semantics")
    elif kind == "symbol":
        score += 12
        reasons.append("missing_symbol_semantics")
    return score, reasons


def prioritize_followup_file(
    file_output: dict[str, Any],
    file_missing_summary: bool,
    file_missing_terms: bool,
) -> dict[str, Any]:
    score, reasons = followup_item_score(file_output["file_path"], "file")
    if file_missing_summary:
        score += 6
        reasons.append("missing_file_business_summary")
    if file_missing_terms:
        score += 6
        reasons.append("missing_file_business_terms")

    prioritized_symbols: list[dict[str, Any]] = []
    for symbol in file_output["symbols"]:
        item_score, item_reasons = followup_item_score(file_output["file_path"], "symbol")
        if not has_business_summary(symbol.get("business_summary")):
            item_score += 4
            item_reasons.append("missing_symbol_business_summary")
        if not has_business_terms(symbol.get("business_terms")):
            item_score += 4
            item_reasons.append("missing_symbol_business_terms")
        enriched = dict(symbol)
        enriched["priority_score"] = item_score
        enriched["priority_reasons"] = item_reasons
        enriched["hint_terms"] = followup_hint_terms(
            file_output["file_path"],
            symbol.get("symbol"),
            symbol.get("symbol_type"),
            symbol.get("summary"),
        )
        enriched["hint_context"] = followup_hint_context(
            file_output["file_path"],
            symbol.get("symbol"),
            symbol.get("symbol_type"),
            symbol.get("summary"),
        )
        prioritized_symbols.append(enriched)

    prioritized_logs: list[dict[str, Any]] = []
    for log in file_output["logs"]:
        item_score, item_reasons = followup_item_score(file_output["file_path"], "log")
        if not has_business_summary(log.get("business_summary")):
            item_score += 4
            item_reasons.append("missing_log_business_summary")
        if not has_business_terms(log.get("business_terms")):
            item_score += 4
            item_reasons.append("missing_log_business_terms")
        enriched = dict(log)
        enriched["priority_score"] = item_score
        enriched["priority_reasons"] = item_reasons
        enriched["hint_terms"] = followup_hint_terms(
            file_output["file_path"],
            log.get("message_template"),
            log.get("function"),
            log.get("level"),
            log.get("logger"),
            log.get("raw_statement"),
            log.get("business_event"),
            log.get("trigger_stage"),
            " ".join(json_list(log.get("symptom_terms"))),
            " ".join(json_list(log.get("likely_causes"))),
            log.get("process_hint"),
            " ".join(json_list(log.get("neighbor_terms"))),
        )
        enriched["hint_context"] = followup_hint_context(
            file_output["file_path"],
            log.get("message_template"),
            log.get("function"),
            log.get("level"),
            log.get("logger"),
            log.get("raw_statement"),
            log.get("business_event"),
            log.get("trigger_stage"),
            " ".join(json_list(log.get("symptom_terms"))),
            " ".join(json_list(log.get("likely_causes"))),
            log.get("process_hint"),
            " ".join(json_list(log.get("neighbor_terms"))),
        )
        prioritized_logs.append(enriched)

    prioritized_symbols.sort(
        key=lambda item: (item["priority_score"], item.get("symbol_type") == "function", item["symbol"]),
        reverse=True,
    )
    prioritized_logs.sort(
        key=lambda item: (item["priority_score"], item.get("level") == "error", item["message_template"]),
        reverse=True,
    )

    score += sum(item["priority_score"] for item in prioritized_symbols[:FOLLOWUP_SYMBOL_LIMIT])
    score += sum(item["priority_score"] for item in prioritized_logs[:FOLLOWUP_LOG_LIMIT])
    for item in prioritized_symbols[:FOLLOWUP_SYMBOL_LIMIT]:
        for reason in item["priority_reasons"]:
            if reason not in reasons:
                reasons.append(reason)
    for item in prioritized_logs[:FOLLOWUP_LOG_LIMIT]:
        for reason in item["priority_reasons"]:
            if reason not in reasons:
                reasons.append(reason)
    enriched_file = dict(file_output)
    enriched_file["priority_score"] = score
    enriched_file["priority_reasons"] = reasons
    enriched_file["hint_terms"] = followup_hint_terms(
        file_output["file_path"],
        file_output.get("summary"),
        " ".join(symbol.get("symbol", "") for symbol in prioritized_symbols[:FOLLOWUP_SYMBOL_LIMIT]),
        " ".join(log.get("message_template", "") for log in prioritized_logs[:FOLLOWUP_LOG_LIMIT]),
    )
    enriched_file["hint_context"] = followup_hint_context(
        file_output["file_path"],
        file_output.get("summary"),
        " ".join(symbol.get("symbol", "") for symbol in prioritized_symbols[:FOLLOWUP_SYMBOL_LIMIT]),
        " ".join(log.get("message_template", "") for log in prioritized_logs[:FOLLOWUP_LOG_LIMIT]),
    )
    enriched_file["symbols"] = prioritized_symbols[:FOLLOWUP_SYMBOL_LIMIT]
    enriched_file["logs"] = prioritized_logs[:FOLLOWUP_LOG_LIMIT]
    enriched_file["truncated_counts"] = {
        "symbols": max(0, len(prioritized_symbols) - len(enriched_file["symbols"])),
        "logs": max(0, len(prioritized_logs) - len(enriched_file["logs"])),
    }
    return enriched_file


def finalize_semantic_followup(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not files:
        return None
    files.sort(key=lambda item: (item["priority_score"], item["file_path"]), reverse=True)
    truncated = len(files) > FOLLOWUP_FILE_LIMIT
    visible_files = files[:FOLLOWUP_FILE_LIMIT]
    remaining_files = max(0, len(files) - len(visible_files))
    return {
        "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
        "workflow_steps": semantic_followup_workflow_steps(),
        "recommended_next_action": "run_learn_business_now",
        "truncated": truncated,
        "returned_counts": {
            "files": len(visible_files),
            "symbols": sum(len(file_item["symbols"]) for file_item in visible_files),
            "logs": sum(len(file_item["logs"]) for file_item in visible_files),
        },
        "remaining_counts": {
            "files": remaining_files,
            "symbols": sum(file_item["truncated_counts"]["symbols"] for file_item in visible_files),
            "logs": sum(file_item["truncated_counts"]["logs"] for file_item in visible_files),
        },
        "followup_payload_template": {"files": visible_files},
    }


def semantic_followup_template(payload_files: list[dict[str, Any]]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for file_item in payload_files:
        if not isinstance(file_item, dict) or not file_item.get("file_path"):
            continue
        file_path = str(file_item["file_path"])
        file_output = {
            "file_path": file_path,
            "summary": file_item.get("summary") or "",
            "business_summary": "" if not has_business_summary(file_item.get("business_summary")) else "",
            "business_terms": [],
            "symbols": [],
            "logs": [],
        }
        for symbol_item in file_item.get("symbols") or []:
            if not isinstance(symbol_item, dict) or not symbol_item.get("symbol"):
                continue
            if has_business_summary(symbol_item.get("business_summary")) and has_business_terms(symbol_item.get("business_terms")):
                continue
            file_output["symbols"].append(
                {
                    "symbol": str(symbol_item["symbol"]),
                    "symbol_type": symbol_item.get("symbol_type"),
                    "summary": symbol_item.get("summary") or "",
                    "business_summary": "",
                    "business_terms": [],
                }
            )
        for log_item in file_item.get("logs") or []:
            if not isinstance(log_item, dict) or not log_item.get("message_template"):
                continue
            if has_business_summary(log_item.get("business_summary")) and has_business_terms(log_item.get("business_terms")):
                continue
            file_output["logs"].append(
                {
                    "message_template": str(log_item["message_template"]),
                    "function": log_item.get("function"),
                    "level": log_item.get("level"),
                    "logger": log_item.get("logger"),
                    "raw_statement": log_item.get("raw_statement"),
                    "business_event": log_item.get("business_event"),
                    "trigger_stage": log_item.get("trigger_stage"),
                    "symptom_terms": log_item.get("symptom_terms") or [],
                    "likely_causes": log_item.get("likely_causes") or [],
                    "process_hint": log_item.get("process_hint"),
                    "neighbor_terms": log_item.get("neighbor_terms") or [],
                    "business_summary": "",
                    "business_terms": [],
                }
            )
        if (
            not has_business_summary(file_item.get("business_summary"))
            or not has_business_terms(file_item.get("business_terms"))
            or file_output["symbols"]
            or file_output["logs"]
        ):
            files.append(
                prioritize_followup_file(
                    file_output,
                    not has_business_summary(file_item.get("business_summary")),
                    not has_business_terms(file_item.get("business_terms")),
                )
            )
    return {"files": files}


def semantic_followup_from_db(project: Project, file_paths: list[str]) -> dict[str, Any] | None:
    seen_paths: set[str] = set()
    unique_paths: list[str] = []
    for raw_path in file_paths:
        path = str(raw_path or "").strip()
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        unique_paths.append(path)
    if not unique_paths:
        return None
    files: list[dict[str, Any]] = []
    with connect(project) as conn:
        for file_path in unique_paths:
            file_row = conn.execute(
                """
                SELECT file_path, summary, business_summary, business_terms
                FROM code_files
                WHERE project_id = ? AND file_path = ?
                """,
                (project.project_id, file_path),
            ).fetchone()
            if not file_row:
                continue
            file_output = {
                "file_path": file_path,
                "summary": file_row["summary"] or "",
                "business_summary": "",
                "business_terms": [],
                "symbols": [],
                "logs": [],
            }
            file_missing = (
                not has_business_summary(file_row["business_summary"])
                or not has_business_terms(file_row["business_terms"])
            )
            symbol_rows = conn.execute(
                """
                SELECT symbol, symbol_type, summary, business_summary, business_terms
                FROM code_symbols
                WHERE project_id = ? AND file_path = ?
                ORDER BY symbol
                """,
                (project.project_id, file_path),
            ).fetchall()
            for row in symbol_rows:
                if has_business_summary(row["business_summary"]) and has_business_terms(row["business_terms"]):
                    continue
                file_output["symbols"].append(
                    {
                        "symbol": row["symbol"],
                        "symbol_type": row["symbol_type"],
                        "summary": row["summary"] or "",
                        "business_summary": "",
                        "business_terms": [],
                    }
                )
            log_rows = conn.execute(
                """
                SELECT message_template, function, level, logger, raw_statement, business_summary, business_terms,
                       business_event, trigger_stage, symptom_terms, likely_causes, process_hint, neighbor_terms
                FROM code_log_statements
                WHERE project_id = ? AND file_path = ?
                ORDER BY message_template
                """,
                (project.project_id, file_path),
            ).fetchall()
            for row in log_rows:
                if has_business_summary(row["business_summary"]) and has_business_terms(row["business_terms"]):
                    continue
                file_output["logs"].append(
                {
                    "message_template": row["message_template"],
                    "function": row["function"],
                    "level": row["level"],
                    "logger": row["logger"],
                    "raw_statement": row["raw_statement"],
                    "business_event": row["business_event"],
                    "trigger_stage": row["trigger_stage"],
                    "symptom_terms": json_list(row["symptom_terms"]),
                    "likely_causes": json_list(row["likely_causes"]),
                    "process_hint": row["process_hint"],
                    "neighbor_terms": json_list(row["neighbor_terms"]),
                    "business_summary": "",
                    "business_terms": [],
                }
                )
            if file_missing or file_output["symbols"] or file_output["logs"]:
                files.append(prioritize_followup_file(file_output, not has_business_summary(file_row["business_summary"]), not has_business_terms(file_row["business_terms"])))
    return finalize_semantic_followup(files)


def merge_business_terms(existing: Any, incoming: Any) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for value in [*json_list(existing), *json_list(incoming)]:
        stripped = str(value).strip()
        normalized = stripped.lower()
        if not stripped or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(stripped)
    return json.dumps(merged, ensure_ascii=False)


def merged_optional_text(existing: Any, incoming: Any) -> str | None:
    incoming_text = str(incoming or "").strip()
    if incoming_text:
        return incoming_text
    existing_text = str(existing or "").strip()
    return existing_text or None


def merged_business_summary(
    existing: Any,
    incoming: Any,
    target: str,
    entity_type: str,
    conflicts: list[dict[str, Any]],
) -> str | None:
    existing_text = str(existing or "").strip()
    incoming_text = str(incoming or "").strip()
    if not existing_text:
        return incoming_text or None
    if not incoming_text:
        return existing_text
    if existing_text == incoming_text:
        return existing_text
    conflicts.append(
        {
            "entity_type": entity_type,
            "target": target,
            "field": "business_summary",
            "existing": existing_text,
            "incoming": incoming_text,
            "resolution": "manual_review_required",
            "source_command": "learn-business",
        }
    )
    return existing_text


def learn_business(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, args.source)
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid --payload JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        raise SystemExit("--payload must be an object with a files array")
    ts = now_iso()
    files_written = 0
    symbols_written = 0
    logs_written = 0
    conflicts: list[dict[str, Any]] = []
    with connect(source_project) as conn:
        for file_item in payload["files"]:
            if not isinstance(file_item, dict) or not file_item.get("file_path"):
                raise SystemExit("each file item must include file_path")
            file_path = str(file_item["file_path"])
            language = file_item.get("language") or CODE_EXTENSIONS.get(Path(file_path).suffix.lower()) or "unknown"
            summary = file_item.get("summary") or f"{language} file"
            existing_file = conn.execute(
                """
                SELECT file_path, summary, language, business_summary, business_terms
                FROM code_files
                WHERE project_id = ? AND file_path = ?
                """,
                (source_project.project_id, file_path),
            ).fetchone()
            file_business_summary = merged_business_summary(
                existing_file["business_summary"] if existing_file else None,
                file_item.get("business_summary"),
                file_path,
                "code_file",
                conflicts,
            )
            file_business_terms = merge_business_terms(
                existing_file["business_terms"] if existing_file else None,
                file_item.get("business_terms"),
            )
            conn.execute(
                """
                INSERT INTO code_files(
                  project_id, file_path, summary, language,
                  business_summary, business_terms, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, file_path) DO UPDATE SET
                  summary=excluded.summary,
                  language=excluded.language,
                  business_summary=excluded.business_summary,
                  business_terms=excluded.business_terms,
                  updated_at=excluded.updated_at
                """,
                (
                    source_project.project_id,
                    file_path,
                    summary,
                    language,
                    file_business_summary,
                    file_business_terms,
                    ts,
                ),
            )
            files_written += 1
            for symbol_item in file_item.get("symbols") or []:
                if not isinstance(symbol_item, dict) or not symbol_item.get("symbol"):
                    continue
                symbol = str(symbol_item["symbol"])
                symbol_type = symbol_item.get("symbol_type") or "symbol"
                symbol_summary = symbol_item.get("summary") or summarize_symbol(file_path, symbol, symbol_type, language)
                existing_symbol = conn.execute(
                    """
                    SELECT *
                    FROM code_symbols
                    WHERE project_id = ? AND file_path = ? AND symbol = ? AND COALESCE(symbol_type, 'symbol') = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (source_project.project_id, file_path, symbol, symbol_type),
                ).fetchone()
                symbol_business_summary = merged_business_summary(
                    existing_symbol["business_summary"] if existing_symbol else None,
                    symbol_item.get("business_summary"),
                    f"{file_path}::{symbol}",
                    "code_symbol",
                    conflicts,
                )
                symbol_business_terms = merge_business_terms(
                    existing_symbol["business_terms"] if existing_symbol else None,
                    symbol_item.get("business_terms"),
                )
                if existing_symbol:
                    conn.execute(
                        """
                        UPDATE code_symbols
                        SET symbol_type = ?, summary = ?, calls = ?,
                            business_summary = ?, business_terms = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            symbol_type,
                            symbol_summary,
                            symbol_item.get("calls") or existing_symbol["calls"] or "",
                            symbol_business_summary,
                            symbol_business_terms,
                            ts,
                            existing_symbol["id"],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO code_symbols(
                          project_id, file_path, symbol, symbol_type, summary, calls,
                          business_summary, business_terms, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_project.project_id,
                            file_path,
                            symbol,
                            symbol_type,
                            symbol_summary,
                            symbol_item.get("calls") or "",
                            symbol_business_summary,
                            symbol_business_terms,
                            ts,
                        ),
                    )
                symbols_written += 1
            for log_item in file_item.get("logs") or []:
                if not isinstance(log_item, dict) or not log_item.get("message_template"):
                    continue
                message_template = str(log_item.get("message_template"))
                existing_log = conn.execute(
                    """
                    SELECT *
                    FROM code_log_statements
                    WHERE project_id = ? AND file_path = ?
                      AND message_template = ?
                      AND COALESCE(function, '') = COALESCE(?, '')
                      AND COALESCE(level, '') = COALESCE(?, '')
                      AND COALESCE(logger, '') = COALESCE(?, '')
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (
                        source_project.project_id,
                        file_path,
                        message_template,
                        log_item.get("function"),
                        log_item.get("level"),
                        log_item.get("logger"),
                    ),
                ).fetchone()
                log_target = f"{file_path}::{message_template}"
                log_business_summary = merged_business_summary(
                    existing_log["business_summary"] if existing_log else None,
                    log_item.get("business_summary"),
                    log_target,
                    "code_log_statement",
                    conflicts,
                )
                log_business_terms = merge_business_terms(
                    existing_log["business_terms"] if existing_log else None,
                    log_item.get("business_terms"),
                )
                log_business_event = merged_optional_text(
                    existing_log["business_event"] if existing_log else None,
                    log_item.get("business_event"),
                )
                log_trigger_stage = merged_optional_text(
                    existing_log["trigger_stage"] if existing_log else None,
                    log_item.get("trigger_stage"),
                )
                log_symptom_terms = merge_business_terms(
                    existing_log["symptom_terms"] if existing_log else None,
                    log_item.get("symptom_terms"),
                )
                log_likely_causes = merge_business_terms(
                    existing_log["likely_causes"] if existing_log else None,
                    log_item.get("likely_causes"),
                )
                log_process_hint = merged_optional_text(
                    existing_log["process_hint"] if existing_log else None,
                    log_item.get("process_hint"),
                )
                log_neighbor_terms = merge_business_terms(
                    existing_log["neighbor_terms"] if existing_log else None,
                    log_item.get("neighbor_terms"),
                )
                if existing_log:
                    conn.execute(
                        """
                        UPDATE code_log_statements
                        SET line = ?, function = ?, level = ?, logger = ?,
                            message_template = ?, raw_statement = ?,
                            business_summary = ?, business_terms = ?, business_event = ?,
                            trigger_stage = ?, symptom_terms = ?, likely_causes = ?,
                            process_hint = ?, neighbor_terms = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            log_item.get("line") if log_item.get("line") is not None else existing_log["line"],
                            log_item.get("function") if log_item.get("function") is not None else existing_log["function"],
                            log_item.get("level") if log_item.get("level") is not None else existing_log["level"],
                            log_item.get("logger") if log_item.get("logger") is not None else existing_log["logger"],
                            message_template,
                            log_item.get("raw_statement") if log_item.get("raw_statement") is not None else existing_log["raw_statement"],
                            log_business_summary,
                            log_business_terms,
                            log_business_event,
                            log_trigger_stage,
                            log_symptom_terms,
                            log_likely_causes,
                            log_process_hint,
                            log_neighbor_terms,
                            ts,
                            existing_log["id"],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO code_log_statements(
                          project_id, file_path, line, function, level, logger,
                          message_template, raw_statement,
                          business_summary, business_terms, business_event, trigger_stage,
                          symptom_terms, likely_causes, process_hint, neighbor_terms, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_project.project_id,
                            file_path,
                            log_item.get("line"),
                            log_item.get("function"),
                            log_item.get("level"),
                            log_item.get("logger"),
                            message_template,
                            log_item.get("raw_statement"),
                            log_business_summary,
                            log_business_terms,
                            log_business_event,
                            log_trigger_stage,
                            log_symptom_terms,
                            log_likely_causes,
                            log_process_hint,
                            log_neighbor_terms,
                            ts,
                        ),
                    )
                logs_written += 1
        rebuild_code_memory_edges(conn, source_project)
        edge_count = conn.execute(
            "SELECT COUNT(*) AS count FROM memory_edges WHERE project_id = ?",
            (source_project.project_id,),
        ).fetchone()["count"]
        for conflict in conflicts:
            conn.execute(
                """
                INSERT INTO semantic_conflicts(
                  project_id, entity_type, target, field, existing, incoming, resolution,
                  source_command, observed_at, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                """,
                (
                    source_project.project_id,
                    conflict.get("entity_type") or "code_file",
                    conflict.get("target"),
                    conflict.get("field"),
                    conflict.get("existing"),
                    conflict.get("incoming"),
                    conflict.get("resolution"),
                    conflict.get("source_command") or "learn-business",
                    ts,
                ),
            )
        conn.commit()
    data = {
        "project_id": project.project_id,
        "source": str(source_project.root),
        "source_command": "learn-business",
        "observed_at": ts,
        "files_written": files_written,
        "symbols_written": symbols_written,
        "logs_written": logs_written,
        "memory_edges_total": edge_count,
    }
    if conflicts:
        for conflict in conflicts:
            conflict.setdefault("observed_at", ts)
        data["semantic_conflicts"] = conflicts
    semantic_quality = semantic_quality_report(payload["files"])
    data.update(semantic_quality)
    if any(semantic_quality["semantic_gaps"].values()):
        template = semantic_followup_template(payload["files"])
        followup = finalize_semantic_followup(template["files"])
        if followup:
            data["semantic_followup"] = followup
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_learn_business.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output(data, args.json)


def add_episode_from_values(project: Project, task: str, summary: str, outcome: str | None) -> None:
    with connect(project) as conn:
        conn.execute(
            """
            INSERT INTO episodes(project_id, task, summary, outcome, files_touched, commands_run, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (project.project_id, task, summary, outcome, None, None, now_iso()),
        )
        conn.commit()


def compare_scope_snapshots(
    previous: dict[str, str],
    current: dict[str, str],
) -> tuple[list[str], list[str], list[str], int]:
    previous_paths = set(previous)
    current_paths = set(current)
    added = sorted(current_paths - previous_paths)
    removed = sorted(previous_paths - current_paths)
    changed = sorted(
        path for path in (previous_paths & current_paths) if previous.get(path) != current.get(path)
    )
    unchanged_count = sum(
        1 for path in (previous_paths & current_paths) if previous.get(path) == current.get(path)
    )
    return added, removed, changed, unchanged_count


def files_for_scope(source_project: Project, scope_row: sqlite3.Row) -> list[Path]:
    scope_type = scope_row["scope_type"]
    if scope_type == "project":
        return collect_project_files(source_project)
    if scope_type == "path":
        target_path = str(scope_row["target_path"] or ".")
        target = resolve_target(source_project, target_path)
        return collect_path_files(source_project, target)
    if scope_type == "entry":
        entry_path = str(scope_row["entry_path"] or "").strip()
        if not entry_path:
            raise SystemExit(f"learn scope {scope_row['id']} is missing entry_path")
        entry = resolve_target(source_project, entry_path)
        if not entry.is_file():
            raise SystemExit(f"learn scope entry no longer exists as file: {entry}")
        depth = int(scope_row["depth"] or 2)
        return collect_entry_related_files(source_project, entry, depth)
    raise SystemExit(f"unsupported learn scope type: {scope_type}")


def semantic_review_targets_from_drift(
    added_files: list[str],
    changed_files: list[str],
    removed_files: list[str],
) -> dict[str, Any]:
    affected: list[str] = []
    seen: set[str] = set()
    for value in [*changed_files, *added_files, *removed_files]:
        stripped = str(value).strip()
        normalized = stripped.lower()
        if not stripped or normalized in seen:
            continue
        seen.add(normalized)
        affected.append(stripped)
    return {
        "drift_detected": bool(affected),
        "refresh_semantic_scope": bool(changed_files or added_files),
        "retire_removed_scope": bool(removed_files),
        "file_paths": affected,
    }


def update_scope_refresh_record(
    project: Project,
    scope_row: sqlite3.Row,
    current_snapshot: dict[str, str],
    refresh_summary: dict[str, Any],
) -> None:
    ts = now_iso()
    with connect(project) as conn:
        conn.execute(
            """
            UPDATE learn_scopes
            SET file_snapshot = ?, file_count = ?, updated_at = ?, last_refreshed_at = ?, last_refresh_summary = ?
            WHERE project_id = ? AND id = ?
            """,
            (
                json.dumps(current_snapshot, ensure_ascii=False, sort_keys=True),
                len(current_snapshot),
                ts,
                ts,
                json.dumps(refresh_summary, ensure_ascii=False, sort_keys=True),
                project.project_id,
                scope_row["id"],
            ),
        )
        conn.commit()


def maintain_refresh_scope(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    scope_rows = load_learn_scopes(project, args.scope_id)
    if args.scope_id is not None and not scope_rows:
        raise SystemExit(f"learn scope not found: {args.scope_id}")

    refreshed: list[dict[str, Any]] = []
    for scope_row in scope_rows:
        source_root = Path(scope_row["source_root"]).expanduser().resolve()
        result: dict[str, Any] = {
            "scope_id": scope_row["id"],
            "scope_type": scope_row["scope_type"],
            "source_root": str(source_root),
            "target_path": scope_row["target_path"],
            "entry_path": scope_row["entry_path"],
            "depth": scope_row["depth"],
            "mode": scope_row["mode"],
        }
        if not source_root.exists() or not source_root.is_dir():
            result["status"] = "missing_source"
            result["warning"] = f"source root no longer exists: {source_root}"
            refreshed.append(result)
            continue

        source_project = replace(project, root=source_root, project_name=source_root.name)
        files = files_for_scope(source_project, scope_row)
        current_snapshot = build_file_snapshot(source_project, files)
        previous_snapshot = json.loads(scope_row["file_snapshot"] or "{}")
        added_files, removed_files, changed_files, unchanged_count = compare_scope_snapshots(
            previous_snapshot,
            current_snapshot,
        )
        stats = write_wiki_scope(
            source_project,
            files,
            replace=False,
            retired_relative_files=removed_files,
        )
        semantic_review_targets = semantic_review_targets_from_drift(
            added_files,
            changed_files,
            removed_files,
        )
        refresh_summary = {
            "status": "refreshed",
            "added_files": added_files,
            "changed_files": changed_files,
            "removed_files": removed_files,
            "unchanged_count": unchanged_count,
            "semantic_review_targets": semantic_review_targets,
        }
        update_scope_refresh_record(project, scope_row, current_snapshot, refresh_summary)
        summary = (
            f"Refreshed learn scope {scope_row['id']} ({scope_row['scope_type']}) "
            f"added={len(added_files)} changed={len(changed_files)} removed={len(removed_files)}"
        )
        add_episode_from_values(project, f"Refresh learn scope {scope_row['id']}", summary, "refreshed")
        result.update(
            {
                "status": "refreshed",
                "previous_file_count": len(previous_snapshot),
                "current_file_count": len(current_snapshot),
                "added_files": added_files,
                "changed_files": changed_files,
                "removed_files": removed_files,
                "unchanged_count": unchanged_count,
                "parse_stats": stats,
                "semantic_review_targets": semantic_review_targets,
            }
        )
        refreshed.append(result)

    payload = {
        "scope_count": len(scope_rows),
        "refreshed_count": sum(1 for item in refreshed if item["status"] == "refreshed"),
        "missing_source_count": sum(1 for item in refreshed if item["status"] == "missing_source"),
        "scopes": refreshed,
    }
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_refresh_scope.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output(payload, args.json)


def learn_entry(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source_project = project_for_learning_source(project, args.source)
    entry = resolve_target(source_project, args.entry)
    if not entry.is_file():
        raise SystemExit(f"entry must be a file: {entry}")
    files = collect_entry_related_files(source_project, entry, args.depth)
    stats = write_wiki_index(source_project, files, replace=args.replace)
    rel_files = [str(path.relative_to(source_project.root)) for path in sorted(files)]
    rel_entry = str(entry.relative_to(source_project.root))
    scope_id = record_learn_scope(
        project,
        source_project.root,
        "entry",
        "replace" if args.replace else "merge",
        files,
        entry_path=rel_entry,
        depth=args.depth,
    )
    payload = {
        "source": str(source_project.root),
        "entry": rel_entry,
        "scope_id": scope_id,
        "depth": args.depth,
        "mode": "replace" if args.replace else "merge",
        "files": rel_files,
        "count": len(rel_files),
        "parse_stats": stats,
    }
    semantic_followup = semantic_followup_from_db(source_project, rel_files)
    if semantic_followup:
        payload["semantic_followup"] = semantic_followup
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_learn_entry.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    add_episode_from_values(
        project,
        f"Learn entry {entry.relative_to(source_project.root)} from {source_project.root}",
        f"{'Replaced' if args.replace else 'Merged'} {len(rel_files)} files related to {entry.relative_to(source_project.root)} with depth {args.depth}",
        "learned",
    )
    output(payload, args.json)


def collect_entry_related_files(project: Project, entry: Path, depth: int) -> list[Path]:
    seen: set[Path] = set()
    frontier: list[tuple[Path, int]] = [(entry.resolve(), 0)]
    while frontier:
        current, current_depth = frontier.pop(0)
        if current in seen:
            continue
        if not current.exists() or not current.is_file() or not language_for(current):
            continue
        seen.add(current)
        if current_depth >= depth:
            continue
        for imported in resolve_project_imports(project, current):
            if imported not in seen:
                frontier.append((imported, current_depth + 1))
    return sorted(seen)


def resolve_project_imports(project: Project, path: Path) -> list[Path]:
    language = language_for(path)
    if not language:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    candidates: list[Path] = []
    if language == "Python":
        candidates.extend(resolve_python_imports(project, path, text))
    elif language in {"TypeScript", "JavaScript"}:
        candidates.extend(resolve_js_imports(project, path, text))
    elif language == "ArkTS":
        candidates.extend(resolve_js_imports(project, path, text, [".ets", ".ts", ".js"]))
        candidates.extend(resolve_arkts_router_targets(project, path, text))
    elif language == "Dart":
        candidates.extend(resolve_quoted_relative_imports(project, path, text, [".dart"]))
    elif language == "Markdown":
        candidates.extend(resolve_markdown_links(project, path, text))
    return [candidate for candidate in candidates if candidate.exists() and language_for(candidate)]


def resolve_python_imports(project: Project, path: Path, text: str) -> list[Path]:
    candidates: list[Path] = []
    for line in text.splitlines():
        line = line.strip()
        rel_match = re.match(r"from\s+(\.+[\w\.]*)\s+import\s+([\w,\s*]+)", line)
        if rel_match:
            module = rel_match.group(1)
            names = [name.strip() for name in rel_match.group(2).split(",") if name.strip() and name.strip() != "*"]
            candidates.extend(resolve_python_module(project, path, module))
            for name in names:
                candidates.extend(resolve_python_module(project, path, f"{module}.{name}"))
            continue
        abs_match = re.match(r"(?:from|import)\s+([A-Za-z_][\w\.]*)", line)
        if abs_match:
            candidates.extend(resolve_python_module(project, path, abs_match.group(1)))
    return candidates


def resolve_python_module(project: Project, path: Path, module: str) -> list[Path]:
    base: Path
    parts: list[str]
    if module.startswith("."):
        dot_count = len(module) - len(module.lstrip("."))
        base = path.parent
        for _ in range(max(dot_count - 1, 0)):
            base = base.parent
        parts = [part for part in module.lstrip(".").split(".") if part]
    else:
        base = project.root
        parts = [part for part in module.split(".") if part]
    module_path = base.joinpath(*parts) if parts else base
    return existing_module_paths(module_path, [".py"])


def existing_module_paths(base: Path, extensions: list[str]) -> list[Path]:
    matches: list[Path] = []
    for ext in extensions:
        file_path = base.with_suffix(ext)
        if file_path.exists():
            matches.append(file_path.resolve())
    for ext in extensions:
        init_path = base / f"__init__{ext}"
        if init_path.exists():
            matches.append(init_path.resolve())
    return matches


def resolve_js_imports(
    project: Project,
    path: Path,
    text: str,
    extensions: list[str] | None = None,
) -> list[Path]:
    imports = re.findall(r"(?:from\s+|import\s*\(|require\s*\()\s*['\"]([^'\"]+)['\"]", text)
    candidates: list[Path] = []
    extensions = extensions or [".ts", ".tsx", ".js", ".jsx"]
    for spec in imports:
        if spec.startswith("."):
            candidates.extend(resolve_relative_spec(path.parent / spec, extensions))
    return candidates


def resolve_arkts_router_targets(project: Project, path: Path, text: str) -> list[Path]:
    candidates: list[Path] = []
    for route, kind in extract_arkts_reference_symbols(text):
        if kind != "route":
            continue
        if route.startswith("$") or route.startswith("@"):
            continue
        if route.startswith("/"):
            route = route.lstrip("/")
        bases = [project.root, arkts_ets_root(path), path.parent]
        for base in bases:
            candidates.extend(resolve_relative_spec(base / route, [".ets"]))
    return candidates


def arkts_ets_root(path: Path) -> Path:
    for parent in [path.parent, *path.parents]:
        if parent.name == "ets":
            return parent
    return path.parent


def resolve_quoted_relative_imports(project: Project, path: Path, text: str, extensions: list[str]) -> list[Path]:
    imports = re.findall(r"import\s+['\"]([^'\"]+)['\"]", text)
    candidates: list[Path] = []
    for spec in imports:
        if spec.startswith("."):
            candidates.extend(resolve_relative_spec(path.parent / spec, extensions))
    return candidates


def resolve_relative_spec(base: Path, extensions: list[str]) -> list[Path]:
    matches: list[Path] = []
    if base.suffix and base.exists():
        matches.append(base.resolve())
    matches.extend(existing_module_paths(base, extensions))
    for ext in extensions:
        index_path = base / f"index{ext}"
        if index_path.exists():
            matches.append(index_path.resolve())
    return matches


def resolve_markdown_links(project: Project, path: Path, text: str) -> list[Path]:
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    candidates: list[Path] = []
    for link in links:
        if "://" in link or link.startswith("#"):
            continue
        target = (path.parent / link.split("#", 1)[0]).resolve()
        try:
            target.relative_to(project.root)
        except ValueError:
            continue
        if target.exists() and target.is_file():
            candidates.append(target)
    return candidates


def wiki_search(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    matches = collect_matches(project, args.query)
    data = matches["wiki_matches"] + matches["code_log_matches"]
    data.sort(key=lambda item: (item.get("score", 0), item.get("updated_at", "")), reverse=True)
    record_query_miss_if_empty(
        project,
        "wiki-search",
        args.query,
        {
            "semantic_facts": [],
            "reflections": [],
            "episodes": [],
            "wiki_matches": matches["wiki_matches"],
            "code_log_matches": matches["code_log_matches"],
            "edge_matches": matches["edge_matches"],
        },
    )
    output(data[:20], args.json)
