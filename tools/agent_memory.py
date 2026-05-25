#!/usr/bin/env python3
"""Local Agent Memory runtime.

This is the stable script API used by Agent Memory skills.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_TABLES = {
    "projects",
    "episodes",
    "semantic_facts",
    "reflections",
    "code_files",
    "code_symbols",
}

VAULT_DIRS = [
    "Episodes",
    "Reflections",
    "Semantic Facts",
    "Codebase Wiki",
    "Daily",
]

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "build",
    "dist",
    ".dart_tool",
    "__pycache__",
    ".agent-memory",
    ".agent-skills",
}

CODE_EXTENSIONS = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".dart": "Dart",
    ".swift": "Swift",
    ".md": "Markdown",
}


@dataclass(frozen=True)
class Project:
    root: Path
    memory_dir: Path
    db_path: Path
    vault_dir: Path
    runtime_dir: Path
    project_id: str
    project_name: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_project(path: str) -> Project:
    root = Path(path).expanduser().resolve()
    project_id = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    memory_dir = root / ".agent-memory"
    return Project(
        root=root,
        memory_dir=memory_dir,
        db_path=memory_dir / "memory.db",
        vault_dir=memory_dir / "vault",
        runtime_dir=memory_dir / "runtime",
        project_id=project_id,
        project_name=root.name,
    )


def ensure_dirs(project: Project) -> None:
    project.memory_dir.mkdir(parents=True, exist_ok=True)
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    project.vault_dir.mkdir(parents=True, exist_ok=True)
    for name in VAULT_DIRS:
        (project.vault_dir / name).mkdir(parents=True, exist_ok=True)


def connect(project: Project) -> sqlite3.Connection:
    conn = sqlite3.connect(project.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT UNIQUE NOT NULL,
          project_path TEXT NOT NULL,
          project_name TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS episodes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          task TEXT NOT NULL,
          summary TEXT NOT NULL,
          outcome TEXT,
          files_touched TEXT,
          commands_run TEXT,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS semantic_facts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          fact TEXT NOT NULL,
          source TEXT NOT NULL,
          confidence REAL DEFAULT 0.8,
          is_stale INTEGER DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reflections (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          task TEXT NOT NULL,
          summary TEXT,
          mistake TEXT,
          lesson TEXT NOT NULL,
          future_rule TEXT,
          is_stale INTEGER DEFAULT 0,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS code_files (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          file_path TEXT NOT NULL,
          summary TEXT,
          language TEXT,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS code_symbols (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          file_path TEXT NOT NULL,
          symbol TEXT NOT NULL,
          symbol_type TEXT,
          summary TEXT,
          calls TEXT,
          updated_at TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_code_files_project_file
        ON code_files(project_id, file_path);

        CREATE INDEX IF NOT EXISTS idx_semantic_project_stale
        ON semantic_facts(project_id, is_stale);

        CREATE INDEX IF NOT EXISTS idx_reflections_project_stale
        ON reflections(project_id, is_stale);
        """
    )
    conn.commit()


def upsert_project(conn: sqlite3.Connection, project: Project) -> None:
    ts = now_iso()
    conn.execute(
        """
        INSERT INTO projects(project_id, project_path, project_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(project_id) DO UPDATE SET
          project_path=excluded.project_path,
          project_name=excluded.project_name,
          updated_at=excluded.updated_at
        """,
        (project.project_id, str(project.root), project.project_name, ts, ts),
    )
    conn.commit()


def write_config(project: Project) -> None:
    config = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "project_name": project.project_name,
        "runtime": "tools/agent_memory.py",
        "vault": ".agent-memory/vault",
        "version": 1,
        "updated_at": now_iso(),
    }
    (project.memory_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def init_project(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_dirs(project)
    with connect(project) as conn:
        create_schema(conn)
        upsert_project(conn, project)
    write_config(project)
    vault_index(args)
    print(f"initialized agent memory for {project.root}")


def doctor(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    checks: list[tuple[str, bool]] = [
        (".agent-memory exists", project.memory_dir.exists()),
        ("config.json exists", (project.memory_dir / "config.json").exists()),
        ("memory.db exists", project.db_path.exists()),
        ("vault directory exists", project.vault_dir.exists()),
        ("runtime directory exists", project.runtime_dir.exists()),
    ]
    table_ok = False
    if project.db_path.exists():
        with connect(project) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            existing = {row["name"] for row in rows}
            table_ok = REQUIRED_TABLES.issubset(existing)
    checks.append(("required tables exist", table_ok))

    failed = False
    for label, ok in checks:
        print(f"{'OK' if ok else 'FAIL'} {label}")
        failed = failed or not ok
    if failed:
        raise SystemExit(1)


def ensure_initialized(project: Project) -> None:
    ensure_dirs(project)
    with connect(project) as conn:
        create_schema(conn)
        upsert_project(conn, project)
    if not (project.memory_dir / "config.json").exists():
        write_config(project)


def add_semantic(args: argparse.Namespace, project: Project) -> None:
    if not args.fact:
        raise SystemExit("--fact is required for --type semantic")
    ts = now_iso()
    with connect(project) as conn:
        cur = conn.execute(
            """
            INSERT INTO semantic_facts(project_id, fact, source, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                args.fact,
                args.source or "manual",
                args.confidence,
                ts,
                ts,
            ),
        )
        conn.commit()
    print(f"semantic fact #{cur.lastrowid} written")


def add_episode(args: argparse.Namespace, project: Project) -> None:
    if not args.task or not args.summary:
        raise SystemExit("--task and --summary are required for --type episode")
    with connect(project) as conn:
        cur = conn.execute(
            """
            INSERT INTO episodes(project_id, task, summary, outcome, files_touched, commands_run, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                args.task,
                args.summary,
                args.outcome,
                args.files_touched,
                args.commands_run,
                now_iso(),
            ),
        )
        conn.commit()
    print(f"episode #{cur.lastrowid} written")


def update(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_initialized(project)
    if args.type == "semantic":
        add_semantic(args, project)
    elif args.type == "episode":
        add_episode(args, project)
    else:
        raise SystemExit(f"unsupported update type: {args.type}")


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        if re.search(r"[\u4e00-\u9fff]", token) and len(token) > 1:
            expanded.extend(token[i : i + 2] for i in range(len(token) - 1))
    return [token for token in expanded if token]


def score_text(query_tokens: list[str], text: str) -> int:
    lowered = text.lower()
    return sum(1 for token in query_tokens if token in lowered)


def row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def collect_matches(project: Project, query: str) -> dict[str, list[dict[str, Any]]]:
    tokens = tokenize(query)
    results: dict[str, list[dict[str, Any]]] = {
        "semantic_facts": [],
        "reflections": [],
        "episodes": [],
        "wiki_matches": [],
    }
    with connect(project) as conn:
        semantic = conn.execute(
            """
            SELECT id, fact, source, confidence, created_at
            FROM semantic_facts
            WHERE project_id = ? AND is_stale = 0
            """,
            (project.project_id,),
        ).fetchall()
        reflections = conn.execute(
            """
            SELECT id, task, summary, mistake, lesson, future_rule, created_at
            FROM reflections
            WHERE project_id = ? AND is_stale = 0
            """,
            (project.project_id,),
        ).fetchall()
        episodes = conn.execute(
            """
            SELECT id, task, summary, outcome, created_at
            FROM episodes
            WHERE project_id = ?
            """,
            (project.project_id,),
        ).fetchall()
        files = conn.execute(
            """
            SELECT id, file_path, summary, language, updated_at
            FROM code_files
            WHERE project_id = ?
            """,
            (project.project_id,),
        ).fetchall()
        symbols = conn.execute(
            """
            SELECT id, file_path, symbol, symbol_type, summary, updated_at
            FROM code_symbols
            WHERE project_id = ?
            """,
            (project.project_id,),
        ).fetchall()

    for row in semantic:
        score = score_text(tokens, row["fact"])
        if score:
            item = row_dict(row)
            item["score"] = score + float(row["confidence"] or 0)
            results["semantic_facts"].append(item)

    for row in reflections:
        text = " ".join(
            str(row[key] or "")
            for key in ("task", "summary", "mistake", "lesson", "future_rule")
        )
        score = score_text(tokens, text)
        if score:
            item = row_dict(row)
            item["score"] = score
            results["reflections"].append(item)

    for row in episodes:
        text = f"{row['task']} {row['summary']} {row['outcome'] or ''}"
        score = score_text(tokens, text)
        if score:
            item = row_dict(row)
            item["score"] = score
            results["episodes"].append(item)

    for row in files:
        text = f"{row['file_path']} {row['summary'] or ''} {row['language'] or ''}"
        score = score_text(tokens, text)
        if score:
            item = row_dict(row)
            item["kind"] = "file"
            item["score"] = score
            results["wiki_matches"].append(item)

    for row in symbols:
        text = f"{row['file_path']} {row['symbol']} {row['symbol_type'] or ''} {row['summary'] or ''}"
        score = score_text(tokens, text)
        if score:
            item = row_dict(row)
            item["kind"] = "symbol"
            item["score"] = score
            results["wiki_matches"].append(item)

    for key in results:
        results[key].sort(key=lambda item: (item.get("score", 0), item.get("created_at", "")), reverse=True)
    return results


def limited_context(project: Project, query: str) -> dict[str, Any]:
    matches = collect_matches(project, query)
    context = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "query": query,
        "semantic_facts": matches["semantic_facts"][:3],
        "reflections": matches["reflections"][:3],
        "episodes": matches["episodes"][:2],
        "wiki_matches": matches["wiki_matches"][:5],
    }
    return context


def output(data: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        if isinstance(data, dict):
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(data)


def search(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_initialized(project)
    data = collect_matches(project, args.query)
    output(data, args.json)


def context(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_initialized(project)
    data = limited_context(project, args.query)
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_context.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output(data, args.json)


def reflect(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_initialized(project)
    if not args.task or not args.lesson:
        raise SystemExit("--task and --lesson are required")
    data = {
        "project_id": project.project_id,
        "task": args.task,
        "summary": args.summary,
        "mistake": args.mistake,
        "lesson": args.lesson,
        "future_rule": args.future_rule,
        "created_at": now_iso(),
    }
    with connect(project) as conn:
        cur = conn.execute(
            """
            INSERT INTO reflections(project_id, task, summary, mistake, lesson, future_rule, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                args.task,
                args.summary,
                args.mistake,
                args.lesson,
                args.future_rule,
                data["created_at"],
            ),
        )
        conn.commit()
        data["id"] = cur.lastrowid
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_reflection.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"reflection #{data['id']} written")


def list_records(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_initialized(project)
    table = table_for_type(args.type)
    with connect(project) as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE project_id = ? ORDER BY id DESC LIMIT ?",
            (project.project_id, args.limit),
        ).fetchall()
    output([row_dict(row) for row in rows], args.json)


def table_for_type(kind: str) -> str:
    tables = {
        "semantic": "semantic_facts",
        "reflection": "reflections",
        "episode": "episodes",
        "code-file": "code_files",
        "code-symbol": "code_symbols",
    }
    if kind not in tables:
        raise SystemExit(f"unsupported type: {kind}")
    return tables[kind]


def mark_stale(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_initialized(project)
    table = table_for_type(args.type)
    if table not in {"semantic_facts", "reflections"}:
        raise SystemExit("mark-stale supports semantic and reflection records")
    with connect(project) as conn:
        conn.execute(
            f"UPDATE {table} SET is_stale = 1 WHERE project_id = ? AND id = ?",
            (project.project_id, args.id),
        )
        conn.commit()
    print(f"{args.type} #{args.id} marked stale")


def slugify(text: str, fallback: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text.strip().lower()).strip("-")
    return slug[:80] or fallback


def frontmatter(record_type: str, project: Project, created_at: str) -> str:
    return (
        "---\n"
        f"type: {record_type}\n"
        f"project_id: {project.project_id}\n"
        f"created_at: {created_at}\n"
        "tags:\n"
        "  - agent-memory\n"
        f"  - {record_type}\n"
        "---\n\n"
    )


def vault_init(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_initialized(project)
    ensure_dirs(project)
    vault_index(args)
    print(f"vault initialized at {project.vault_dir}")


def write_vault_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def vault_export(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_initialized(project)
    ensure_dirs(project)
    with connect(project) as conn:
        episodes = conn.execute(
            "SELECT * FROM episodes WHERE project_id = ? ORDER BY id DESC",
            (project.project_id,),
        ).fetchall()
        facts = conn.execute(
            "SELECT * FROM semantic_facts WHERE project_id = ? ORDER BY id DESC",
            (project.project_id,),
        ).fetchall()
        reflections = conn.execute(
            "SELECT * FROM reflections WHERE project_id = ? ORDER BY id DESC",
            (project.project_id,),
        ).fetchall()
        files = conn.execute(
            "SELECT * FROM code_files WHERE project_id = ? ORDER BY file_path",
            (project.project_id,),
        ).fetchall()
        symbols = conn.execute(
            "SELECT * FROM code_symbols WHERE project_id = ? ORDER BY file_path, symbol",
            (project.project_id,),
        ).fetchall()

    for row in episodes:
        slug = slugify(row["task"], f"episode-{row['id']}")
        content = frontmatter("episode", project, row["created_at"])
        content += f"# Episode: {row['task']}\n\n"
        content += f"## Summary\n\n{row['summary']}\n\n"
        if row["outcome"]:
            content += f"## Outcome\n\n{row['outcome']}\n"
        write_vault_file(project.vault_dir / "Episodes" / f"{row['id']:04d}-{slug}.md", content)

    for row in reflections:
        slug = slugify(row["task"], f"reflection-{row['id']}")
        content = frontmatter("reflection", project, row["created_at"])
        content += f"# Reflection: {row['task']}\n\n"
        if row["summary"]:
            content += f"## Summary\n\n{row['summary']}\n\n"
        if row["mistake"]:
            content += f"## Mistake\n\n{row['mistake']}\n\n"
        content += f"## Lesson\n\n{row['lesson']}\n\n"
        if row["future_rule"]:
            content += f"## Future Rule\n\n{row['future_rule']}\n"
        write_vault_file(project.vault_dir / "Reflections" / f"{row['id']:04d}-{slug}.md", content)

    facts_content = frontmatter("semantic-facts", project, now_iso())
    facts_content += "# Semantic Facts\n\n"
    for row in facts:
        stale = " stale" if row["is_stale"] else ""
        facts_content += f"- #{row['id']} ({row['source']}, confidence {row['confidence']}{stale}): {row['fact']}\n"
    write_vault_file(project.vault_dir / "Semantic Facts" / "project-facts.md", facts_content)

    files_content = frontmatter("codebase-wiki", project, now_iso())
    files_content += "# Code Files\n\n"
    for row in files:
        files_content += f"- `{row['file_path']}` ({row['language'] or 'unknown'}): {row['summary'] or ''}\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "files.md", files_content)

    symbols_content = frontmatter("codebase-wiki", project, now_iso())
    symbols_content += "# Code Symbols\n\n"
    for row in symbols:
        symbols_content += f"- `{row['file_path']}` :: `{row['symbol']}` ({row['symbol_type'] or 'symbol'})\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "symbols.md", symbols_content)

    daily = project.vault_dir / "Daily" / f"{datetime.now().date().isoformat()}.md"
    daily_content = frontmatter("daily", project, now_iso())
    daily_content += "# Daily Agent Memory\n\n"
    daily_content += f"- Exported at {now_iso()}\n"
    write_vault_file(daily, daily_content)

    vault_index(args)
    print(f"vault exported to {project.vault_dir}")


def vault_index(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_dirs(project)
    content = "# Agent Memory Vault\n\n"
    content += "## Recent Episodes\n\n"
    for path in sorted((project.vault_dir / "Episodes").glob("*.md"), reverse=True)[:10]:
        content += f"- [[Episodes/{path.stem}]]\n"
    content += "\n## Recent Reflections\n\n"
    for path in sorted((project.vault_dir / "Reflections").glob("*.md"), reverse=True)[:10]:
        content += f"- [[Reflections/{path.stem}]]\n"
    content += "\n## Semantic Facts\n\n- [[Semantic Facts/project-facts]]\n"
    content += "\n## Codebase Wiki\n\n- [[Codebase Wiki/files]]\n- [[Codebase Wiki/symbols]]\n"
    write_vault_file(project.vault_dir / "index.md", content)


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
    return f"{language} file with {len(lines)} non-empty lines"


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
                symbols.append((name, kind))
    return symbols


def wiki_index(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_initialized(project)
    ts = now_iso()
    with connect(project) as conn:
        conn.execute("DELETE FROM code_files WHERE project_id = ?", (project.project_id,))
        conn.execute("DELETE FROM code_symbols WHERE project_id = ?", (project.project_id,))
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
                language = language_for(path)
                if not language:
                    continue
                summary = summarize_file(path, language)
                conn.execute(
                    """
                    INSERT INTO code_files(project_id, file_path, summary, language, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (project.project_id, str(rel), summary, language, ts),
                )
                for symbol, symbol_type in extract_symbols(path, language):
                    conn.execute(
                        """
                        INSERT INTO code_symbols(project_id, file_path, symbol, symbol_type, summary, calls, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (project.project_id, str(rel), symbol, symbol_type, "", "", ts),
                    )
        conn.commit()
    print("wiki index updated")


def wiki_search(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    ensure_initialized(project)
    data = collect_matches(project, args.query)["wiki_matches"]
    output(data[:20], args.json)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent_memory.py")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_project(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project", default=".")

    p = sub.add_parser("init")
    add_project(p)
    p.set_defaults(func=init_project)

    p = sub.add_parser("doctor")
    add_project(p)
    p.set_defaults(func=doctor)

    p = sub.add_parser("update")
    add_project(p)
    p.add_argument("--type", required=True, choices=["semantic", "episode"])
    p.add_argument("--fact")
    p.add_argument("--source", default="manual")
    p.add_argument("--confidence", type=float, default=0.8)
    p.add_argument("--task")
    p.add_argument("--summary")
    p.add_argument("--outcome")
    p.add_argument("--files-touched")
    p.add_argument("--commands-run")
    p.set_defaults(func=update)

    p = sub.add_parser("search")
    add_project(p)
    p.add_argument("--query", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=search)

    p = sub.add_parser("context")
    add_project(p)
    p.add_argument("--query", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=context)

    p = sub.add_parser("reflect")
    add_project(p)
    p.add_argument("--task", required=True)
    p.add_argument("--summary")
    p.add_argument("--mistake")
    p.add_argument("--lesson", required=True)
    p.add_argument("--future-rule")
    p.set_defaults(func=reflect)

    p = sub.add_parser("list")
    add_project(p)
    p.add_argument("--type", required=True, choices=["semantic", "reflection", "episode", "code-file", "code-symbol"])
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=list_records)

    p = sub.add_parser("mark-stale")
    add_project(p)
    p.add_argument("--type", required=True, choices=["semantic", "reflection"])
    p.add_argument("--id", required=True, type=int)
    p.set_defaults(func=mark_stale)

    p = sub.add_parser("vault-init")
    add_project(p)
    p.set_defaults(func=vault_init)

    p = sub.add_parser("vault-export")
    add_project(p)
    p.set_defaults(func=vault_export)

    p = sub.add_parser("vault-index")
    add_project(p)
    p.set_defaults(func=vault_index)

    p = sub.add_parser("wiki-index")
    add_project(p)
    p.set_defaults(func=wiki_index)

    p = sub.add_parser("wiki-search")
    add_project(p)
    p.add_argument("--query", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=wiki_search)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
