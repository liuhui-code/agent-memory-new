# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3
from typing import Any, Iterable

from .semantic_mechanism_evidence import mechanism_search_terms
from .text import identifier_tokens, tokenize, unique_list


PASSAGE_SCHEMA_VERSION = "code-passages-v2"
SQL_CHUNK_SIZE = 400
CALLABLE_TYPES = {"function", "method"}
REQUIRED_PASSAGE_COLUMNS = {
    "id", "project_id", "source_type", "source_id", "passage_kind",
    "file_path", "symbol", "identity_terms", "semantic_terms", "body_terms",
    "string_terms", "mechanism_terms", "source_digest", "index_generation",
    "start_line", "end_line", "updated_at",
}


def create_code_passage_schema(conn: sqlite3.Connection) -> None:
    drop_stale_code_passage_schema(conn)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS code_passages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          source_type TEXT NOT NULL,
          source_id INTEGER NOT NULL,
          passage_kind TEXT NOT NULL,
          file_path TEXT NOT NULL,
          symbol TEXT,
          identity_terms TEXT NOT NULL DEFAULT '',
          semantic_terms TEXT NOT NULL DEFAULT '',
          body_terms TEXT NOT NULL DEFAULT '',
          string_terms TEXT NOT NULL DEFAULT '',
          mechanism_terms TEXT NOT NULL DEFAULT '',
          source_digest TEXT,
          index_generation INTEGER NOT NULL DEFAULT 0,
          start_line INTEGER,
          end_line INTEGER,
          updated_at TEXT NOT NULL,
          UNIQUE(project_id, source_type, source_id, passage_kind)
        );

        CREATE INDEX IF NOT EXISTS idx_code_passages_project_source
        ON code_passages(project_id, source_type, source_id);

        CREATE INDEX IF NOT EXISTS idx_code_passages_project_file
        ON code_passages(project_id, file_path, passage_kind);

        CREATE INDEX IF NOT EXISTS idx_code_passages_project_generation
        ON code_passages(project_id, index_generation, file_path);

        CREATE VIRTUAL TABLE IF NOT EXISTS code_passage_fts USING fts5(
          project_id UNINDEXED,
          source_type UNINDEXED,
          passage_kind UNINDEXED,
          source_id UNINDEXED,
          file_path,
          symbol,
          identity_terms,
          semantic_terms,
          body_terms,
          string_terms,
          mechanism_terms
        );

        CREATE TRIGGER IF NOT EXISTS code_passage_fts_ai
        AFTER INSERT ON code_passages BEGIN
          INSERT INTO code_passage_fts(
            rowid, project_id, source_type, passage_kind, source_id, file_path, symbol,
            identity_terms, semantic_terms, body_terms, string_terms,
            mechanism_terms
          ) VALUES (
            new.id, new.project_id, new.source_type, new.passage_kind,
            new.source_id, new.file_path, COALESCE(new.symbol, ''), new.identity_terms,
            new.semantic_terms, new.body_terms, new.string_terms,
            new.mechanism_terms
          );
        END;

        CREATE TRIGGER IF NOT EXISTS code_passage_fts_ad
        AFTER DELETE ON code_passages BEGIN
          DELETE FROM code_passage_fts WHERE rowid = old.id;
        END;

        CREATE TRIGGER IF NOT EXISTS code_passage_fts_au
        AFTER UPDATE ON code_passages BEGIN
          DELETE FROM code_passage_fts WHERE rowid = old.id;
          INSERT INTO code_passage_fts(
            rowid, project_id, source_type, passage_kind, source_id, file_path, symbol,
            identity_terms, semantic_terms, body_terms, string_terms,
            mechanism_terms
          ) VALUES (
            new.id, new.project_id, new.source_type, new.passage_kind,
            new.source_id, new.file_path, COALESCE(new.symbol, ''), new.identity_terms,
            new.semantic_terms, new.body_terms, new.string_terms,
            new.mechanism_terms
          );
        END;
        """
    )


def drop_stale_code_passage_schema(conn: sqlite3.Connection) -> None:
    columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(code_passages)").fetchall()
    }
    fts_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(code_passage_fts)").fetchall()
    }
    if not columns and not fts_columns:
        return
    if REQUIRED_PASSAGE_COLUMNS.issubset(columns) and "mechanism_terms" in fts_columns:
        return
    conn.executescript(
        """
        DROP TRIGGER IF EXISTS code_passage_fts_ai;
        DROP TRIGGER IF EXISTS code_passage_fts_ad;
        DROP TRIGGER IF EXISTS code_passage_fts_au;
        DROP TABLE IF EXISTS code_passage_fts;
        DROP TABLE IF EXISTS code_passages;
        """
    )


def rebuild_code_passages(
    conn: sqlite3.Connection,
    project_id: str,
    file_paths: list[str] | None = None,
) -> dict[str, int | str]:
    create_code_passage_schema(conn)
    normalized_paths = sorted(set(file_paths or []))
    delete_passages(conn, project_id, normalized_paths if file_paths is not None else None)
    files = source_rows(conn, "code_files", project_id, normalized_paths, file_paths)
    symbols = source_rows(conn, "code_symbols", project_id, normalized_paths, file_paths)
    rows = [*(file_passage(row) for row in files), *(symbol_passage(row) for row in symbols)]
    conn.executemany(
        """
        INSERT INTO code_passages(
          project_id, source_type, source_id, passage_kind, file_path, symbol,
          identity_terms, semantic_terms, body_terms, string_terms,
          mechanism_terms,
          source_digest, index_generation, start_line, end_line, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return {
        "schema_version": PASSAGE_SCHEMA_VERSION,
        "files_written": len(files),
        "symbols_written": len(symbols),
        "passages_written": len(rows),
    }


def delete_passages(
    conn: sqlite3.Connection,
    project_id: str,
    file_paths: list[str] | None,
) -> None:
    if file_paths is None:
        conn.execute("DELETE FROM code_passages WHERE project_id = ?", (project_id,))
        return
    for chunk in chunks(file_paths):
        placeholders = ",".join("?" for _ in chunk)
        conn.execute(
            f"DELETE FROM code_passages WHERE project_id = ? "
            f"AND file_path IN ({placeholders})",
            (project_id, *chunk),
        )


def source_rows(
    conn: sqlite3.Connection,
    table: str,
    project_id: str,
    normalized_paths: list[str],
    original_paths: list[str] | None,
) -> list[sqlite3.Row]:
    if original_paths is not None and not normalized_paths:
        return []
    if original_paths is None:
        return conn.execute(
            f"SELECT * FROM {table} WHERE project_id = ? ORDER BY id",
            (project_id,),
        ).fetchall()
    rows: list[sqlite3.Row] = []
    for chunk in chunks(normalized_paths):
        placeholders = ",".join("?" for _ in chunk)
        rows.extend(conn.execute(
            f"SELECT * FROM {table} WHERE project_id = ? "
            f"AND file_path IN ({placeholders}) ORDER BY id",
            (project_id, *chunk),
        ).fetchall())
    return rows


def file_passage(row: sqlite3.Row) -> tuple[Any, ...]:
    return (
        row["project_id"], "code_file", int(row["id"]), "file",
        row["file_path"], None,
        normalized_terms(row["file_path"], row["language"]),
        normalized_terms(row["summary"], row["business_summary"], row["business_terms"]),
        "", "", "", row["source_digest"], int(row["index_generation"] or 0),
        None, None, row["updated_at"],
    )


def symbol_passage(row: sqlite3.Row) -> tuple[Any, ...]:
    symbol_type = str(row["symbol_type"] or "symbol")
    passage_kind = "callable" if symbol_type in CALLABLE_TYPES else "symbol"
    return (
        row["project_id"], "code_symbol", int(row["id"]), passage_kind,
        row["file_path"], row["symbol"],
        normalized_terms(
            row["file_path"], row["symbol"], row["symbol_type"],
            row["qualified_name"], row["signature"],
        ),
        normalized_terms(row["summary"], row["business_summary"], row["business_terms"]),
        normalized_terms(row["method_evidence"]),
        normalized_terms(row["string_evidence"]),
        normalized_terms(mechanism_search_terms(row["mechanism_evidence"])),
        row["source_digest"], int(row["index_generation"] or 0),
        row["start_line"], row["end_line"], row["updated_at"],
    )


def normalized_terms(*values: Any) -> str:
    terms: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        terms.extend(tokenize(text))
        terms.extend(identifier_tokens(text))
    return " ".join(unique_list(term for term in terms if len(term) > 1))


def chunks(values: list[str]) -> Iterable[list[str]]:
    for index in range(0, len(values), SQL_CHUNK_SIZE):
        yield values[index:index + SQL_CHUNK_SIZE]
