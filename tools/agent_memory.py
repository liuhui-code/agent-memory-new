#!/usr/bin/env python3
"""Local Agent Memory runtime.

This is the stable script API used by Agent Memory skills.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import re
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
    "code_log_statements",
    "memory_edges",
    "query_misses",
}

VAULT_DIRS = [
    "Episodes",
    "Reflections",
    "Semantic Facts",
    "Codebase Wiki",
    "Governance",
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
    ".ets": "ArkTS",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".dart": "Dart",
    ".swift": "Swift",
    ".md": "Markdown",
    ".json5": "HarmonyOS Config",
}

ACTIVE_STATUS = "active"
NON_QUERY_STATUSES = {"stale", "merged", "archived", "rejected"}
VALID_MEMORY_STATUSES = {"active", "stale", "merged", "archived", "rejected"}
NETWORK_MAX_DEPTH = 1
NETWORK_EDGE_LIMIT = 10
EVIDENCE_CHAIN_LIMIT = 3
QUERY_ALLOWED_EDGE_RELATIONS = {"contains", "emits_log", "imports", "routes_to", "uses_resource"}

GOVERNANCE_COLUMNS = {
    "semantic_facts": [
        ("status", "TEXT DEFAULT 'active'"),
        ("category", "TEXT"),
        ("scope", "TEXT"),
        ("evidence", "TEXT"),
        ("last_used_at", "TEXT"),
        ("use_count", "INTEGER DEFAULT 0"),
        ("reviewed_at", "TEXT"),
        ("merged_into_id", "INTEGER"),
        ("stale_reason", "TEXT"),
    ],
    "reflections": [
        ("status", "TEXT DEFAULT 'active'"),
        ("scope", "TEXT"),
        ("confidence", "REAL DEFAULT 0.8"),
        ("evidence", "TEXT"),
        ("trigger_condition", "TEXT"),
        ("anti_pattern", "TEXT"),
        ("repair_action", "TEXT"),
        ("applies_to", "TEXT"),
        ("does_not_apply_to", "TEXT"),
        ("last_used_at", "TEXT"),
        ("use_count", "INTEGER DEFAULT 0"),
        ("reviewed_at", "TEXT"),
        ("merged_into_id", "INTEGER"),
        ("stale_reason", "TEXT"),
        ("last_applied_at", "TEXT"),
        ("applied_count", "INTEGER DEFAULT 0"),
        ("last_outcome", "TEXT"),
    ],
    "episodes": [
        ("status", "TEXT DEFAULT 'active'"),
        ("importance", "REAL DEFAULT 0.5"),
        ("last_used_at", "TEXT"),
        ("use_count", "INTEGER DEFAULT 0"),
        ("reviewed_at", "TEXT"),
        ("derived_facts", "TEXT"),
        ("derived_reflections", "TEXT"),
    ],
}


@dataclass(frozen=True)
class Project:
    root: Path
    memory_home: Path
    memory_dir: Path
    db_path: Path
    vault_dir: Path
    runtime_dir: Path
    project_id: str
    project_name: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_memory_home(path: str | None = None) -> Path:
    raw = path or os.environ.get("AGENT_MEMORY_HOME") or "~/.agent-memory"
    return Path(raw).expanduser().resolve()


def resolve_project(path: str, memory_home: str | None = None) -> Project:
    root = Path(path).expanduser().resolve()
    project_id = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    resolved_memory_home = resolve_memory_home(memory_home)
    memory_dir = resolved_memory_home / "projects" / project_id
    return Project(
        root=root,
        memory_home=resolved_memory_home,
        memory_dir=memory_dir,
        db_path=memory_dir / "memory.db",
        vault_dir=memory_dir / "vault",
        runtime_dir=memory_dir / "runtime",
        project_id=project_id,
        project_name=root.name,
    )


def ensure_dirs(project: Project) -> None:
    project.memory_home.mkdir(parents=True, exist_ok=True)
    (project.memory_home / "projects").mkdir(parents=True, exist_ok=True)
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

        CREATE TABLE IF NOT EXISTS code_log_statements (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          file_path TEXT NOT NULL,
          line INTEGER,
          function TEXT,
          level TEXT,
          logger TEXT,
          message_template TEXT NOT NULL,
          raw_statement TEXT,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memory_edges (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          source_type TEXT NOT NULL,
          source_id INTEGER NOT NULL,
          relation TEXT NOT NULL,
          target_type TEXT NOT NULL,
          target_id INTEGER NOT NULL,
          evidence TEXT,
          confidence REAL DEFAULT 0.8,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS query_misses (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          query TEXT NOT NULL,
          source TEXT DEFAULT 'context',
          result_counts TEXT,
          created_at TEXT NOT NULL,
          reviewed_at TEXT,
          status TEXT DEFAULT 'open',
          resolution TEXT
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_code_files_project_file
        ON code_files(project_id, file_path);

        CREATE INDEX IF NOT EXISTS idx_semantic_project_stale
        ON semantic_facts(project_id, is_stale);

        CREATE INDEX IF NOT EXISTS idx_reflections_project_stale
        ON reflections(project_id, is_stale);

        CREATE INDEX IF NOT EXISTS idx_query_misses_project_status
        ON query_misses(project_id, status);

        CREATE INDEX IF NOT EXISTS idx_code_logs_project_file
        ON code_log_statements(project_id, file_path);

        CREATE INDEX IF NOT EXISTS idx_memory_edges_project_source
        ON memory_edges(project_id, source_type, source_id);

        CREATE INDEX IF NOT EXISTS idx_memory_edges_project_target
        ON memory_edges(project_id, target_type, target_id);
        """
    )
    migrate_schema(conn)
    conn.commit()


def migrate_schema(conn: sqlite3.Connection) -> None:
    for table, columns in GOVERNANCE_COLUMNS.items():
        existing = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, definition in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
    for table in ("semantic_facts", "reflections"):
        conn.execute(
            f"""
            UPDATE {table}
            SET status = 'stale'
            WHERE COALESCE(is_stale, 0) = 1
              AND COALESCE(status, 'active') = 'active'
            """
        )


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
        "memory_home": str(project.memory_home),
        "memory_dir": str(project.memory_dir),
        "runtime": "tools/agent_memory.py",
        "vault": str(project.vault_dir),
        "version": 1,
        "updated_at": now_iso(),
    }
    (project.memory_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_global_config(project: Project) -> None:
    config_path = project.memory_home / "config.json"
    config = {
        "memory_home": str(project.memory_home),
        "layout": "projects/<project_id>",
        "version": 1,
        "updated_at": now_iso(),
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def init_project(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_dirs(project)
    with connect(project) as conn:
        create_schema(conn)
        upsert_project(conn, project)
    write_global_config(project)
    write_config(project)
    vault_index(args)
    print(f"initialized agent memory for {project.root} at {project.memory_dir}")


def doctor(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    checks: list[tuple[str, bool]] = [
        ("memory home exists", project.memory_home.exists()),
        ("project memory directory exists", project.memory_dir.exists()),
        ("global config.json exists", (project.memory_home / "config.json").exists()),
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
    if not (project.memory_home / "config.json").exists():
        write_global_config(project)
    if not (project.memory_dir / "config.json").exists():
        write_config(project)


def add_semantic(args: argparse.Namespace, project: Project) -> None:
    if not args.fact:
        raise SystemExit("--fact is required for --type semantic")
    ts = now_iso()
    with connect(project) as conn:
        cur = conn.execute(
            """
            INSERT INTO semantic_facts(
              project_id, fact, source, confidence, category, scope, evidence,
              created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                args.fact,
                args.source or "manual",
                args.confidence,
                args.category,
                args.scope,
                args.evidence,
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
            INSERT INTO episodes(
              project_id, task, summary, outcome, files_touched, commands_run,
              importance, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                args.task,
                args.summary,
                args.outcome,
                args.files_touched,
                args.commands_run,
                args.importance,
                now_iso(),
            ),
        )
        conn.commit()
    print(f"episode #{cur.lastrowid} written")


def update(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
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


def memory_warning(item: dict[str, Any]) -> str | None:
    status = item.get("status") or ACTIVE_STATUS
    if status in NON_QUERY_STATUSES:
        return "This memory is not active. Verify before use."
    confidence = item.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < 0.6:
        return "This memory has low confidence. Verify against current source files."
    if item.get("is_stale"):
        return "This memory is stale. Verify against current source files."
    return None


def collect_matches(project: Project, query: str) -> dict[str, list[dict[str, Any]]]:
    tokens = tokenize(query)
    results: dict[str, list[dict[str, Any]]] = {
        "semantic_facts": [],
        "reflections": [],
        "episodes": [],
        "wiki_matches": [],
        "code_log_matches": [],
        "edge_matches": [],
    }
    with connect(project) as conn:
        semantic = conn.execute(
            """
            SELECT *
            FROM semantic_facts
            WHERE project_id = ? AND COALESCE(is_stale, 0) = 0
              AND COALESCE(status, 'active') = 'active'
            """,
            (project.project_id,),
        ).fetchall()
        reflections = conn.execute(
            """
            SELECT *
            FROM reflections
            WHERE project_id = ? AND COALESCE(is_stale, 0) = 0
              AND COALESCE(status, 'active') = 'active'
            """,
            (project.project_id,),
        ).fetchall()
        episodes = conn.execute(
            """
            SELECT *
            FROM episodes
            WHERE project_id = ? AND COALESCE(status, 'active') = 'active'
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
        logs = conn.execute(
            """
            SELECT *
            FROM code_log_statements
            WHERE project_id = ?
            """,
            (project.project_id,),
        ).fetchall()

    for row in semantic:
        score = score_text(tokens, row["fact"])
        if score:
            item = row_dict(row)
            item["score"] = score + float(row["confidence"] or 0)
            item["warning"] = memory_warning(item)
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
            item["warning"] = memory_warning(item)
            results["reflections"].append(item)

    for row in episodes:
        text = f"{row['task']} {row['summary']} {row['outcome'] or ''}"
        score = score_text(tokens, text)
        if score:
            item = row_dict(row)
            item["score"] = score
            item["warning"] = memory_warning(item)
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

    for row in logs:
        text = " ".join(
            str(row[key] or "")
            for key in ("file_path", "function", "level", "logger", "message_template", "raw_statement")
        )
        score = score_text(tokens, text)
        if score:
            item = row_dict(row)
            item["kind"] = "log_statement"
            item["score"] = score
            results["code_log_matches"].append(item)

    edge_targets: dict[str, set[int]] = {
        "code_file": set(),
        "code_symbol": set(),
        "code_log_statement": set(),
    }
    for item in results["wiki_matches"]:
        if item.get("kind") == "file":
            edge_targets["code_file"].add(int(item["id"]))
        elif item.get("kind") == "symbol":
            edge_targets["code_symbol"].add(int(item["id"]))
    for item in results["code_log_matches"]:
        edge_targets["code_log_statement"].add(int(item["id"]))
    if any(edge_targets.values()):
        results["edge_matches"] = collect_related_edges(project, edge_targets)

    for key in results:
        results[key].sort(key=lambda item: (item.get("score", 0), item.get("created_at", "")), reverse=True)
    return results


def collect_related_edges(project: Project, targets: dict[str, set[int]]) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = [project.project_id]
    for entity_type, ids in targets.items():
        for entity_id in sorted(ids):
            clauses.append("(source_type = ? AND source_id = ?)")
            values.extend([entity_type, entity_id])
            clauses.append("(target_type = ? AND target_id = ?)")
            values.extend([entity_type, entity_id])
    if not clauses:
        return []
    with connect(project) as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM memory_edges
            WHERE project_id = ?
              AND relation IN ({','.join('?' for _ in sorted(QUERY_ALLOWED_EDGE_RELATIONS))})
              AND ({' OR '.join(clauses)})
            ORDER BY confidence DESC, id DESC
            LIMIT ?
            """,
            [
                values[0],
                *sorted(QUERY_ALLOWED_EDGE_RELATIONS),
                *values[1:],
                NETWORK_EDGE_LIMIT,
            ],
        ).fetchall()
    return [row_dict(row) for row in rows]


def network_limits() -> dict[str, Any]:
    return {
        "max_depth": NETWORK_MAX_DEPTH,
        "edge_limit": NETWORK_EDGE_LIMIT,
        "evidence_chain_limit": EVIDENCE_CHAIN_LIMIT,
        "allowed_relations": sorted(QUERY_ALLOWED_EDGE_RELATIONS),
    }


def evidence_reason(edge: dict[str, Any]) -> str:
    if (
        edge.get("source_type") == "code_symbol"
        and edge.get("relation") == "emits_log"
        and edge.get("target_type") == "code_log_statement"
    ):
        return "matched log statement emitted by symbol"
    if edge.get("relation") == "contains":
        return "matched node contained by learned code file"
    if edge.get("relation") == "imports":
        return "matched file connected by ArkTS import"
    if edge.get("relation") == "routes_to":
        return "matched file connected by ArkTS router target"
    if edge.get("relation") == "uses_resource":
        return "matched ArkTS resource used by learned file"
    return "matched node connected by allowed one-hop edge"


def build_evidence_chains(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chains: list[dict[str, Any]] = []
    for edge in edges[:EVIDENCE_CHAIN_LIMIT]:
        chains.append(
            {
                "depth": NETWORK_MAX_DEPTH,
                "reason": evidence_reason(edge),
                "source_type": edge.get("source_type"),
                "source_id": edge.get("source_id"),
                "relation": edge.get("relation"),
                "target_type": edge.get("target_type"),
                "target_id": edge.get("target_id"),
                "evidence": edge.get("evidence"),
                "confidence": edge.get("confidence"),
            }
        )
    return chains


def limited_context(project: Project, query: str) -> dict[str, Any]:
    matches = collect_matches(project, query)
    context = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "query": query,
        "advisory_notice": "Memory is advisory. Current source files and explicit user instructions override stored memory.",
        "semantic_facts": matches["semantic_facts"][:3],
        "reflections": matches["reflections"][:3],
        "episodes": matches["episodes"][:2],
        "wiki_matches": matches["wiki_matches"][:5],
        "code_log_matches": matches["code_log_matches"][:5],
        "edge_matches": matches["edge_matches"][:10],
        "evidence_chains": build_evidence_chains(matches["edge_matches"]),
        "network_limits": network_limits(),
    }
    record_context_use(project, context)
    record_query_miss_if_empty(project, "context", query, context)
    return context


def record_context_use(project: Project, context_data: dict[str, Any]) -> None:
    ts = now_iso()
    updates = [
        ("semantic_facts", context_data.get("semantic_facts", [])),
        ("reflections", context_data.get("reflections", [])),
        ("episodes", context_data.get("episodes", [])),
    ]
    with connect(project) as conn:
        for table, items in updates:
            for item in items:
                conn.execute(
                    f"""
                    UPDATE {table}
                    SET use_count = COALESCE(use_count, 0) + 1,
                        last_used_at = ?
                    WHERE project_id = ? AND id = ?
                    """,
                    (ts, project.project_id, item["id"]),
                )
        conn.commit()


def result_counts(data: dict[str, Any]) -> dict[str, int]:
    return {
        key: len(value)
        for key, value in data.items()
        if isinstance(value, list)
    }


def has_any_result(data: dict[str, Any]) -> bool:
    return any(result_counts(data).values())


def record_query_miss_if_empty(project: Project, source: str, query: str, data: dict[str, Any]) -> None:
    counts = result_counts(data)
    if any(counts.values()):
        return
    with connect(project) as conn:
        conn.execute(
            """
            INSERT INTO query_misses(project_id, query, source, result_counts, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                query,
                source,
                json.dumps(counts, ensure_ascii=False),
                now_iso(),
            ),
        )
        conn.commit()


def output(data: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        if isinstance(data, dict):
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(data)


def search(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = collect_matches(project, args.query)
    record_query_miss_if_empty(project, "search", args.query, data)
    output(data, args.json)


def context(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = limited_context(project, args.query)
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_context.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output(data, args.json)


def reflect(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
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
        "scope": args.scope,
        "evidence": args.evidence,
        "confidence": args.confidence,
        "trigger_condition": args.trigger_condition,
        "anti_pattern": args.anti_pattern,
        "repair_action": args.repair_action,
        "applies_to": args.applies_to,
        "does_not_apply_to": args.does_not_apply_to,
        "created_at": now_iso(),
    }
    with connect(project) as conn:
        cur = conn.execute(
            """
            INSERT INTO reflections(
              project_id, task, summary, mistake, lesson, future_rule,
              scope, evidence, confidence, trigger_condition, anti_pattern,
              repair_action, applies_to, does_not_apply_to, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                args.task,
                args.summary,
                args.mistake,
                args.lesson,
                args.future_rule,
                args.scope,
                args.evidence,
                args.confidence,
                args.trigger_condition,
                args.anti_pattern,
                args.repair_action,
                args.applies_to,
                args.does_not_apply_to,
                data["created_at"],
            ),
        )
        if args.used_reflection_ids:
            ids = parse_ids(args.used_reflection_ids)
            conn.execute(
                f"""
                UPDATE reflections
                SET applied_count = COALESCE(applied_count, 0) + 1,
                    last_applied_at = ?,
                    last_outcome = ?
                WHERE project_id = ? AND id IN ({','.join('?' for _ in ids)})
                """,
                [data["created_at"], args.reflection_outcome, project.project_id, *ids],
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
    project = resolve_project(args.project, args.memory_home)
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
        "code-log": "code_log_statements",
        "memory-edge": "memory_edges",
    }
    if kind not in tables:
        raise SystemExit(f"unsupported type: {kind}")
    return tables[kind]


def miss_list(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    status_filter = "AND status = ?" if args.status else ""
    values: list[Any] = [project.project_id]
    if args.status:
        values.append(args.status)
    values.append(args.limit)
    with connect(project) as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM query_misses
            WHERE project_id = ? {status_filter}
            ORDER BY id DESC
            LIMIT ?
            """,
            values,
        ).fetchall()
    output([row_dict(row) for row in rows], args.json)


def miss_status(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    if args.status not in {"open", "reviewed", "resolved", "ignored"}:
        raise SystemExit(f"unsupported query miss status: {args.status}")
    with connect(project) as conn:
        conn.execute(
            """
            UPDATE query_misses
            SET status = ?, resolution = ?, reviewed_at = ?
            WHERE project_id = ? AND id = ?
            """,
            (args.status, args.resolution, now_iso(), project.project_id, args.id),
        )
        conn.commit()
    print(f"query miss #{args.id} status set to {args.status}")


def mark_stale(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    table = table_for_type(args.type)
    if table not in {"semantic_facts", "reflections"}:
        raise SystemExit("mark-stale supports semantic and reflection records")
    with connect(project) as conn:
        conn.execute(
            f"UPDATE {table} SET is_stale = 1, status = 'stale' WHERE project_id = ? AND id = ?",
            (project.project_id, args.id),
        )
        conn.commit()
    print(f"{args.type} #{args.id} marked stale")


def memory_text(row: dict[str, Any], kind: str) -> str:
    if kind == "semantic":
        return str(row.get("fact") or "")
    if kind == "reflection":
        return " ".join(
            str(row.get(key) or "")
            for key in ("task", "summary", "mistake", "lesson", "future_rule")
        )
    if kind == "episode":
        return " ".join(str(row.get(key) or "") for key in ("task", "summary", "outcome"))
    return ""


def token_set(text: str) -> set[str]:
    return {token for token in tokenize(text) if len(token) > 1}


def duplicate_candidates(rows: list[dict[str, Any]], kind: str, limit: int = 10) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    prepared = [(row, token_set(memory_text(row, kind))) for row in rows]
    for index, (left, left_tokens) in enumerate(prepared):
        if not left_tokens:
            continue
        for right, right_tokens in prepared[index + 1 :]:
            if not right_tokens:
                continue
            overlap = len(left_tokens & right_tokens)
            union = len(left_tokens | right_tokens)
            similarity = overlap / union if union else 0.0
            if similarity >= 0.55:
                candidates.append(
                    {
                        "type": kind,
                        "ids": [left["id"], right["id"]],
                        "similarity": round(similarity, 3),
                        "reason": "high token overlap",
                        "suggested_action": "review or merge",
                    }
                )
    candidates.sort(key=lambda item: item["similarity"], reverse=True)
    return candidates[:limit]


def fetch_memory_rows(conn: sqlite3.Connection, project: Project, kind: str, active_only: bool = True) -> list[dict[str, Any]]:
    table = table_for_type(kind)
    status_filter = "AND COALESCE(status, 'active') = 'active'" if active_only else ""
    stale_filter = "AND COALESCE(is_stale, 0) = 0" if table in {"semantic_facts", "reflections"} and active_only else ""
    rows = conn.execute(
        f"""
        SELECT * FROM {table}
        WHERE project_id = ? {status_filter} {stale_filter}
        ORDER BY id DESC
        """,
        (project.project_id,),
    ).fetchall()
    return [row_dict(row) for row in rows]


def maintain_health(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    with connect(project) as conn:
        semantic_rows = fetch_memory_rows(conn, project, "semantic", active_only=False)
        reflection_rows = fetch_memory_rows(conn, project, "reflection", active_only=False)
        episode_rows = fetch_memory_rows(conn, project, "episode", active_only=False)

    semantic_active = [row for row in semantic_rows if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")]
    reflection_active = [row for row in reflection_rows if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")]
    duplicate_count = len(duplicate_candidates(semantic_active, "semantic")) + len(duplicate_candidates(reflection_active, "reflection"))
    low_confidence_count = sum(1 for row in semantic_rows + reflection_rows if float(row.get("confidence") or 0.8) < 0.6)
    stale_count = sum(1 for row in semantic_rows + reflection_rows if row.get("is_stale") or row.get("status") == "stale")
    unreviewed_reflections = sum(
        1
        for row in reflection_rows
        if not row.get("reviewed_at")
        and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS
        and not row.get("is_stale")
    )

    recommended_actions: list[str] = []
    if stale_count:
        recommended_actions.append("Review stale memories and archive, merge, or refresh them.")
    if duplicate_count:
        recommended_actions.append("Run maintain-review and merge duplicate candidates.")
    if low_confidence_count:
        recommended_actions.append("Verify low-confidence memories against source files or user instructions.")
    if unreviewed_reflections:
        recommended_actions.append("Review reflections and promote durable lessons into semantic facts.")

    data = {
        "project_id": project.project_id,
        "counts": {
            "semantic_facts": len(semantic_rows),
            "reflections": len(reflection_rows),
            "episodes": len(episode_rows),
            "stale": stale_count,
            "low_confidence": low_confidence_count,
            "duplicate_candidates": duplicate_count,
            "unreviewed_reflections": unreviewed_reflections,
        },
        "recommended_actions": recommended_actions,
    }
    output(data, args.json)


def maintain_review(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = build_review_data(project, args.limit)
    output(data, args.json)


def reflect_review(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = build_reflect_review_data(project, args.limit)
    output(data, args.json)


def build_reflect_review_data(project: Project, limit: int) -> dict[str, Any]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT * FROM reflections
            WHERE project_id = ?
              AND COALESCE(status, 'active') = 'active'
              AND COALESCE(is_stale, 0) = 0
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
    items = []
    for row in rows:
        item = row_dict(row)
        issues = reflection_quality_issues(item)
        if issues:
            action = reflection_quality_action(issues)
            items.append(
                {
                    "id": item["id"],
                    "task": item["task"],
                    "issues": issues,
                    "suggested_action": action,
                    "reason": reflection_quality_reason(issues),
                }
            )
    return {"project_id": project.project_id, "reflections": items}


def reflection_quality_issues(row: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not row.get("scope"):
        issues.append("missing_scope")
    if not row.get("evidence"):
        issues.append("missing_evidence")
    if not row.get("future_rule"):
        issues.append("missing_future_rule")
    if not row.get("trigger_condition"):
        issues.append("missing_trigger_condition")
    if not row.get("repair_action"):
        issues.append("missing_repair_action")
    if is_generic_reflection_text(row.get("future_rule") or ""):
        issues.append("future_rule_too_generic")
    if is_generic_reflection_text(row.get("lesson") or ""):
        issues.append("lesson_too_generic")
    if int(row.get("applied_count") or 0) == 0:
        issues.append("never_applied")
    if row.get("last_outcome") == "misleading":
        issues.append("misleading_outcome")
    return issues


def is_generic_reflection_text(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return False
    generic_phrases = {
        "be careful",
        "be careful.",
        "do better",
        "do better.",
        "注意",
        "小心",
        "以后注意",
    }
    return normalized in generic_phrases or len(tokenize(normalized)) <= 2


def reflection_quality_reason(issues: list[str]) -> str:
    if "misleading_outcome" in issues:
        return "reflection was previously misleading"
    if reflection_quality_action(issues) == "observe":
        return "reflection has not been reused yet"
    return "reflection is not actionable enough for future tasks"


def reflection_quality_action(issues: list[str]) -> str:
    if "misleading_outcome" in issues:
        return "mark_stale"
    structural_issues = set(issues) - {"never_applied"}
    if structural_issues:
        return "rewrite"
    return "observe"


def build_review_data(project: Project, limit: int) -> dict[str, Any]:
    with connect(project) as conn:
        semantic_rows = fetch_memory_rows(conn, project, "semantic", active_only=False)
        reflection_rows = fetch_memory_rows(conn, project, "reflection", active_only=False)
        episode_rows = fetch_memory_rows(conn, project, "episode", active_only=False)

    semantic_active = [
        row for row in semantic_rows
        if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")
    ]
    reflection_active = [
        row for row in reflection_rows
        if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")
    ]
    return {
        "stale_memories": [
            row for row in semantic_rows + reflection_rows
            if row.get("is_stale") or row.get("status") == "stale"
        ][:limit],
        "low_confidence": [
            row for row in semantic_rows + reflection_rows
            if float(row.get("confidence") or 0.8) < 0.6
        ][:limit],
        "unreviewed_reflections": [
            row for row in reflection_rows
            if not row.get("reviewed_at")
            and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS
            and not row.get("is_stale")
        ][:limit],
        "unreviewed_episodes": [
            row for row in episode_rows
            if not row.get("reviewed_at") and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS
        ][:limit],
        "duplicate_candidates": (
            duplicate_candidates(semantic_active, "semantic", limit)
            + duplicate_candidates(reflection_active, "reflection", limit)
        )[:limit],
    }


def maintain_plan(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    review = build_review_data(project, args.limit)
    reflection_quality = build_reflect_review_data(project, args.limit)
    query_misses = build_query_miss_data(project, args.limit)
    actions: list[dict[str, Any]] = []

    for row in review["stale_memories"]:
        kind = "semantic" if "fact" in row else "reflection"
        reason = row.get("stale_reason") or "stale memory should be archived, refreshed, or merged"
        actions.append(
            {
                "action": "archive",
                "type": kind,
                "id": row["id"],
                "reason": reason,
                "risk": "low",
                "requires_confirmation": True,
                "command": (
                    "python tools/agent_memory.py maintain-status "
                    f"--project . --type {kind} --id {row['id']} --status archived "
                    f"--reason {json.dumps(reason, ensure_ascii=False)}"
                ),
            }
        )

    for candidate in review["duplicate_candidates"]:
        actions.append(
            {
                "action": "review",
                "type": candidate["type"],
                "ids": candidate["ids"],
                "reason": candidate["reason"],
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
            }
        )

    for row in review["low_confidence"]:
        kind = "semantic" if "fact" in row else "reflection"
        actions.append(
            {
                "action": "verify",
                "type": kind,
                "id": row["id"],
                "reason": "low-confidence memory needs source verification",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
            }
        )

    for item in reflection_quality["reflections"]:
        if item["suggested_action"] == "mark_stale":
            reason = item["reason"]
            actions.append(
                {
                    "action": "mark_stale",
                    "type": "reflection",
                    "id": item["id"],
                    "reason": reason,
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": (
                        "python tools/agent_memory.py maintain-status "
                        f"--project . --type reflection --id {item['id']} --status stale "
                        f"--reason {json.dumps(reason, ensure_ascii=False)}"
                    ),
                }
            )
        elif item["suggested_action"] == "rewrite":
            actions.append(
                {
                    "action": "rewrite_reflection",
                    "type": "reflection",
                    "id": item["id"],
                    "reason": ", ".join(item["issues"]),
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": None,
                }
            )

    for row in review["unreviewed_reflections"]:
        actions.append(
            {
                "action": "promote_or_mark_reviewed",
                "type": "reflection",
                "id": row["id"],
                "reason": "unreviewed reflection may contain a durable lesson",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
            }
        )

    for row in review["unreviewed_episodes"]:
        actions.append(
            {
                "action": "promote_or_archive",
                "type": "episode",
                "id": row["id"],
                "reason": "unreviewed episode may contain durable project knowledge",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
            }
        )

    for row in query_misses:
        actions.append(
            {
                "action": "review_query_miss",
                "type": "query_miss",
                "id": row["id"],
                "reason": "query had no memory or wiki matches",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
            }
        )

    data = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "summary": {
            "stale": len(review["stale_memories"]),
            "duplicate_candidates": len(review["duplicate_candidates"]),
            "low_confidence": len(review["low_confidence"]),
            "unreviewed_reflections": len(review["unreviewed_reflections"]),
            "unreviewed_episodes": len(review["unreviewed_episodes"]),
            "reflection_quality_issues": len(reflection_quality["reflections"]),
            "open_query_misses": len(query_misses),
        },
        "actions": actions,
        "advisory_notice": "maintain-plan only proposes actions. Execute changes only after user confirmation.",
    }
    output(data, args.json)


def build_query_miss_data(project: Project, limit: int) -> list[dict[str, Any]]:
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT * FROM query_misses
            WHERE project_id = ? AND status = 'open'
            ORDER BY id DESC
            LIMIT ?
            """,
            (project.project_id, limit),
        ).fetchall()
    return [row_dict(row) for row in rows]


def maintain_status(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    if args.status not in VALID_MEMORY_STATUSES:
        raise SystemExit(f"unsupported status: {args.status}")
    table = table_for_type(args.type)
    if table not in {"semantic_facts", "reflections", "episodes"}:
        raise SystemExit("maintain-status supports semantic, reflection, and episode records")
    ts = now_iso()
    assignments = ["status = ?", "reviewed_at = ?"]
    values: list[Any] = [args.status, ts]
    if "stale_reason" in {name for name, _ in GOVERNANCE_COLUMNS.get(table, [])}:
        assignments.append("stale_reason = ?")
        values.append(args.reason)
    if table in {"semantic_facts", "reflections"}:
        assignments.append("is_stale = ?")
        values.append(1 if args.status == "stale" else 0)
    values.extend([project.project_id, args.id])
    with connect(project) as conn:
        conn.execute(
            f"""
            UPDATE {table}
            SET {", ".join(assignments)}
            WHERE project_id = ? AND id = ?
            """,
            values,
        )
        conn.commit()
    print(f"{args.type} #{args.id} status set to {args.status}")


def parse_ids(raw: str) -> list[int]:
    ids = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not ids:
        raise SystemExit("--ids must contain at least one id")
    return ids


def maintain_merge(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    ids = parse_ids(args.ids)
    table = table_for_type(args.type)
    if table not in {"semantic_facts", "reflections"}:
        raise SystemExit("maintain-merge supports semantic and reflection records")
    ts = now_iso()
    with connect(project) as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE project_id = ? AND id IN ({','.join('?' for _ in ids)})",
            [project.project_id, *ids],
        ).fetchall()
        if len(rows) != len(set(ids)):
            raise SystemExit("some ids were not found")
        if args.type == "semantic":
            if not args.fact:
                raise SystemExit("--fact is required when merging semantic records")
            cur = conn.execute(
                """
                INSERT INTO semantic_facts(
                  project_id, fact, source, confidence, category, scope, evidence,
                  created_at, updated_at, reviewed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.project_id,
                    args.fact,
                    args.source or "maintain-merge",
                    args.confidence,
                    args.category,
                    args.scope,
                    f"merged from semantic ids: {','.join(map(str, ids))}",
                    ts,
                    ts,
                    ts,
                ),
            )
        else:
            if not args.lesson:
                raise SystemExit("--lesson is required when merging reflections")
            cur = conn.execute(
                """
                INSERT INTO reflections(
                  project_id, task, summary, mistake, lesson, future_rule,
                  scope, evidence, confidence, created_at, reviewed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.project_id,
                    args.task or "Merged reflections",
                    args.summary,
                    None,
                    args.lesson,
                    args.future_rule,
                    args.scope,
                    f"merged from reflection ids: {','.join(map(str, ids))}",
                    args.confidence,
                    ts,
                    ts,
                ),
            )
        new_id = cur.lastrowid
        conn.execute(
            f"""
            UPDATE {table}
            SET status = 'merged', merged_into_id = ?, reviewed_at = ?
            WHERE project_id = ? AND id IN ({','.join('?' for _ in ids)})
            """,
            [new_id, ts, project.project_id, *ids],
        )
        conn.commit()
    output({"merged_into_id": new_id, "source_ids": ids, "type": args.type}, args.json)


def maintain_promote(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    if not args.fact:
        raise SystemExit("--fact is required")
    if bool(args.episode_id) == bool(args.reflection_id):
        raise SystemExit("provide exactly one of --episode-id or --reflection-id")
    ts = now_iso()
    with connect(project) as conn:
        source = f"episode:{args.episode_id}" if args.episode_id else f"reflection:{args.reflection_id}"
        evidence = args.evidence or f"promoted from {source}"
        if args.episode_id:
            source_row = conn.execute(
                "SELECT * FROM episodes WHERE project_id = ? AND id = ?",
                (project.project_id, args.episode_id),
            ).fetchone()
            if not source_row:
                raise SystemExit(f"episode not found: {args.episode_id}")
        else:
            source_row = conn.execute(
                "SELECT * FROM reflections WHERE project_id = ? AND id = ?",
                (project.project_id, args.reflection_id),
            ).fetchone()
            if not source_row:
                raise SystemExit(f"reflection not found: {args.reflection_id}")
        cur = conn.execute(
            """
            INSERT INTO semantic_facts(
              project_id, fact, source, confidence, category, scope, evidence,
              created_at, updated_at, reviewed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                args.fact,
                source,
                args.confidence,
                args.category,
                args.scope,
                evidence,
                ts,
                ts,
                ts,
            ),
        )
        fact_id = cur.lastrowid
        if args.episode_id:
            conn.execute(
                """
                UPDATE episodes
                SET reviewed_at = ?, derived_facts = ?
                WHERE project_id = ? AND id = ?
                """,
                (ts, json.dumps([fact_id]), project.project_id, args.episode_id),
            )
        else:
            conn.execute(
                """
                UPDATE reflections
                SET reviewed_at = ?
                WHERE project_id = ? AND id = ?
                """,
                (ts, project.project_id, args.reflection_id),
            )
        conn.commit()
    payload = {"semantic_fact_id": fact_id}
    if args.episode_id:
        payload["episode_id"] = args.episode_id
    else:
        payload["reflection_id"] = args.reflection_id
    output(payload, args.json)


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
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    ensure_dirs(project)
    vault_index(args)
    print(f"vault initialized at {project.vault_dir}")


def write_vault_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def vault_export(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
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
        logs = conn.execute(
            "SELECT * FROM code_log_statements WHERE project_id = ? ORDER BY file_path, line",
            (project.project_id,),
        ).fetchall()
        edges = conn.execute(
            "SELECT * FROM memory_edges WHERE project_id = ? ORDER BY source_type, source_id, relation",
            (project.project_id,),
        ).fetchall()
        query_misses = conn.execute(
            "SELECT * FROM query_misses WHERE project_id = ? ORDER BY id DESC",
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
        content += f"- Status: {row['status'] or ACTIVE_STATUS}\n"
        content += f"- Confidence: {row['confidence'] or 0.8}\n"
        if row["scope"]:
            content += f"- Scope: {row['scope']}\n"
        if row["evidence"]:
            content += f"- Evidence: {row['evidence']}\n"
        content += "\n"
        if row["summary"]:
            content += f"## Summary\n\n{row['summary']}\n\n"
        if row["mistake"]:
            content += f"## Mistake\n\n{row['mistake']}\n\n"
        content += f"## Lesson\n\n{row['lesson']}\n\n"
        if row["future_rule"]:
            content += f"## Future Rule\n\n{row['future_rule']}\n"
        quality_sections = [
            ("Trigger Condition", row["trigger_condition"]),
            ("Anti Pattern", row["anti_pattern"]),
            ("Repair Action", row["repair_action"]),
            ("Applies To", row["applies_to"]),
            ("Does Not Apply To", row["does_not_apply_to"]),
        ]
        for heading, value in quality_sections:
            if value:
                content += f"\n## {heading}\n\n{value}\n"
        content += "\n## Reuse\n\n"
        content += f"- Applied count: {row['applied_count'] or 0}\n"
        content += f"- Last applied at: {row['last_applied_at'] or ''}\n"
        content += f"- Last outcome: {row['last_outcome'] or ''}\n"
        write_vault_file(project.vault_dir / "Reflections" / f"{row['id']:04d}-{slug}.md", content)

    facts_content = frontmatter("semantic-facts", project, now_iso())
    facts_content += "# Semantic Facts\n\n"
    for row in facts:
        status = row["status"] or ("stale" if row["is_stale"] else ACTIVE_STATUS)
        details = f"{row['source']}, status {status}, confidence {row['confidence']}"
        if row["scope"]:
            details += f", scope {row['scope']}"
        facts_content += f"- #{row['id']} ({details}): {row['fact']}\n"
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

    logs_content = frontmatter("codebase-wiki", project, now_iso())
    logs_content += "# Code Log Statements\n\n"
    for row in logs:
        location = f"{row['file_path']}:{row['line']}" if row["line"] else row["file_path"]
        function = f" in `{row['function']}`" if row["function"] else ""
        logs_content += (
            f"- `{location}`{function} [{row['level'] or 'log'}] "
            f"{row['message_template']}\n"
        )
    write_vault_file(project.vault_dir / "Codebase Wiki" / "log-statements.md", logs_content)

    edges_content = frontmatter("codebase-wiki", project, now_iso())
    edges_content += "# Memory Edges\n\n"
    for row in edges:
        edges_content += (
            f"- {row['source_type']} #{row['source_id']} "
            f"--{row['relation']}--> {row['target_type']} #{row['target_id']}"
        )
        if row["evidence"]:
            edges_content += f" ({row['evidence']})"
        edges_content += "\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "memory-edges.md", edges_content)

    daily = project.vault_dir / "Daily" / f"{datetime.now().date().isoformat()}.md"
    daily_content = frontmatter("daily", project, now_iso())
    daily_content += "# Daily Agent Memory\n\n"
    daily_content += f"- Exported at {now_iso()}\n"
    write_vault_file(daily, daily_content)

    write_governance_dashboard(project, facts, reflections, episodes, query_misses)
    vault_index(args)
    print(f"vault exported to {project.vault_dir}")


def write_governance_dashboard(
    project: Project,
    facts: list[sqlite3.Row],
    reflections: list[sqlite3.Row],
    episodes: list[sqlite3.Row],
    query_misses: list[sqlite3.Row],
) -> None:
    fact_rows = [row_dict(row) for row in facts]
    reflection_rows = [row_dict(row) for row in reflections]
    episode_rows = [row_dict(row) for row in episodes]
    query_miss_rows = [row_dict(row) for row in query_misses]
    active_facts = [row for row in fact_rows if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")]
    active_reflections = [row for row in reflection_rows if (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS and not row.get("is_stale")]
    stale = [
        row for row in fact_rows + reflection_rows
        if row.get("is_stale") or row.get("status") == "stale"
    ]
    low_confidence = [
        row for row in fact_rows + reflection_rows
        if float(row.get("confidence") or 0.8) < 0.6
    ]
    duplicates = duplicate_candidates(active_facts, "semantic") + duplicate_candidates(active_reflections, "reflection")
    unreviewed_reflections = [
        row for row in reflection_rows
        if not row.get("reviewed_at") and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS
    ]

    header = frontmatter("governance", project, now_iso())
    notice = "This file is generated. Edit memory through agent-memory-maintain or agent-memory-reflect.\n\n"

    health = header + "# Memory Health\n\n" + notice
    health += f"- Semantic facts: {len(fact_rows)}\n"
    health += f"- Reflections: {len(reflection_rows)}\n"
    health += f"- Episodes: {len(episode_rows)}\n"
    health += f"- Stale memories: {len(stale)}\n"
    health += f"- Low-confidence memories: {len(low_confidence)}\n"
    health += f"- Duplicate candidates: {len(duplicates)}\n"
    health += f"- Unreviewed reflections: {len(unreviewed_reflections)}\n"
    health += f"- Open query misses: {sum(1 for row in query_miss_rows if row.get('status') == 'open')}\n"
    write_vault_file(project.vault_dir / "Governance" / "Health.md", health)

    review = header + "# Review Queue\n\n" + notice
    review += "## Unreviewed Reflections\n\n"
    for row in unreviewed_reflections[:30]:
        review += f"- reflection #{row['id']}: {row['task']}\n"
    review += "\n## Unreviewed Episodes\n\n"
    for row in episode_rows[:30]:
        if not row.get("reviewed_at") and (row.get("status") or ACTIVE_STATUS) == ACTIVE_STATUS:
            review += f"- episode #{row['id']}: {row['task']}\n"
    write_vault_file(project.vault_dir / "Governance" / "Review Queue.md", review)

    stale_doc = header + "# Stale Memories\n\n" + notice
    for row in stale[:50]:
        text = row.get("fact") or row.get("lesson") or row.get("task")
        stale_doc += f"- #{row['id']} ({row.get('status') or 'stale'}): {text}\n"
    write_vault_file(project.vault_dir / "Governance" / "Stale Memories.md", stale_doc)

    merge_doc = header + "# Merge Candidates\n\n" + notice
    for item in duplicates[:50]:
        merge_doc += f"- {item['type']} ids {item['ids']} similarity {item['similarity']}: {item['reason']}\n"
    write_vault_file(project.vault_dir / "Governance" / "Merge Candidates.md", merge_doc)

    low_doc = header + "# Low Confidence\n\n" + notice
    for row in low_confidence[:50]:
        text = row.get("fact") or row.get("lesson") or row.get("task")
        low_doc += f"- #{row['id']} confidence {row.get('confidence')}: {text}\n"
    write_vault_file(project.vault_dir / "Governance" / "Low Confidence.md", low_doc)

    reflection_quality = [
        {
            "id": row["id"],
            "task": row["task"],
            "issues": reflection_quality_issues(row),
        }
        for row in active_reflections
    ]
    reflection_quality = [item for item in reflection_quality if item["issues"]]
    quality_doc = header + "# Reflection Quality\n\n" + notice
    quality_doc += "## Reflection Quality Issues\n\n"
    for item in reflection_quality[:50]:
        quality_doc += f"- reflection #{item['id']} {item['task']}: {', '.join(item['issues'])}\n"
    write_vault_file(project.vault_dir / "Governance" / "Reflection Quality.md", quality_doc)

    misses_doc = header + "# Query Misses\n\n" + notice
    for row in query_miss_rows[:50]:
        misses_doc += f"- query miss #{row['id']} ({row['status']}, {row['source']}): {row['query']}\n"
        if row.get("resolution"):
            misses_doc += f"  - resolution: {row['resolution']}\n"
    write_vault_file(project.vault_dir / "Governance" / "Query Misses.md", misses_doc)


def vault_index(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_dirs(project)
    content = "# Agent Memory Vault\n\n"
    content += "## Recent Episodes\n\n"
    for path in sorted((project.vault_dir / "Episodes").glob("*.md"), reverse=True)[:10]:
        content += f"- [[Episodes/{path.stem}]]\n"
    content += "\n## Recent Reflections\n\n"
    for path in sorted((project.vault_dir / "Reflections").glob("*.md"), reverse=True)[:10]:
        content += f"- [[Reflections/{path.stem}]]\n"
    content += "\n## Semantic Facts\n\n- [[Semantic Facts/project-facts]]\n"
    content += "\n## Codebase Wiki\n\n"
    content += "- [[Codebase Wiki/files]]\n"
    content += "- [[Codebase Wiki/symbols]]\n"
    content += "- [[Codebase Wiki/log-statements]]\n"
    content += "- [[Codebase Wiki/memory-edges]]\n"
    content += "\n## Governance\n\n"
    content += "- [[Governance/Health]]\n"
    content += "- [[Governance/Review Queue]]\n"
    content += "- [[Governance/Stale Memories]]\n"
    content += "- [[Governance/Merge Candidates]]\n"
    content += "- [[Governance/Low Confidence]]\n"
    content += "- [[Governance/Reflection Quality]]\n"
    content += "- [[Governance/Query Misses]]\n"
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
    files = collect_project_files(project)
    stats = write_wiki_index(project, files, replace=True)
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

    with connect(project) as conn:
        if replace:
            conn.execute("DELETE FROM code_files WHERE project_id = ?", (project.project_id,))
            conn.execute("DELETE FROM code_symbols WHERE project_id = ?", (project.project_id,))
            conn.execute("DELETE FROM code_log_statements WHERE project_id = ?", (project.project_id,))
        else:
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
        conn.execute("DELETE FROM memory_edges WHERE project_id = ?", (project.project_id,))
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
        rebuild_code_memory_edges(conn, project)
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


def rebuild_code_memory_edges(conn: sqlite3.Connection, project: Project) -> None:
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
    for row in symbols:
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
    for row in logs:
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

    insert_arkts_knowledge_edges(conn, project, files, symbols, ts)


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
    target = resolve_target(project, args.path)
    files = collect_path_files(project, target)
    stats = write_wiki_index(project, files, replace=args.replace)
    task = f"Learn path {target.relative_to(project.root)}"
    mode = "replaced" if args.replace else "merged"
    summary = f"{mode.capitalize()} {len(files)} files from {target.relative_to(project.root)}"
    add_episode_from_values(project, task, summary, "learned")
    payload = {
        "path": str(target.relative_to(project.root)),
        "mode": "replace" if args.replace else "merge",
        "files": [str(path.relative_to(project.root)) for path in sorted(files)],
        "count": len(files),
        "summary": summary,
        "parse_stats": stats,
    }
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


def learn_entry(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    entry = resolve_target(project, args.entry)
    if not entry.is_file():
        raise SystemExit(f"entry must be a file: {entry}")
    files = collect_entry_related_files(project, entry, args.depth)
    stats = write_wiki_index(project, files, replace=args.replace)
    rel_files = [str(path.relative_to(project.root)) for path in sorted(files)]
    payload = {
        "entry": str(entry.relative_to(project.root)),
        "depth": args.depth,
        "mode": "replace" if args.replace else "merge",
        "files": rel_files,
        "count": len(rel_files),
        "parse_stats": stats,
    }
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_learn_entry.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    add_episode_from_values(
        project,
        f"Learn entry {entry.relative_to(project.root)}",
        f"{'Replaced' if args.replace else 'Merged'} {len(rel_files)} files related to {entry.relative_to(project.root)} with depth {args.depth}",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent_memory.py")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_project(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project", default=".")
        p.add_argument("--memory-home")

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
    p.add_argument("--category")
    p.add_argument("--scope")
    p.add_argument("--evidence")
    p.add_argument("--task")
    p.add_argument("--summary")
    p.add_argument("--outcome")
    p.add_argument("--files-touched")
    p.add_argument("--commands-run")
    p.add_argument("--importance", type=float, default=0.5)
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
    p.add_argument("--scope")
    p.add_argument("--evidence")
    p.add_argument("--confidence", type=float, default=0.8)
    p.add_argument("--trigger-condition")
    p.add_argument("--anti-pattern")
    p.add_argument("--repair-action")
    p.add_argument("--applies-to")
    p.add_argument("--does-not-apply-to")
    p.add_argument("--used-reflection-ids")
    p.add_argument("--reflection-outcome")
    p.set_defaults(func=reflect)

    p = sub.add_parser("reflect-review")
    add_project(p)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=reflect_review)

    p = sub.add_parser("list")
    add_project(p)
    p.add_argument(
        "--type",
        required=True,
        choices=["semantic", "reflection", "episode", "code-file", "code-symbol", "code-log", "memory-edge"],
    )
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=list_records)

    p = sub.add_parser("miss-list")
    add_project(p)
    p.add_argument("--status", choices=["open", "reviewed", "resolved", "ignored"])
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=miss_list)

    p = sub.add_parser("miss-status")
    add_project(p)
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--status", required=True, choices=["open", "reviewed", "resolved", "ignored"])
    p.add_argument("--resolution")
    p.set_defaults(func=miss_status)

    p = sub.add_parser("mark-stale")
    add_project(p)
    p.add_argument("--type", required=True, choices=["semantic", "reflection"])
    p.add_argument("--id", required=True, type=int)
    p.set_defaults(func=mark_stale)

    p = sub.add_parser("maintain-health")
    add_project(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=maintain_health)

    p = sub.add_parser("maintain-review")
    add_project(p)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=maintain_review)

    p = sub.add_parser("maintain-plan")
    add_project(p)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=maintain_plan)

    p = sub.add_parser("maintain-status")
    add_project(p)
    p.add_argument("--type", required=True, choices=["semantic", "reflection", "episode"])
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--status", required=True, choices=sorted(VALID_MEMORY_STATUSES))
    p.add_argument("--reason")
    p.set_defaults(func=maintain_status)

    p = sub.add_parser("maintain-merge")
    add_project(p)
    p.add_argument("--type", required=True, choices=["semantic", "reflection"])
    p.add_argument("--ids", required=True)
    p.add_argument("--fact")
    p.add_argument("--lesson")
    p.add_argument("--task")
    p.add_argument("--summary")
    p.add_argument("--future-rule")
    p.add_argument("--source", default="maintain-merge")
    p.add_argument("--confidence", type=float, default=0.85)
    p.add_argument("--category")
    p.add_argument("--scope")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=maintain_merge)

    p = sub.add_parser("maintain-promote")
    add_project(p)
    p.add_argument("--episode-id", type=int)
    p.add_argument("--reflection-id", type=int)
    p.add_argument("--fact", required=True)
    p.add_argument("--confidence", type=float, default=0.85)
    p.add_argument("--category")
    p.add_argument("--scope")
    p.add_argument("--evidence")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=maintain_promote)

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

    p = sub.add_parser("learn-path")
    add_project(p)
    p.add_argument("--path", required=True)
    p.add_argument("--replace", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=learn_path)

    p = sub.add_parser("learn-entry")
    add_project(p)
    p.add_argument("--entry", required=True)
    p.add_argument("--depth", type=int, default=2)
    p.add_argument("--replace", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=learn_entry)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
