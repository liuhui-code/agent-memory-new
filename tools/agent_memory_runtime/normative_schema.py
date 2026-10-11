# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3


def create_normative_schema(conn: sqlite3.Connection) -> None:
    """Create a derived Git-document index; approval remains in the source."""
    search_missing = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='normative_document_fts'"
    ).fetchone() is None
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS normative_documents (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          source_root TEXT NOT NULL,
          file_path TEXT NOT NULL,
          document_id TEXT NOT NULL,
          kind TEXT NOT NULL,
          title TEXT NOT NULL,
          status TEXT NOT NULL,
          scopes TEXT NOT NULL DEFAULT '[]',
          approval TEXT NOT NULL DEFAULT '{}',
          supersedes TEXT NOT NULL DEFAULT '',
          superseded_by TEXT NOT NULL DEFAULT '',
          body TEXT NOT NULL,
          body_start_line INTEGER NOT NULL,
          search_terms TEXT NOT NULL,
          source_digest TEXT NOT NULL,
          source_revision TEXT,
          index_generation INTEGER NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(project_id, source_root, file_path)
        );
        CREATE INDEX IF NOT EXISTS idx_normative_document_identity
          ON normative_documents(project_id, source_root, document_id);
        CREATE INDEX IF NOT EXISTS idx_normative_supersedes
          ON normative_documents(project_id, source_root, supersedes);
        CREATE VIRTUAL TABLE IF NOT EXISTS normative_document_fts USING fts5(
          project_id UNINDEXED, search_terms, tokenize='unicode61'
        );
        CREATE TRIGGER IF NOT EXISTS normative_document_insert
          AFTER INSERT ON normative_documents BEGIN
          INSERT INTO normative_document_fts(rowid, project_id, search_terms)
            VALUES (new.id, new.project_id, new.search_terms);
        END;
        CREATE TRIGGER IF NOT EXISTS normative_document_delete
          AFTER DELETE ON normative_documents BEGIN
          DELETE FROM normative_document_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS normative_document_update
          AFTER UPDATE ON normative_documents BEGIN
          DELETE FROM normative_document_fts WHERE rowid = old.id;
          INSERT INTO normative_document_fts(rowid, project_id, search_terms)
            VALUES (new.id, new.project_id, new.search_terms);
        END;
        """
    )
    if search_missing:
        rebuild_normative_search(conn)


def rebuild_normative_search(conn: sqlite3.Connection) -> None:
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='normative_document_fts'"
    ).fetchone():
        return
    conn.execute("DELETE FROM normative_document_fts")
    conn.execute(
        """INSERT INTO normative_document_fts(rowid, project_id, search_terms)
           SELECT id, project_id, search_terms FROM normative_documents"""
    )
