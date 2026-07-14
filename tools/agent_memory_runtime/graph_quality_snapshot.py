# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .models import Project
from .storage import now_iso


SNAPSHOT_FILE = "graph_quality_snapshot.json"


def load_graph_revision(conn: Any, project_id: str) -> int:
    row = conn.execute(
        "SELECT graph_revision FROM graph_runtime_state WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    return int(row["graph_revision"] or 0) if row else 0


def bump_graph_revision(conn: Any, project_id: str) -> int:
    ts = now_iso()
    conn.execute(
        """
        INSERT INTO graph_runtime_state(project_id, graph_revision, updated_at)
        VALUES (?, 1, ?)
        ON CONFLICT(project_id) DO UPDATE SET
          graph_revision = graph_runtime_state.graph_revision + 1,
          updated_at = excluded.updated_at
        """,
        (project_id, ts),
    )
    return load_graph_revision(conn, project_id)


def load_graph_quality_snapshot(
    project: Project,
    graph_revision: int,
) -> dict[str, Any] | None:
    path = project.runtime_dir / SNAPSHOT_FILE
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if raw.get("project_id") != project.project_id:
        return None
    if int(raw.get("graph_revision", -1)) != graph_revision:
        return None
    payload = raw.get("quality_payload")
    return payload if isinstance(payload, dict) else None


def store_graph_quality_snapshot(
    project: Project,
    graph_revision: int,
    payload: dict[str, Any],
) -> None:
    path = project.runtime_dir / SNAPSHOT_FILE
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(
            {
                "project_id": project.project_id,
                "graph_revision": graph_revision,
                "quality_payload": payload,
                "updated_at": now_iso(),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def snapshot_metadata(
    payload: dict[str, Any],
    graph_revision: int,
    status: str,
) -> dict[str, Any]:
    return {
        **payload,
        "graph_revision": graph_revision,
        "quality_revision": graph_revision,
        "snapshot_status": status,
    }
