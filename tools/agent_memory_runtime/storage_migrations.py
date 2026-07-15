# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3

from .models import CODE_BUSINESS_COLUMNS, CODE_SEMANTIC_COLUMNS, GOVERNANCE_COLUMNS

EDGE_METADATA_SCHEMA_VERSION = "edge-metadata-v1"

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
    create_design_outcomes_table(conn)
    migrate_design_outcome_columns(conn)


def migrate_memory_edge_metadata(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_schema_versions(
          component TEXT PRIMARY KEY,
          version TEXT NOT NULL
        )
        """
    )
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(memory_edges)").fetchall()}
    changed = False
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
            changed = True
    version = conn.execute(
        "SELECT version FROM runtime_schema_versions WHERE component = 'edge_metadata'"
    ).fetchone()
    if not changed and version and str(version["version"]) == EDGE_METADATA_SCHEMA_VERSION:
        return
    conn.execute(
        """
        UPDATE memory_edges
        SET extractor_version = COALESCE(NULLIF(extractor_version, ''), 'legacy'),
            evidence_kind = COALESCE(NULLIF(evidence_kind, ''), 'legacy'),
            valid_from = COALESCE(valid_from, created_at),
            last_verified_at = COALESCE(last_verified_at, created_at)
        WHERE extractor_version IS NULL OR extractor_version = ''
           OR evidence_kind IS NULL OR evidence_kind = ''
           OR valid_from IS NULL OR last_verified_at IS NULL
        """
    )
    conn.execute(
        """
        INSERT INTO runtime_schema_versions(component, version)
        VALUES ('edge_metadata', ?)
        ON CONFLICT(component) DO UPDATE SET version = excluded.version
        """,
        (EDGE_METADATA_SCHEMA_VERSION,),
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


def create_design_outcomes_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS design_outcomes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          candidate_id TEXT NOT NULL,
          contract_id TEXT NOT NULL,
          verification_status TEXT NOT NULL,
          outcome TEXT NOT NULL,
          baseline_revision INTEGER NOT NULL DEFAULT 0,
          current_revision INTEGER NOT NULL DEFAULT 0,
          planned_file_recall REAL NOT NULL DEFAULT 0,
          unplanned_file_ratio REAL NOT NULL DEFAULT 0,
          planned_symbol_recall REAL NOT NULL DEFAULT 0,
          scenario_verification_rate REAL NOT NULL DEFAULT 0,
          failed_test_count INTEGER NOT NULL DEFAULT 0,
          replan_count INTEGER NOT NULL DEFAULT 0,
          archetype TEXT NOT NULL DEFAULT 'general',
          change_size_bucket TEXT NOT NULL DEFAULT 'small',
          risk_count INTEGER NOT NULL DEFAULT 0,
          api_change_count INTEGER NOT NULL DEFAULT 0,
          graph_delta_count INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL
        )
        """
    )


def migrate_design_outcome_columns(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(design_outcomes)").fetchall()}
    for name in ("baseline_revision", "current_revision"):
        if name not in existing:
            conn.execute(f"ALTER TABLE design_outcomes ADD COLUMN {name} INTEGER NOT NULL DEFAULT 0")
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(design_outcomes)").fetchall()}
    for name, definition in (
        ("archetype", "TEXT NOT NULL DEFAULT 'general'"),
        ("change_size_bucket", "TEXT NOT NULL DEFAULT 'small'"),
        ("risk_count", "INTEGER NOT NULL DEFAULT 0"),
        ("api_change_count", "INTEGER NOT NULL DEFAULT 0"),
        ("graph_delta_count", "INTEGER NOT NULL DEFAULT 0"),
    ):
        if name not in existing:
            conn.execute(f"ALTER TABLE design_outcomes ADD COLUMN {name} {definition}")


def migrate_incident_semantic_columns(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(incident_traces)").fetchall()}
    for name in ("causal_chain", "span_graph", "intervention", "verification_evidence"):
        if name not in existing:
            conn.execute(f"ALTER TABLE incident_traces ADD COLUMN {name} TEXT")



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

        CREATE INDEX IF NOT EXISTS idx_memory_edges_project_valid_source_relation
        ON memory_edges(project_id, valid_to, source_type, source_id, relation);

        CREATE INDEX IF NOT EXISTS idx_memory_edges_project_valid_target_relation
        ON memory_edges(project_id, valid_to, target_type, target_id, relation);

        CREATE INDEX IF NOT EXISTS idx_impact_feedback_project_change
        ON impact_feedback(project_id, change_fingerprint, created_at);

        CREATE INDEX IF NOT EXISTS idx_design_outcomes_project_created
        ON design_outcomes(project_id, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_design_outcomes_project_profile
        ON design_outcomes(project_id, archetype, change_size_bucket, id DESC);

        CREATE INDEX IF NOT EXISTS idx_code_symbols_project_key
        ON code_symbols(project_id, symbol_key);

        CREATE INDEX IF NOT EXISTS idx_code_symbols_project_qualified
        ON code_symbols(project_id, file_path, qualified_name);

        CREATE INDEX IF NOT EXISTS idx_retrieval_feedback_project_type_recent
        ON retrieval_feedback(project_id, record_type, status, created_at DESC, id DESC);

        CREATE INDEX IF NOT EXISTS idx_experience_usage_project_type_recent
        ON experience_usage_events(project_id, record_type, created_at DESC, id DESC);
        """
    )
