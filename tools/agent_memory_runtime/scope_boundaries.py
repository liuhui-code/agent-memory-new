# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .code_wiki_extractors import extract_symbols, language_for
from .code_wiki_imports import resolve_project_imports
from .index_freshness import file_sha256
from .models import Project
from .storage import connect, now_iso


def sync_scope_boundaries(
    project: Project,
    scope_id: int,
    learned_paths: set[str],
    consumer_paths: set[str] | None = None,
) -> int:
    consumers = sorted(consumer_paths if consumer_paths is not None else learned_paths)
    rows = discover_boundary_rows(project, learned_paths, consumers)
    ts = now_iso()
    with connect(project) as conn:
        if consumer_paths is None:
            conn.execute(
                "DELETE FROM scope_boundary_dependencies WHERE project_id = ? AND scope_id = ?",
                (project.project_id, scope_id),
            )
        elif consumers:
            placeholders = ",".join("?" for _ in consumers)
            conn.execute(
                "DELETE FROM scope_boundary_dependencies WHERE project_id = ? "
                f"AND scope_id = ? AND consumer_path IN ({placeholders})",
                (project.project_id, scope_id, *consumers),
            )
        if learned_paths:
            for chunk in chunks(sorted(learned_paths), 400):
                placeholders = ",".join("?" for _ in chunk)
                conn.execute(
                    "DELETE FROM scope_boundary_dependencies WHERE project_id = ? "
                    f"AND scope_id = ? AND dependency_path IN ({placeholders})",
                    (project.project_id, scope_id, *chunk),
                )
        conn.executemany(
            """
            INSERT INTO scope_boundary_dependencies(
              project_id, scope_id, consumer_path, dependency_path,
              dependency_kind, source_digest, surface_digest, status,
              last_observed_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'import', ?, ?, 'active', ?, ?, ?)
            ON CONFLICT(project_id, scope_id, consumer_path, dependency_path, dependency_kind)
            DO UPDATE SET source_digest=excluded.source_digest,
              surface_digest=excluded.surface_digest, status='active',
              last_observed_at=excluded.last_observed_at,
              updated_at=excluded.updated_at
            """,
            [
                (
                    project.project_id,
                    scope_id,
                    row["consumer_path"],
                    row["dependency_path"],
                    row["source_digest"],
                    row["surface_digest"],
                    ts,
                    ts,
                    ts,
                )
                for row in rows
            ],
        )
        conn.commit()
    return len(rows)


def discover_boundary_rows(
    project: Project,
    learned_paths: set[str],
    consumer_paths: list[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for consumer_path in consumer_paths:
        consumer = project.root / consumer_path
        if not consumer.is_file():
            continue
        for dependency in resolve_project_imports(project, consumer):
            dependency_path = str(dependency.relative_to(project.root))
            if dependency_path in learned_paths:
                continue
            rows.append(
                {
                    "consumer_path": consumer_path,
                    "dependency_path": dependency_path,
                    "source_digest": file_sha256(dependency),
                    "surface_digest": surface_digest(dependency),
                }
            )
    unique = {
        (row["consumer_path"], row["dependency_path"]): row
        for row in rows
    }
    return [unique[key] for key in sorted(unique)]


def load_scope_boundaries(project: Project, scope_id: int) -> list[sqlite3.Row]:
    with connect(project) as conn:
        return conn.execute(
            """
            SELECT * FROM scope_boundary_dependencies
            WHERE project_id = ? AND scope_id = ? AND status IN ('active', 'missing')
            ORDER BY dependency_path, consumer_path, id
            """,
            (project.project_id, scope_id),
        ).fetchall()


def observe_boundary_changes(
    project: Project,
    rows: list[sqlite3.Row],
    candidate_paths: set[str],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        dependency_path = str(row["dependency_path"])
        if dependency_path in candidate_paths:
            grouped.setdefault(dependency_path, []).append(row)
    changes: list[dict[str, Any]] = []
    for dependency_path, dependencies in sorted(grouped.items()):
        source = project.root / dependency_path
        missing = not source.is_file()
        digest = None if missing else file_sha256(source)
        surface = None if missing else surface_digest(source)
        previous_digests = {row["source_digest"] for row in dependencies}
        previous_surfaces = {row["surface_digest"] for row in dependencies}
        if digest in previous_digests and surface in previous_surfaces and not missing:
            continue
        changes.append(
            {
                "dependency_path": dependency_path,
                "consumer_paths": sorted({str(row["consumer_path"]) for row in dependencies}),
                "missing": missing,
                "content_changed": digest not in previous_digests,
                "surface_changed": surface not in previous_surfaces,
                "source_digest": digest,
                "surface_digest": surface,
                "row_ids": [int(row["id"]) for row in dependencies],
            }
        )
    return changes


def apply_boundary_observations(project: Project, changes: list[dict[str, Any]]) -> None:
    ts = now_iso()
    with connect(project) as conn:
        for change in changes:
            row_ids = change.get("row_ids") or []
            if not row_ids:
                continue
            placeholders = ",".join("?" for _ in row_ids)
            conn.execute(
                "UPDATE scope_boundary_dependencies SET source_digest = ?, "
                "surface_digest = ?, status = ?, last_observed_at = ?, updated_at = ? "
                f"WHERE project_id = ? AND id IN ({placeholders})",
                (
                    change.get("source_digest"),
                    change.get("surface_digest"),
                    "missing" if change.get("missing") else "active",
                    ts,
                    ts,
                    project.project_id,
                    *row_ids,
                ),
            )
        conn.commit()


def public_boundary_changes(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: value for key, value in change.items() if key not in {"row_ids", "source_digest", "surface_digest"}}
        for change in changes
    ]


def surface_digest(path: Path) -> str:
    language = language_for(path) or "Unknown"
    symbols = sorted(extract_symbols(path, language))
    payload = json.dumps(symbols, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index:index + size] for index in range(0, len(values), size)]
