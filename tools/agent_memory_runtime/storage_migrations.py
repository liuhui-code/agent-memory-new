# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3

from .models import CODE_BUSINESS_COLUMNS, CODE_SEMANTIC_COLUMNS, GOVERNANCE_COLUMNS

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
    for table, columns in CODE_SEMANTIC_COLUMNS.items():
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
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
    existing_conflict_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(semantic_conflicts)").fetchall()
    }
    if "entity_type" not in existing_conflict_columns:
        conn.execute("ALTER TABLE semantic_conflicts ADD COLUMN entity_type TEXT NOT NULL DEFAULT 'code_file'")
    for name, definition in (
        ("decision_note", "TEXT"),
        ("replacement_source", "TEXT"),
    ):
        if name not in existing_conflict_columns:
            conn.execute(f"ALTER TABLE semantic_conflicts ADD COLUMN {name} {definition}")
    existing_scope_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(learn_scopes)").fetchall()
    }
    for name, definition in (
        ("status", "TEXT NOT NULL DEFAULT 'active'"),
        ("last_refresh_summary", "TEXT"),
        ("last_refreshed_at", "TEXT"),
    ):
        if name not in existing_scope_columns:
            conn.execute(f"ALTER TABLE learn_scopes ADD COLUMN {name} {definition}")
    conn.execute(
        """
        UPDATE query_misses
        SET normalized_query = LOWER(TRIM(query))
        WHERE normalized_query IS NULL OR normalized_query = ''
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS retrieval_feedback (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          query TEXT NOT NULL,
          normalized_query TEXT NOT NULL,
          record_type TEXT NOT NULL,
          record_id INTEGER NOT NULL,
          reason TEXT NOT NULL,
          replacement_type TEXT,
          replacement_id INTEGER,
          note TEXT,
          status TEXT NOT NULL DEFAULT 'open',
          created_at TEXT NOT NULL,
          reviewed_at TEXT
        )
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
    migrate_memory_edge_metadata(conn)
    migrate_incident_semantic_columns(conn)
    create_impact_feedback_table(conn)


def migrate_memory_edge_metadata(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(memory_edges)").fetchall()}
    for name, definition in (
        ("source_revision", "TEXT"),
        ("extractor_version", "TEXT NOT NULL DEFAULT 'legacy'"),
        ("valid_from", "TEXT"),
        ("valid_to", "TEXT"),
        ("evidence_kind", "TEXT NOT NULL DEFAULT 'legacy'"),
        ("last_verified_at", "TEXT"),
    ):
        if name not in existing:
            conn.execute(f"ALTER TABLE memory_edges ADD COLUMN {name} {definition}")
    conn.execute(
        """
        UPDATE memory_edges
        SET extractor_version = COALESCE(NULLIF(extractor_version, ''), 'legacy'),
            evidence_kind = COALESCE(NULLIF(evidence_kind, ''), 'legacy'),
            valid_from = COALESCE(valid_from, created_at),
            last_verified_at = COALESCE(last_verified_at, created_at)
        """
    )


def create_impact_feedback_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS impact_feedback (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          change_fingerprint TEXT NOT NULL,
          changed_files TEXT NOT NULL,
          recommended_tests TEXT,
          executed_tests TEXT,
          outcome TEXT NOT NULL,
          failed_tests TEXT,
          flaky_tests TEXT,
          missed_targets TEXT,
          note TEXT,
          created_at TEXT NOT NULL
        )
        """
    )


def migrate_incident_semantic_columns(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(incident_traces)").fetchall()}
    if "causal_chain" not in existing:
        conn.execute("ALTER TABLE incident_traces ADD COLUMN causal_chain TEXT")



def create_post_migration_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_semantic_project_status_stale
        ON semantic_facts(project_id, status, is_stale);

        CREATE INDEX IF NOT EXISTS idx_reflections_project_status_stale
        ON reflections(project_id, status, is_stale);

        CREATE INDEX IF NOT EXISTS idx_memory_edges_project_valid_source
        ON memory_edges(project_id, valid_to, source_type, source_id);

        CREATE INDEX IF NOT EXISTS idx_memory_edges_project_valid_target
        ON memory_edges(project_id, valid_to, target_type, target_id);

        CREATE INDEX IF NOT EXISTS idx_impact_feedback_project_change
        ON impact_feedback(project_id, change_fingerprint, created_at);

        CREATE INDEX IF NOT EXISTS idx_code_symbols_project_key
        ON code_symbols(project_id, symbol_key);

        CREATE INDEX IF NOT EXISTS idx_code_symbols_project_qualified
        ON code_symbols(project_id, file_path, qualified_name);
        """
    )
