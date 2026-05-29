# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    CODE_BUSINESS_COLUMNS,
    GOVERNANCE_COLUMNS,
    Project,
    VAULT_DIRS,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_memory_home(path: str | None = None) -> Path:
    env_home = os.environ.get("AGENT_MEMORY_HOME")
    raw = path or (env_home if env_home else None)
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.cwd() / ".agent-memory").resolve()


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
          business_summary TEXT,
          business_terms TEXT,
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
          business_summary TEXT,
          business_terms TEXT,
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
          business_summary TEXT,
          business_terms TEXT,
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
          normalized_query TEXT,
          source TEXT DEFAULT 'context',
          result_counts TEXT,
          created_at TEXT NOT NULL,
          last_seen_at TEXT,
          miss_count INTEGER DEFAULT 1,
          reviewed_at TEXT,
          status TEXT DEFAULT 'open',
          resolution TEXT
        );

        CREATE TABLE IF NOT EXISTS reflection_reuse_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          reused_reflection_id INTEGER NOT NULL,
          applying_reflection_id INTEGER NOT NULL,
          outcome TEXT NOT NULL,
          task TEXT,
          created_at TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_code_files_project_file
        ON code_files(project_id, file_path);

        CREATE INDEX IF NOT EXISTS idx_semantic_project_stale
        ON semantic_facts(project_id, is_stale);

        CREATE INDEX IF NOT EXISTS idx_reflections_project_stale
        ON reflections(project_id, is_stale);

        CREATE INDEX IF NOT EXISTS idx_query_misses_project_status
        ON query_misses(project_id, status);

        CREATE INDEX IF NOT EXISTS idx_query_misses_project_normalized
        ON query_misses(project_id, source, normalized_query, status);

        CREATE INDEX IF NOT EXISTS idx_reflection_reuse_project_reused
        ON reflection_reuse_events(project_id, reused_reflection_id);

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
    for table, columns in CODE_BUSINESS_COLUMNS.items():
        existing = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, definition in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
    existing_query_miss_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(query_misses)").fetchall()
    }
    for name, definition in (
        ("normalized_query", "TEXT"),
        ("last_seen_at", "TEXT"),
        ("miss_count", "INTEGER DEFAULT 1"),
    ):
        if name not in existing_query_miss_columns:
            conn.execute(f"ALTER TABLE query_misses ADD COLUMN {name} {definition}")
    conn.execute(
        """
        UPDATE query_misses
        SET normalized_query = LOWER(TRIM(query))
        WHERE normalized_query IS NULL OR normalized_query = ''
        """
    )
    conn.execute(
        """
        UPDATE query_misses
        SET last_seen_at = created_at
        WHERE last_seen_at IS NULL OR last_seen_at = ''
        """
    )
    conn.execute(
        """
        UPDATE query_misses
        SET miss_count = 1
        WHERE miss_count IS NULL OR miss_count < 1
        """
    )
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


def ensure_initialized(project: Project) -> None:
    ensure_dirs(project)
    with connect(project) as conn:
        create_schema(conn)
        upsert_project(conn, project)
    if not (project.memory_home / "config.json").exists():
        write_global_config(project)
    if not (project.memory_dir / "config.json").exists():
        write_config(project)
