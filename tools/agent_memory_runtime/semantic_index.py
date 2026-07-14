# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from .models import Project
from .semantic_models import SemanticBatch, SemanticEntity, SemanticRelation
from .semantic_provider_metrics import append_provider_metric
from .semantic_runtime import run_semantic_adapter
from .storage import now_iso


SEMANTIC_RELATIONS = {
    "calls", "reads_state", "writes_state", "implements", "extends", "overrides",
    "registers_callback", "exposes_api", "consumes_api", "awaits",
}
SQL_CHUNK_SIZE = 400
SEMANTIC_FILE_BATCH_SIZE = 1000


def persist_semantic_index(
    conn: sqlite3.Connection,
    project: Project,
    scope_file_paths: list[str],
    revision: str,
) -> dict[str, Any]:
    rows = rows_for_scope(conn, project, scope_file_paths)
    grouped: dict[str, list[Path]] = defaultdict(list)
    for row in rows:
        language = str(row["language"])
        path = project.root / str(row["file_path"])
        if language in {"ArkTS", "TypeScript"} and path.is_file():
            grouped[language].append(path)
    batches: list[SemanticBatch] = []
    provider_runs: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for language, files in sorted(grouped.items()):
        for batch_index, file_batch in enumerate(semantic_file_batches(files), start=1):
            try:
                selection = run_semantic_adapter(project, language, file_batch)
                batches.append(selection.batch)
                telemetry = {**selection.telemetry, "batch": batch_index, "batch_files": len(file_batch)}
                provider_runs.append(telemetry)
                append_provider_metric(project, telemetry)
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append({"language": language, "batch": str(batch_index), "error": str(exc)[:240]})
    emitted = 0
    unresolved = 0
    for batch in batches:
        enrich_code_symbols(conn, project, batch)
        counts = persist_batch_relations(conn, project, batch, revision)
        emitted += counts["emitted"]
        unresolved += counts["unresolved"]
    return {
        "schema_version": "semantic-index/v1",
        "adapters": unique_adapters(batches),
        "capabilities": sorted({capability for batch in batches for capability in batch.capabilities}),
        "files_indexed": sum(len(batch.source_digests) for batch in batches),
        "entities": sum(len(batch.entities) for batch in batches),
        "relations_extracted": sum(len(batch.relations) for batch in batches),
        "relations_emitted": emitted,
        "unresolved_relations": unresolved,
        "gaps": [gap for batch in batches for gap in batch.gaps][:100],
        "adapter_errors": errors,
        "provider_runs": provider_runs,
    }


def semantic_file_batches(files: list[Path]) -> list[list[Path]]:
    ordered = sorted(set(files))
    return [
        ordered[index:index + SEMANTIC_FILE_BATCH_SIZE]
        for index in range(0, len(ordered), SEMANTIC_FILE_BATCH_SIZE)
    ]


def unique_adapters(batches: list[SemanticBatch]) -> list[dict[str, str]]:
    adapters = {
        (batch.adapter_id, batch.adapter_version, batch.language)
        for batch in batches
    }
    return [
        {"id": adapter_id, "version": version, "language": language}
        for adapter_id, version, language in sorted(adapters)
    ]


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
    unresolved = 0
    timestamp = now_iso()
    resolved: list[tuple[SemanticRelation, tuple[str, int, str, str, int]]] = []
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
        resolved.append((item, key))
    existing = load_existing_edges(conn, project.project_id, resolved)
    edge_ids_to_close: set[int] = set()
    insert_rows: list[tuple[Any, ...]] = []
    for item, key in resolved:
        source = (key[0], key[1])
        target = (key[3], key[4])
        current_rows = existing.get(key, [])
        if has_stronger_edge(current_rows, item.evidence_class):
            continue
        edge_ids_to_close.update(weaker_edge_ids(current_rows, item.evidence_class))
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
        insert_rows.append(
            (
                project.project_id, source[0], source[1], item.relation, target[0], target[1],
                evidence, item.confidence, revision,
                f"semantic-index:v1/{batch.adapter_id}@{batch.adapter_version}", timestamp,
                f"{item.evidence_class}_semantic_{item.relation}", timestamp, timestamp,
            )
        )
    conn.executemany(
        "UPDATE memory_edges SET valid_to = ? WHERE id = ?",
        [(timestamp, edge_id) for edge_id in sorted(edge_ids_to_close)],
    )
    conn.executemany(
        """
        INSERT INTO memory_edges(
          project_id, source_type, source_id, relation, target_type, target_id,
          evidence, confidence, source_revision, extractor_version, valid_from,
          valid_to, evidence_kind, last_verified_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
        """,
        insert_rows,
    )
    return {"emitted": len(insert_rows), "unresolved": unresolved}


def load_existing_edges(
    conn: sqlite3.Connection,
    project_id: str,
    resolved: list[tuple[SemanticRelation, tuple[str, int, str, str, int]]],
) -> dict[tuple[str, int, str, str, int], list[sqlite3.Row]]:
    source_ids: dict[str, set[int]] = defaultdict(set)
    for _item, key in resolved:
        source_ids[key[0]].add(key[1])
    grouped: dict[tuple[str, int, str, str, int], list[sqlite3.Row]] = defaultdict(list)
    for source_type, ids in source_ids.items():
        for chunk in chunks(sorted(ids)):
            rows = conn.execute(
                f"""
                SELECT id, source_type, source_id, relation, target_type, target_id, evidence_kind
                FROM memory_edges
                WHERE project_id = ? AND valid_to IS NULL AND source_type = ?
                  AND source_id IN ({','.join('?' for _ in chunk)})
                """,
                (project_id, source_type, *chunk),
            ).fetchall()
            for row in rows:
                key = (
                    str(row["source_type"]), int(row["source_id"]), str(row["relation"]),
                    str(row["target_type"]), int(row["target_id"]),
                )
                grouped[key].append(row)
    return grouped


def evidence_rank(evidence_kind: str) -> int:
    return {"exact": 4, "static": 3, "heuristic": 2, "inferred": 1}.get(
        evidence_kind.split("_", 1)[0], 0
    )


def has_stronger_edge(rows: list[sqlite3.Row], evidence_class: str) -> bool:
    return any(evidence_rank(str(row["evidence_kind"] or "legacy")) > evidence_rank(evidence_class) for row in rows)


def weaker_edge_ids(rows: list[sqlite3.Row], evidence_class: str) -> list[int]:
    rank = evidence_rank(evidence_class)
    return [
        int(row["id"])
        for row in rows
        if evidence_rank(str(row["evidence_kind"] or "legacy")) <= rank
    ]


def load_endpoint_lookup(conn: sqlite3.Connection, project: Project, batch: SemanticBatch) -> dict[str, Any]:
    paths = set(batch.source_digests)
    paths.update(item.target_file_path for item in batch.relations if item.target_file_path)
    names = {item.target_name for item in batch.relations if item.target_name}
    qualified = {item.target_qualified_name for item in batch.relations if item.target_qualified_name}
    keys = {item.target_key for item in batch.relations if item.target_key}
    symbols = load_candidate_symbols(conn, project, sorted(paths), sorted(names), sorted(qualified), sorted(keys))
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
    keys: list[str],
) -> list[sqlite3.Row]:
    selected: dict[int, sqlite3.Row] = {}
    for field, items in (
        ("file_path", paths), ("symbol", names), ("qualified_name", qualified), ("symbol_key", keys),
    ):
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
