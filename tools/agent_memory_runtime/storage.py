# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Project, VAULT_DIRS
from .storage_schema import create_schema

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
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn



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
