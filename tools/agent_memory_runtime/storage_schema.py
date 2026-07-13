# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3

from .incident_trace_schema import create_incident_trace_schema
from .storage_migrations import create_post_migration_indexes, migrate_schema
from .storage_search_schema import create_search_schema

def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT UNIQUE NOT NULL,
          project_path TEXT NOT NULL,
          project_name TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS episodes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          task TEXT NOT NULL,
          summary TEXT NOT NULL,
          outcome TEXT,
          files_touched TEXT,
          commands_run TEXT,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS semantic_facts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          fact TEXT NOT NULL,
          source TEXT NOT NULL,
          confidence REAL DEFAULT 0.8,
          is_stale INTEGER DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reflections (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          task TEXT NOT NULL,
          summary TEXT,
          mistake TEXT,
          lesson TEXT NOT NULL,
          future_rule TEXT,
          is_stale INTEGER DEFAULT 0,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS code_files (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          file_path TEXT NOT NULL,
          summary TEXT,
          language TEXT,
          business_summary TEXT,
          business_terms TEXT,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS code_symbols (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          file_path TEXT NOT NULL,
          symbol TEXT NOT NULL,
          symbol_type TEXT,
          summary TEXT,
          calls TEXT,
          business_summary TEXT,
          business_terms TEXT,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS code_log_statements (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          file_path TEXT NOT NULL,
          line INTEGER,
          function TEXT,
          level TEXT,
          logger TEXT,
          message_template TEXT NOT NULL,
          raw_statement TEXT,
          business_summary TEXT,
          business_terms TEXT,
          business_event TEXT,
          trigger_stage TEXT,
          symptom_terms TEXT,
          likely_causes TEXT,
          process_hint TEXT,
          neighbor_terms TEXT,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memory_edges (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          source_type TEXT NOT NULL,
          source_id INTEGER NOT NULL,
          relation TEXT NOT NULL,
          target_type TEXT NOT NULL,
          target_id INTEGER NOT NULL,
          evidence TEXT,
          confidence REAL DEFAULT 0.8,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS learn_scopes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          scope_key TEXT NOT NULL,
          scope_type TEXT NOT NULL,
          source_root TEXT NOT NULL,
          target_path TEXT,
          entry_path TEXT,
          depth INTEGER,
          mode TEXT NOT NULL,
          file_snapshot TEXT NOT NULL,
          file_count INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'active',
          last_refresh_summary TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          last_refreshed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS query_misses (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          query TEXT NOT NULL,
          normalized_query TEXT,
          source TEXT DEFAULT 'context',
          result_counts TEXT,
          created_at TEXT NOT NULL,
          last_seen_at TEXT,
          miss_count INTEGER DEFAULT 1,
          reviewed_at TEXT,
          status TEXT DEFAULT 'open',
          resolution TEXT
        );

        CREATE TABLE IF NOT EXISTS reflection_reuse_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          reused_reflection_id INTEGER NOT NULL,
          applying_reflection_id INTEGER NOT NULL,
          outcome TEXT NOT NULL,
          task TEXT,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS experience_usage_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          query TEXT NOT NULL,
          normalized_query TEXT NOT NULL,
          record_type TEXT NOT NULL,
          record_id INTEGER NOT NULL,
          outcome TEXT NOT NULL,
          note TEXT,
          evidence TEXT,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS semantic_conflicts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          entity_type TEXT NOT NULL DEFAULT 'code_file',
          target TEXT NOT NULL,
          field TEXT NOT NULL,
          existing TEXT,
          incoming TEXT,
          resolution TEXT,
          decision_note TEXT,
          replacement_source TEXT,
          source_command TEXT NOT NULL,
          observed_at TEXT NOT NULL,
          status TEXT DEFAULT 'open',
          reviewed_at TEXT
        );

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
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_code_files_project_file
        ON code_files(project_id, file_path);

        CREATE INDEX IF NOT EXISTS idx_code_files_project_updated
        ON code_files(project_id, updated_at);

        CREATE INDEX IF NOT EXISTS idx_code_symbols_project_file
        ON code_symbols(project_id, file_path);

        CREATE INDEX IF NOT EXISTS idx_code_symbols_project_symbol
        ON code_symbols(project_id, symbol);

        CREATE INDEX IF NOT EXISTS idx_code_symbols_project_type
        ON code_symbols(project_id, symbol_type);

        CREATE INDEX IF NOT EXISTS idx_semantic_project_stale
        ON semantic_facts(project_id, is_stale);

        CREATE INDEX IF NOT EXISTS idx_reflections_project_stale
        ON reflections(project_id, is_stale);

        CREATE INDEX IF NOT EXISTS idx_query_misses_project_status
        ON query_misses(project_id, status);

        CREATE INDEX IF NOT EXISTS idx_query_misses_project_normalized
        ON query_misses(project_id, source, normalized_query, status);

        CREATE INDEX IF NOT EXISTS idx_reflection_reuse_project_reused
        ON reflection_reuse_events(project_id, reused_reflection_id);

        CREATE INDEX IF NOT EXISTS idx_experience_usage_project_record
        ON experience_usage_events(project_id, record_type, record_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_experience_usage_project_query
        ON experience_usage_events(project_id, normalized_query, outcome, created_at);

        CREATE INDEX IF NOT EXISTS idx_semantic_conflicts_project_status
        ON semantic_conflicts(project_id, status, observed_at);

        CREATE INDEX IF NOT EXISTS idx_retrieval_feedback_project_record
        ON retrieval_feedback(project_id, record_type, record_id, status);

        CREATE INDEX IF NOT EXISTS idx_retrieval_feedback_project_status
        ON retrieval_feedback(project_id, status, created_at);

        CREATE INDEX IF NOT EXISTS idx_code_logs_project_file
        ON code_log_statements(project_id, file_path);

        CREATE INDEX IF NOT EXISTS idx_code_logs_project_message
        ON code_log_statements(project_id, message_template);

        CREATE INDEX IF NOT EXISTS idx_code_logs_project_function
        ON code_log_statements(project_id, function);

        CREATE INDEX IF NOT EXISTS idx_memory_edges_project_source
        ON memory_edges(project_id, source_type, source_id);

        CREATE INDEX IF NOT EXISTS idx_memory_edges_project_target
        ON memory_edges(project_id, target_type, target_id);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_learn_scopes_project_scope_key
        ON learn_scopes(project_id, scope_key);
        """
    )
    create_incident_trace_schema(conn)
    migrate_schema(conn)
    create_post_migration_indexes(conn)
    create_search_schema(conn)
    conn.commit()
