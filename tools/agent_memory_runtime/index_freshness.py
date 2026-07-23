# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import Project
from .storage import connect, now_iso


INDEX_EXTRACTOR_VERSION = "code-derived:v1"
DERIVED_TABLES = ("code_files", "code_symbols", "code_log_statements")


def next_index_generation(conn: sqlite3.Connection, project_id: str) -> int:
    row = conn.execute(
        "SELECT generation FROM code_index_state WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    return int(row["generation"] or 0) + 1 if row else 1


def activate_index_generation(
    conn: sqlite3.Connection,
    project_id: str,
    generation: int,
    source_revision: str,
    indexed_file_count: int,
    retired_file_count: int,
) -> None:
    conn.execute(
        """
        INSERT INTO code_index_state(
          project_id, generation, source_revision, extractor_version, status,
          indexed_file_count, retired_file_count, updated_at
        ) VALUES (?, ?, ?, ?, 'active', ?, ?, ?)
        ON CONFLICT(project_id) DO UPDATE SET
          generation=excluded.generation,
          source_revision=excluded.source_revision,
          extractor_version=excluded.extractor_version,
          status='active',
          indexed_file_count=excluded.indexed_file_count,
          retired_file_count=excluded.retired_file_count,
          updated_at=excluded.updated_at
        """,
        (
            project_id,
            generation,
            source_revision,
            INDEX_EXTRACTOR_VERSION,
            indexed_file_count,
            retired_file_count,
            now_iso(),
        ),
    )


def filter_fresh_candidate_rows(
    conn: sqlite3.Connection,
    project: Project,
    rows: dict[str, list[Any]],
) -> tuple[dict[str, list[Any]], dict[str, Any]]:
    path_rows = candidate_rows_by_path(rows)
    roots = source_roots_by_path(conn, project, set(path_rows))
    boundary_drift_ids = boundary_drift_scope_ids(
        conn, project.project_id, set(path_rows)
    )
    stale: set[str] = set()
    missing: set[str] = set()
    unverified: set[str] = set()
    current: set[str] = set()
    for file_path, candidates in path_rows.items():
        expected = {
            str(row["source_digest"])
            for _table, row in candidates
            if row["source_digest"]
        }
        if not expected:
            unverified.add(file_path)
            continue
        source = roots.get(file_path, project.root) / file_path
        if not source.is_file():
            stale.add(file_path)
            missing.add(file_path)
            continue
        observed = file_sha256(source)
        if len(expected) != 1 or observed not in expected:
            stale.add(file_path)
        else:
            current.add(file_path)
    filtered: dict[str, list[Any]] = {key: list(value) for key, value in rows.items()}
    blocked_by_table: dict[str, int] = {}
    for table in DERIVED_TABLES:
        original = rows.get(table, [])
        retained = [row for row in original if str(row["file_path"]) not in stale]
        filtered[table] = retained
        blocked_by_table[table] = len(original) - len(retained)
    state = load_index_state(conn, project.project_id)
    status = freshness_status(path_rows, stale, unverified, boundary_drift_ids)
    report = {
        "schema_version": "source-freshness/v1",
        "status": status,
        "generation": int(state.get("generation") or 0),
        "source_revision": state.get("source_revision") or "unversioned",
        "extractor_version": state.get("extractor_version") or "legacy",
        "candidate_file_count": len(path_rows),
        "checked_file_count": len(current) + len(stale),
        "current_file_count": len(current),
        "blocked_rows": sum(blocked_by_table.values()),
        "blocked_rows_by_table": blocked_by_table,
        "stale_paths": sorted(stale)[:20],
        "missing_paths": sorted(missing)[:20],
        "unverified_paths": sorted(unverified)[:20],
        "boundary_drift_scope_ids": boundary_drift_ids[:10],
        "policy": "digest_mismatch_and_missing_source_blocked",
    }
    return filtered, report


def filter_scored_derived_matches(
    project: Project,
    results: dict[str, list[dict[str, Any]]],
    previous: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    wiki = results.get("wiki_matches") or []
    derived = {
        "code_files": [item for item in wiki if item.get("kind") == "file"],
        "code_symbols": [item for item in wiki if item.get("kind") == "symbol"],
        "code_log_statements": results.get("code_log_matches") or [],
    }
    with connect(project) as conn:
        _filtered, observed = filter_fresh_candidate_rows(
            conn, project, derived
        )
        report = merge_freshness_reports(previous, observed)
        stale_paths = set(report["stale_paths"])
        if stale_paths:
            results["wiki_matches"] = [
                item for item in wiki
                if str(item.get("file_path") or "") not in stale_paths
            ]
            results["code_log_matches"] = [
                item for item in results.get("code_log_matches") or []
                if str(item.get("file_path") or "") not in stale_paths
            ]
            results["edge_matches"] = filter_stale_edges(
                conn,
                project.project_id,
                results.get("edge_matches") or [],
                stale_paths,
            )
    return results, report


def merge_freshness_reports(
    previous: dict[str, Any],
    observed: dict[str, Any],
) -> dict[str, Any]:
    report = dict(previous or observed)
    for key in ("stale_paths", "missing_paths", "unverified_paths", "boundary_drift_scope_ids"):
        report[key] = sorted(set(previous.get(key) or []) | set(observed.get(key) or []))[:20]
    previous_blocked = previous.get("blocked_rows_by_table") or {}
    observed_blocked = observed.get("blocked_rows_by_table") or {}
    report["blocked_rows_by_table"] = {
        table: int(previous_blocked.get(table) or 0) + int(observed_blocked.get(table) or 0)
        for table in DERIVED_TABLES
    }
    report["blocked_rows"] = sum(report["blocked_rows_by_table"].values())
    report["candidate_file_count"] = max(
        int(previous.get("candidate_file_count") or 0),
        int(observed.get("candidate_file_count") or 0),
    )
    report["checked_file_count"] = max(
        int(previous.get("checked_file_count") or 0),
        int(observed.get("checked_file_count") or 0),
    )
    report["current_file_count"] = max(
        int(previous.get("current_file_count") or 0),
        int(observed.get("current_file_count") or 0),
    )
    if report["stale_paths"]:
        report["status"] = "partial_current"
    elif report["unverified_paths"]:
        report["status"] = "unverified"
    elif report["boundary_drift_scope_ids"]:
        report["status"] = "boundary_drift"
    elif report["candidate_file_count"]:
        report["status"] = "current"
    else:
        report["status"] = "empty"
    return report


def filter_stale_edges(
    conn: sqlite3.Connection,
    project_id: str,
    edges: list[dict[str, Any]],
    stale_paths: set[str],
) -> list[dict[str, Any]]:
    blocked: dict[str, set[int]] = {
        "code_file": set(),
        "code_symbol": set(),
        "code_log_statement": set(),
    }
    for table, entity_type in (
        ("code_files", "code_file"),
        ("code_symbols", "code_symbol"),
        ("code_log_statements", "code_log_statement"),
    ):
        placeholders = ",".join("?" for _ in stale_paths)
        rows = conn.execute(
            f"SELECT id FROM {table} WHERE project_id = ? "
            f"AND file_path IN ({placeholders})",
            (project_id, *sorted(stale_paths)),
        ).fetchall()
        blocked[entity_type].update(int(row["id"]) for row in rows)
    return [
        edge for edge in edges
        if int(edge.get("source_id") or 0) not in blocked.get(str(edge.get("source_type") or ""), set())
        and int(edge.get("target_id") or 0) not in blocked.get(str(edge.get("target_type") or ""), set())
    ]


def candidate_rows_by_path(
    rows: dict[str, list[Any]],
) -> dict[str, list[tuple[str, Any]]]:
    grouped: dict[str, list[tuple[str, Any]]] = {}
    for table in DERIVED_TABLES:
        for row in rows.get(table, []):
            file_path = str(row["file_path"] or "").strip()
            if file_path:
                grouped.setdefault(file_path, []).append((table, row))
    return grouped


def source_roots_by_path(
    conn: sqlite3.Connection,
    project: Project,
    candidate_paths: set[str],
) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    if not candidate_paths:
        return roots
    scope_rows = conn.execute(
        """
        SELECT source_root, file_snapshot
        FROM learn_scopes
        WHERE project_id = ? AND status = 'active'
        ORDER BY updated_at DESC, id DESC
        """,
        (project.project_id,),
    ).fetchall()
    for row in scope_rows:
        try:
            paths = set(json.loads(row["file_snapshot"] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        root = Path(str(row["source_root"])).expanduser().resolve()
        for file_path in candidate_paths & paths:
            roots.setdefault(file_path, root)
    return roots


def boundary_drift_scope_ids(
    conn: sqlite3.Connection,
    project_id: str,
    candidate_paths: set[str],
) -> list[int]:
    if not candidate_paths:
        return []
    rows = conn.execute(
        """
        SELECT id, file_snapshot FROM learn_scopes
        WHERE project_id = ? AND status = 'active'
          AND refresh_state = 'boundary_drift'
        ORDER BY updated_at DESC, id DESC
        """,
        (project_id,),
    ).fetchall()
    scope_ids: list[int] = []
    for row in rows:
        try:
            paths = set(json.loads(row["file_snapshot"] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if candidate_paths & paths:
            scope_ids.append(int(row["id"]))
    return scope_ids


def load_index_state(conn: sqlite3.Connection, project_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM code_index_state WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    return dict(row) if row else {}


def index_health_summary(project: Project) -> dict[str, Any]:
    with connect(project) as conn:
        state = load_index_state(conn, project.project_id)
        totals = {
            table: int(conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE project_id = ?",
                (project.project_id,),
            ).fetchone()[0])
            for table in DERIVED_TABLES
        }
        unverified_by_table = {
            table: int(conn.execute(
                f"SELECT COUNT(*) FROM {table} "
                "WHERE project_id = ? AND (source_digest IS NULL OR source_digest = '')",
                (project.project_id,),
            ).fetchone()[0])
            for table in DERIVED_TABLES
        }
    total = sum(totals.values())
    unverified = sum(unverified_by_table.values())
    verified = total - unverified
    return {
        "schema_version": "code-index-health/v1",
        "status": "legacy_unverified" if unverified else (state.get("status") or "empty"),
        "generation": int(state.get("generation") or 0),
        "source_revision": state.get("source_revision") or "unversioned",
        "extractor_version": state.get("extractor_version") or "legacy",
        "indexed_file_count": int(state.get("indexed_file_count") or 0),
        "retired_file_count": int(state.get("retired_file_count") or 0),
        "total_rows": total,
        "verified_rows": verified,
        "digest_coverage": round(verified / total, 4) if total else 1.0,
        "unverified_rows": unverified,
        "unverified_rows_by_table": unverified_by_table,
    }


def filter_stale_path_context(value: dict[str, Any], stale_paths: list[str]) -> dict[str, Any]:
    blocked = set(stale_paths)
    if not blocked:
        return value
    filtered = dict(value)
    candidates = value.get("path_candidates") or []
    filtered["path_candidates"] = [
        item for item in candidates
        if not (path_candidate_files(item) & blocked)
    ]
    gaps = dict(value.get("gaps") or {})
    gaps["stale_source_paths"] = sorted(blocked)[:20]
    filtered["gaps"] = gaps
    return filtered


def filter_fresh_path_context(
    project: Project,
    value: dict[str, Any],
    previous: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = {
        file_path
        for candidate in value.get("path_candidates") or []
        for file_path in path_candidate_files(candidate)
    }
    if not paths:
        return value, previous
    placeholders = ",".join("?" for _ in paths)
    with connect(project) as conn:
        rows = conn.execute(
            "SELECT file_path, source_digest FROM code_files "
            f"WHERE project_id = ? AND file_path IN ({placeholders})",
            (project.project_id, *sorted(paths)),
        ).fetchall()
        _filtered, observed = filter_fresh_candidate_rows(
            conn, project, {"code_files": rows}
        )
    report = merge_freshness_reports(previous, observed)
    return filter_stale_path_context(value, report["stale_paths"]), report


def compact_freshness_report(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    compact = {
        "status": value.get("status") or "empty",
        "generation": int(value.get("generation") or 0),
    }
    if compact["status"] in {"partial_current", "unverified", "boundary_drift"}:
        compact["blocked_rows"] = int(value.get("blocked_rows") or 0)
        for key in ("stale_paths", "missing_paths", "unverified_paths"):
            paths = value.get(key) or []
            if paths:
                compact[key] = [str(path) for path in paths[:10]]
        if value.get("boundary_drift_scope_ids"):
            compact["boundary_drift_scope_ids"] = [
                int(scope_id) for scope_id in value["boundary_drift_scope_ids"][:10]
            ]
    return compact


def path_candidate_files(value: Any) -> set[str]:
    if not isinstance(value, dict):
        return set()
    paths: set[str] = set()
    for endpoint in (value.get("entry"), value.get("emitter")):
        if isinstance(endpoint, dict):
            node = endpoint.get("node") if isinstance(endpoint.get("node"), dict) else endpoint
            if node.get("file_path"):
                paths.add(str(node["file_path"]))
    for key in ("nodes", "expected_log_anchors"):
        for item in value.get(key) or []:
            if isinstance(item, dict) and item.get("file_path"):
                paths.add(str(item["file_path"]))
    return paths


def freshness_status(
    rows_by_path: dict[str, list[tuple[str, Any]]],
    stale: set[str],
    unverified: set[str],
    boundary_drift_scope_ids: list[int],
) -> str:
    if stale:
        return "partial_current"
    if unverified:
        return "unverified"
    if boundary_drift_scope_ids:
        return "boundary_drift"
    return "current" if rows_by_path else "empty"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
