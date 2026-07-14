# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from .models import Project
from .semantic_adapters import adapter_for
from .semantic_models import SemanticBatch, SemanticEntity, SemanticRelation
from .storage import now_iso


SEMANTIC_RELATIONS = {
    "calls", "reads_state", "writes_state", "implements", "extends", "overrides",
    "registers_callback", "exposes_api", "consumes_api", "awaits",
}
SQL_CHUNK_SIZE = 400


def persist_semantic_index(
    conn: sqlite3.Connection,
    project: Project,
    scope_file_paths: list[str],
    revision: str,
) -> dict[str, Any]:
    rows = rows_for_scope(conn, project, scope_file_paths)
    grouped: dict[str, list[Path]] = defaultdict(list)
    for row in rows:
        adapter = adapter_for(str(row["language"]))
        path = project.root / str(row["file_path"])
        if adapter and path.is_file():
            grouped[str(row["language"])].append(path)
    batches: list[SemanticBatch] = []
    errors: list[dict[str, str]] = []
    for language, files in sorted(grouped.items()):
        adapter = adapter_for(language)
        if not adapter:
            continue
        try:
            batches.append(adapter.index(project, files))
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append({"language": language, "error": str(exc)[:240]})
    emitted = 0
    unresolved = 0
    for batch in batches:
        enrich_code_symbols(conn, project, batch)
        counts = persist_batch_relations(conn, project, batch, revision)
        emitted += counts["emitted"]
        unresolved += counts["unresolved"]
    return {
        "schema_version": "semantic-index/v1",
        "adapters": [
            {"id": batch.adapter_id, "version": batch.adapter_version, "language": batch.language}
            for batch in batches
        ],
        "capabilities": sorted({capability for batch in batches for capability in batch.capabilities}),
        "files_indexed": sum(len(batch.source_digests) for batch in batches),
        "entities": sum(len(batch.entities) for batch in batches),
        "relations_extracted": sum(len(batch.relations) for batch in batches),
        "relations_emitted": emitted,
        "unresolved_relations": unresolved,
        "gaps": [gap for batch in batches for gap in batch.gaps][:100],
        "adapter_errors": errors,
    }


def rows_for_scope(conn: sqlite3.Connection, project: Project, paths: list[str]) -> list[sqlite3.Row]:
    if not paths:
        return []
    rows: list[sqlite3.Row] = []
    for chunk in chunks(paths):
        placeholders = ",".join("?" for _ in chunk)
        rows.extend(conn.execute(
            f"SELECT id, file_path, language FROM code_files WHERE project_id = ? AND file_path IN ({placeholders})",
            (project.project_id, *chunk),
        ).fetchall())
    return rows


def enrich_code_symbols(conn: sqlite3.Connection, project: Project, batch: SemanticBatch) -> None:
    paths = sorted(batch.source_digests)
    if not paths:
        return
    rows: list[sqlite3.Row] = []
    for chunk in chunks(paths):
        placeholders = ",".join("?" for _ in chunk)
        rows.extend(conn.execute(
            f"SELECT * FROM code_symbols WHERE project_id = ? AND file_path IN ({placeholders}) ORDER BY id",
            (project.project_id, *chunk),
        ).fetchall())
    grouped_rows: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        grouped_rows[(str(row["file_path"]), str(row["symbol"]))].append(row)
    used: set[int] = set()
    for entity in batch.entities:
        candidates = [row for row in grouped_rows.get((entity.file_path, entity.name), []) if int(row["id"]) not in used]
        compatible = [row for row in candidates if compatible_kind(str(row["symbol_type"] or ""), entity.kind)]
        target = (compatible or candidates)[0] if (compatible or candidates) else None
        if not target:
            continue
        used.add(int(target["id"]))
        conn.execute(
            """
            UPDATE code_symbols
            SET symbol_key = ?, qualified_name = ?, signature = ?, start_line = ?, end_line = ?,
                semantic_adapter = ?, source_digest = ?, evidence_class = ?
            WHERE project_id = ? AND id = ?
            """,
            (
                entity.key, entity.qualified_name, entity.signature, entity.start_line, entity.end_line,
                f"{batch.adapter_id}@{batch.adapter_version}", batch.source_digests.get(entity.file_path),
                entity.evidence_class, project.project_id, int(target["id"]),
            ),
        )


def compatible_kind(stored: str, semantic: str) -> bool:
    if stored == semantic:
        return True
    return (stored, semantic) in {
        ("function", "method"), ("class", "interface"), ("component", "class"),
    }


def persist_batch_relations(
    conn: sqlite3.Connection,
    project: Project,
    batch: SemanticBatch,
    revision: str,
) -> dict[str, int]:
    lookup = load_endpoint_lookup(conn, project, batch)
    emitted_keys: set[tuple[str, int, str, str, int]] = set()
    emitted = 0
    unresolved = 0
    timestamp = now_iso()
    for item in batch.relations:
        source = resolve_source(item.source_key, lookup)
        target = resolve_target(item, lookup)
        if not source or not target:
            unresolved += 1
            continue
        key = (source[0], source[1], item.relation, target[0], target[1])
        if key in emitted_keys:
            continue
        emitted_keys.add(key)
        if not supersede_weaker_edge(conn, project.project_id, key, item.evidence_class, timestamp):
            continue
        evidence = json.dumps(
            {
                "schema_version": "semantic-evidence/v1",
                "adapter": f"{batch.adapter_id}@{batch.adapter_version}",
                "language": batch.language,
                "line": item.line,
                "detail": item.detail,
                "evidence_class": item.evidence_class,
                "source_digest": batch.source_digests.get(lookup["key_paths"].get(item.source_key, "")),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        conn.execute(
            """
            INSERT INTO memory_edges(
              project_id, source_type, source_id, relation, target_type, target_id,
              evidence, confidence, source_revision, extractor_version, valid_from,
              valid_to, evidence_kind, last_verified_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
            """,
            (
                project.project_id, source[0], source[1], item.relation, target[0], target[1],
                evidence, item.confidence, revision,
                f"semantic-index:v1/{batch.adapter_id}@{batch.adapter_version}", timestamp,
                f"{item.evidence_class}_semantic_{item.relation}", timestamp, timestamp,
            ),
        )
        emitted += 1
    return {"emitted": emitted, "unresolved": unresolved}


def load_endpoint_lookup(conn: sqlite3.Connection, project: Project, batch: SemanticBatch) -> dict[str, Any]:
    paths = set(batch.source_digests)
    paths.update(item.target_file_path for item in batch.relations if item.target_file_path)
    names = {item.target_name for item in batch.relations if item.target_name}
    qualified = {item.target_qualified_name for item in batch.relations if item.target_qualified_name}
    symbols = load_candidate_symbols(conn, project, sorted(paths), sorted(names), sorted(qualified))
    files = load_candidate_files(conn, project, sorted(paths))
    by_key = unique_rows(symbols, "symbol_key")
    by_name = unique_rows(symbols, "symbol")
    by_qualified = unique_rows(symbols, "qualified_name")
    by_file_name = unique_pair_rows(symbols, "file_path", "symbol")
    by_file_qualified = unique_pair_rows(symbols, "file_path", "qualified_name")
    return {
        "by_key": by_key,
        "by_name": by_name,
        "by_qualified": by_qualified,
        "by_file_name": by_file_name,
        "by_file_qualified": by_file_qualified,
        "files": {str(row["file_path"]): row for row in files},
        "key_paths": {entity.key: entity.file_path for entity in batch.entities},
    }


def load_candidate_symbols(
    conn: sqlite3.Connection,
    project: Project,
    paths: list[str],
    names: list[str],
    qualified: list[str],
) -> list[sqlite3.Row]:
    selected: dict[int, sqlite3.Row] = {}
    for field, items in (("file_path", paths), ("symbol", names), ("qualified_name", qualified)):
        for chunk in chunks(items):
            rows = conn.execute(
                f"SELECT * FROM code_symbols WHERE project_id = ? AND {field} IN ({','.join('?' for _ in chunk)})",
                (project.project_id, *chunk),
            ).fetchall()
            selected.update({int(row["id"]): row for row in rows})
    return [selected[key] for key in sorted(selected)]


def load_candidate_files(conn: sqlite3.Connection, project: Project, paths: list[str]) -> list[sqlite3.Row]:
    rows: list[sqlite3.Row] = []
    for chunk in chunks(paths):
        rows.extend(conn.execute(
            f"SELECT * FROM code_files WHERE project_id = ? AND file_path IN ({','.join('?' for _ in chunk)})",
            (project.project_id, *chunk),
        ).fetchall())
    return rows


def chunks(items: list[Any], size: int = SQL_CHUNK_SIZE) -> list[list[Any]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def unique_rows(rows: list[sqlite3.Row], field: str) -> dict[str, sqlite3.Row]:
    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        value = str(row[field] or "")
        if value:
            grouped[value].append(row)
    return {key: values[0] for key, values in grouped.items() if len(values) == 1}


def unique_pair_rows(rows: list[sqlite3.Row], first: str, second: str) -> dict[tuple[str, str], sqlite3.Row]:
    grouped: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        key = (str(row[first] or ""), str(row[second] or ""))
        if all(key):
            grouped[key].append(row)
    return {key: values[0] for key, values in grouped.items() if len(values) == 1}


def resolve_source(key: str, lookup: dict[str, Any]) -> tuple[str, int] | None:
    if key.startswith("file:"):
        row = lookup["files"].get(key[5:])
        return ("code_file", int(row["id"])) if row else None
    row = lookup["by_key"].get(key)
    return ("code_symbol", int(row["id"])) if row else None


def resolve_target(item: SemanticRelation, lookup: dict[str, Any]) -> tuple[str, int] | None:
    row = lookup["by_key"].get(item.target_key or "")
    if not row and item.target_file_path and item.target_qualified_name:
        row = lookup["by_file_qualified"].get((item.target_file_path, item.target_qualified_name))
    if not row and item.target_file_path and item.target_name:
        row = lookup["by_file_name"].get((item.target_file_path, item.target_name))
    if not row and item.target_qualified_name:
        row = lookup["by_qualified"].get(item.target_qualified_name)
    if not row and item.target_name:
        row = lookup["by_name"].get(item.target_name)
    return ("code_symbol", int(row["id"])) if row else None


def supersede_weaker_edge(
    conn: sqlite3.Connection,
    project_id: str,
    key: tuple[str, int, str, str, int],
    evidence_class: str,
    timestamp: str,
) -> bool:
    rank = {"exact": 4, "static": 3, "heuristic": 2, "inferred": 1}
    rows = conn.execute(
        """
        SELECT id, evidence_kind FROM memory_edges
        WHERE project_id = ? AND source_type = ? AND source_id = ? AND relation = ?
          AND target_type = ? AND target_id = ? AND valid_to IS NULL
        """,
        (project_id, *key),
    ).fetchall()
    if any(
        rank.get(str(row["evidence_kind"] or "legacy").split("_", 1)[0], 0) > rank[evidence_class]
        for row in rows
    ):
        return False
    for row in rows:
        current = str(row["evidence_kind"] or "legacy").split("_", 1)[0]
        if rank.get(current, 0) <= rank[evidence_class]:
            conn.execute("UPDATE memory_edges SET valid_to = ? WHERE id = ?", (timestamp, int(row["id"])))
    return True
