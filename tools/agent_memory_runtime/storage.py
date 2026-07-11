# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .incident_trace_schema import create_incident_trace_schema
from .models import (
    CODE_BUSINESS_COLUMNS,
    GOVERNANCE_COLUMNS,
    Project,
    VAULT_DIRS,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_memory_home(path: str | None = None) -> Path:
    env_home = os.environ.get("AGENT_MEMORY_HOME")
    raw = path or (env_home if env_home else None)
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.cwd() / ".agent-memory").resolve()


def resolve_project(path: str, memory_home: str | None = None) -> Project:
    root = Path(path).expanduser().resolve()
    project_id = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    resolved_memory_home = resolve_memory_home(memory_home)
    memory_dir = resolved_memory_home / "projects" / project_id
    return Project(
        root=root,
        memory_home=resolved_memory_home,
        memory_dir=memory_dir,
        db_path=memory_dir / "memory.db",
        vault_dir=memory_dir / "vault",
        runtime_dir=memory_dir / "runtime",
        project_id=project_id,
        project_name=root.name,
    )


def ensure_dirs(project: Project) -> None:
    project.memory_home.mkdir(parents=True, exist_ok=True)
    (project.memory_home / "projects").mkdir(parents=True, exist_ok=True)
    project.memory_dir.mkdir(parents=True, exist_ok=True)
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    project.vault_dir.mkdir(parents=True, exist_ok=True)
    for name in VAULT_DIRS:
        (project.vault_dir / name).mkdir(parents=True, exist_ok=True)


def connect(project: Project) -> sqlite3.Connection:
    conn = sqlite3.connect(project.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


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


def create_post_migration_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_semantic_project_status_stale
        ON semantic_facts(project_id, status, is_stale);

        CREATE INDEX IF NOT EXISTS idx_reflections_project_status_stale
        ON reflections(project_id, status, is_stale);
        """
    )


def create_search_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS semantic_fact_fts USING fts5(
          project_id UNINDEXED,
          fact,
          source,
          category,
          scope,
          evidence
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS reflection_fts USING fts5(
          project_id UNINDEXED,
          task,
          summary,
          mistake,
          lesson,
          future_rule,
          task_type,
          outcome,
          problem,
          reasoning_summary,
          context_used,
          what_worked,
          what_failed,
          hidden_assumptions,
          negative_preconditions,
          useful_followup_focus,
          useful_followup_terms,
          misleading_followup_terms,
          inspection_targets,
          final_verification_path,
          related_cases,
          verification_method,
          reuse_feedback,
          source_cases,
          skill_candidate,
          trigger_condition,
          anti_pattern,
          repair_action,
          evidence
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS episode_fts USING fts5(
          project_id UNINDEXED,
          task,
          summary,
          outcome,
          files_touched,
          commands_run
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS code_file_fts USING fts5(
          project_id UNINDEXED,
          file_path,
          summary,
          language,
          business_summary,
          business_terms
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS code_symbol_fts USING fts5(
          project_id UNINDEXED,
          file_path,
          symbol,
          symbol_type,
          summary,
          business_summary,
          business_terms
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS code_log_fts USING fts5(
          project_id UNINDEXED,
          file_path,
          function,
          level,
          logger,
          message_template,
          raw_statement,
          business_summary,
          business_terms,
          business_event,
          trigger_stage,
          symptom_terms,
          likely_causes,
          process_hint,
          neighbor_terms
        );
        """
    )
    create_search_triggers(conn)
    rebuild_search_indexes(conn)


def create_search_triggers(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS semantic_fact_fts_ai AFTER INSERT ON semantic_facts BEGIN
          INSERT INTO semantic_fact_fts(rowid, project_id, fact, source, category, scope, evidence)
          VALUES (new.id, new.project_id, COALESCE(new.fact, ''), COALESCE(new.source, ''), COALESCE(new.category, ''), COALESCE(new.scope, ''), COALESCE(new.evidence, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS semantic_fact_fts_ad AFTER DELETE ON semantic_facts BEGIN
          DELETE FROM semantic_fact_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS semantic_fact_fts_au AFTER UPDATE ON semantic_facts BEGIN
          DELETE FROM semantic_fact_fts WHERE rowid = old.id;
          INSERT INTO semantic_fact_fts(rowid, project_id, fact, source, category, scope, evidence)
          VALUES (new.id, new.project_id, COALESCE(new.fact, ''), COALESCE(new.source, ''), COALESCE(new.category, ''), COALESCE(new.scope, ''), COALESCE(new.evidence, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS reflection_fts_ai AFTER INSERT ON reflections BEGIN
          INSERT INTO reflection_fts(rowid, project_id, task, summary, mistake, lesson, future_rule, task_type, outcome, problem, reasoning_summary, context_used, what_worked, what_failed, hidden_assumptions, negative_preconditions, useful_followup_focus, useful_followup_terms, misleading_followup_terms, inspection_targets, final_verification_path, related_cases, verification_method, reuse_feedback, source_cases, skill_candidate, trigger_condition, anti_pattern, repair_action, evidence)
          VALUES (new.id, new.project_id, COALESCE(new.task, ''), COALESCE(new.summary, ''), COALESCE(new.mistake, ''), COALESCE(new.lesson, ''), COALESCE(new.future_rule, ''), COALESCE(new.task_type, ''), COALESCE(new.outcome, ''), COALESCE(new.problem, ''), COALESCE(new.reasoning_summary, ''), COALESCE(new.context_used, ''), COALESCE(new.what_worked, ''), COALESCE(new.what_failed, ''), COALESCE(new.hidden_assumptions, ''), COALESCE(new.negative_preconditions, ''), COALESCE(new.useful_followup_focus, ''), COALESCE(new.useful_followup_terms, ''), COALESCE(new.misleading_followup_terms, ''), COALESCE(new.inspection_targets, ''), COALESCE(new.final_verification_path, ''), COALESCE(new.related_cases, ''), COALESCE(new.verification_method, ''), COALESCE(new.reuse_feedback, ''), COALESCE(new.source_cases, ''), COALESCE(new.skill_candidate, ''), COALESCE(new.trigger_condition, ''), COALESCE(new.anti_pattern, ''), COALESCE(new.repair_action, ''), COALESCE(new.evidence, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS reflection_fts_ad AFTER DELETE ON reflections BEGIN
          DELETE FROM reflection_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS reflection_fts_au AFTER UPDATE ON reflections BEGIN
          DELETE FROM reflection_fts WHERE rowid = old.id;
          INSERT INTO reflection_fts(rowid, project_id, task, summary, mistake, lesson, future_rule, task_type, outcome, problem, reasoning_summary, context_used, what_worked, what_failed, hidden_assumptions, negative_preconditions, useful_followup_focus, useful_followup_terms, misleading_followup_terms, inspection_targets, final_verification_path, related_cases, verification_method, reuse_feedback, source_cases, skill_candidate, trigger_condition, anti_pattern, repair_action, evidence)
          VALUES (new.id, new.project_id, COALESCE(new.task, ''), COALESCE(new.summary, ''), COALESCE(new.mistake, ''), COALESCE(new.lesson, ''), COALESCE(new.future_rule, ''), COALESCE(new.task_type, ''), COALESCE(new.outcome, ''), COALESCE(new.problem, ''), COALESCE(new.reasoning_summary, ''), COALESCE(new.context_used, ''), COALESCE(new.what_worked, ''), COALESCE(new.what_failed, ''), COALESCE(new.hidden_assumptions, ''), COALESCE(new.negative_preconditions, ''), COALESCE(new.useful_followup_focus, ''), COALESCE(new.useful_followup_terms, ''), COALESCE(new.misleading_followup_terms, ''), COALESCE(new.inspection_targets, ''), COALESCE(new.final_verification_path, ''), COALESCE(new.related_cases, ''), COALESCE(new.verification_method, ''), COALESCE(new.reuse_feedback, ''), COALESCE(new.source_cases, ''), COALESCE(new.skill_candidate, ''), COALESCE(new.trigger_condition, ''), COALESCE(new.anti_pattern, ''), COALESCE(new.repair_action, ''), COALESCE(new.evidence, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS episode_fts_ai AFTER INSERT ON episodes BEGIN
          INSERT INTO episode_fts(rowid, project_id, task, summary, outcome, files_touched, commands_run)
          VALUES (new.id, new.project_id, COALESCE(new.task, ''), COALESCE(new.summary, ''), COALESCE(new.outcome, ''), COALESCE(new.files_touched, ''), COALESCE(new.commands_run, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS episode_fts_ad AFTER DELETE ON episodes BEGIN
          DELETE FROM episode_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS episode_fts_au AFTER UPDATE ON episodes BEGIN
          DELETE FROM episode_fts WHERE rowid = old.id;
          INSERT INTO episode_fts(rowid, project_id, task, summary, outcome, files_touched, commands_run)
          VALUES (new.id, new.project_id, COALESCE(new.task, ''), COALESCE(new.summary, ''), COALESCE(new.outcome, ''), COALESCE(new.files_touched, ''), COALESCE(new.commands_run, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS code_file_fts_ai AFTER INSERT ON code_files BEGIN
          INSERT INTO code_file_fts(rowid, project_id, file_path, summary, language, business_summary, business_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.summary, ''), COALESCE(new.language, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS code_file_fts_ad AFTER DELETE ON code_files BEGIN
          DELETE FROM code_file_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS code_file_fts_au AFTER UPDATE ON code_files BEGIN
          DELETE FROM code_file_fts WHERE rowid = old.id;
          INSERT INTO code_file_fts(rowid, project_id, file_path, summary, language, business_summary, business_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.summary, ''), COALESCE(new.language, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS code_symbol_fts_ai AFTER INSERT ON code_symbols BEGIN
          INSERT INTO code_symbol_fts(rowid, project_id, file_path, symbol, symbol_type, summary, business_summary, business_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.symbol, ''), COALESCE(new.symbol_type, ''), COALESCE(new.summary, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS code_symbol_fts_ad AFTER DELETE ON code_symbols BEGIN
          DELETE FROM code_symbol_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS code_symbol_fts_au AFTER UPDATE ON code_symbols BEGIN
          DELETE FROM code_symbol_fts WHERE rowid = old.id;
          INSERT INTO code_symbol_fts(rowid, project_id, file_path, symbol, symbol_type, summary, business_summary, business_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.symbol, ''), COALESCE(new.symbol_type, ''), COALESCE(new.summary, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS code_log_fts_ai AFTER INSERT ON code_log_statements BEGIN
          INSERT INTO code_log_fts(rowid, project_id, file_path, function, level, logger, message_template, raw_statement, business_summary, business_terms, business_event, trigger_stage, symptom_terms, likely_causes, process_hint, neighbor_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.function, ''), COALESCE(new.level, ''), COALESCE(new.logger, ''), COALESCE(new.message_template, ''), COALESCE(new.raw_statement, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''), COALESCE(new.business_event, ''), COALESCE(new.trigger_stage, ''), COALESCE(new.symptom_terms, ''), COALESCE(new.likely_causes, ''), COALESCE(new.process_hint, ''), COALESCE(new.neighbor_terms, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS code_log_fts_ad AFTER DELETE ON code_log_statements BEGIN
          DELETE FROM code_log_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS code_log_fts_au AFTER UPDATE ON code_log_statements BEGIN
          DELETE FROM code_log_fts WHERE rowid = old.id;
          INSERT INTO code_log_fts(rowid, project_id, file_path, function, level, logger, message_template, raw_statement, business_summary, business_terms, business_event, trigger_stage, symptom_terms, likely_causes, process_hint, neighbor_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.function, ''), COALESCE(new.level, ''), COALESCE(new.logger, ''), COALESCE(new.message_template, ''), COALESCE(new.raw_statement, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''), COALESCE(new.business_event, ''), COALESCE(new.trigger_stage, ''), COALESCE(new.symptom_terms, ''), COALESCE(new.likely_causes, ''), COALESCE(new.process_hint, ''), COALESCE(new.neighbor_terms, ''));
        END;
        """
    )


def rebuild_search_indexes(conn: sqlite3.Connection) -> None:
    tables = (
        "semantic_fact_fts",
        "reflection_fts",
        "episode_fts",
        "code_file_fts",
        "code_symbol_fts",
        "code_log_fts",
    )
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.execute(
        """
        INSERT INTO semantic_fact_fts(rowid, project_id, fact, source, category, scope, evidence)
        SELECT id, project_id, COALESCE(fact, ''), COALESCE(source, ''), COALESCE(category, ''), COALESCE(scope, ''), COALESCE(evidence, '')
        FROM semantic_facts
        """
    )
    conn.execute(
        """
        INSERT INTO reflection_fts(rowid, project_id, task, summary, mistake, lesson, future_rule, task_type, outcome, problem, reasoning_summary, context_used, what_worked, what_failed, hidden_assumptions, negative_preconditions, useful_followup_focus, useful_followup_terms, misleading_followup_terms, inspection_targets, final_verification_path, related_cases, verification_method, reuse_feedback, source_cases, skill_candidate, trigger_condition, anti_pattern, repair_action, evidence)
        SELECT id, project_id, COALESCE(task, ''), COALESCE(summary, ''), COALESCE(mistake, ''), COALESCE(lesson, ''), COALESCE(future_rule, ''), COALESCE(task_type, ''), COALESCE(outcome, ''), COALESCE(problem, ''), COALESCE(reasoning_summary, ''), COALESCE(context_used, ''), COALESCE(what_worked, ''), COALESCE(what_failed, ''), COALESCE(hidden_assumptions, ''), COALESCE(negative_preconditions, ''), COALESCE(useful_followup_focus, ''), COALESCE(useful_followup_terms, ''), COALESCE(misleading_followup_terms, ''), COALESCE(inspection_targets, ''), COALESCE(final_verification_path, ''), COALESCE(related_cases, ''), COALESCE(verification_method, ''), COALESCE(reuse_feedback, ''), COALESCE(source_cases, ''), COALESCE(skill_candidate, ''), COALESCE(trigger_condition, ''), COALESCE(anti_pattern, ''), COALESCE(repair_action, ''), COALESCE(evidence, '')
        FROM reflections
        """
    )
    conn.execute(
        """
        INSERT INTO episode_fts(rowid, project_id, task, summary, outcome, files_touched, commands_run)
        SELECT id, project_id, COALESCE(task, ''), COALESCE(summary, ''), COALESCE(outcome, ''), COALESCE(files_touched, ''), COALESCE(commands_run, '')
        FROM episodes
        """
    )
    conn.execute(
        """
        INSERT INTO code_file_fts(rowid, project_id, file_path, summary, language, business_summary, business_terms)
        SELECT id, project_id, COALESCE(file_path, ''), COALESCE(summary, ''), COALESCE(language, ''), COALESCE(business_summary, ''), COALESCE(business_terms, '')
        FROM code_files
        """
    )
    conn.execute(
        """
        INSERT INTO code_symbol_fts(rowid, project_id, file_path, symbol, symbol_type, summary, business_summary, business_terms)
        SELECT id, project_id, COALESCE(file_path, ''), COALESCE(symbol, ''), COALESCE(symbol_type, ''), COALESCE(summary, ''), COALESCE(business_summary, ''), COALESCE(business_terms, '')
        FROM code_symbols
        """
    )
    conn.execute(
        """
        INSERT INTO code_log_fts(rowid, project_id, file_path, function, level, logger, message_template, raw_statement, business_summary, business_terms, business_event, trigger_stage, symptom_terms, likely_causes, process_hint, neighbor_terms)
        SELECT id, project_id, COALESCE(file_path, ''), COALESCE(function, ''), COALESCE(level, ''), COALESCE(logger, ''), COALESCE(message_template, ''), COALESCE(raw_statement, ''), COALESCE(business_summary, ''), COALESCE(business_terms, ''), COALESCE(business_event, ''), COALESCE(trigger_stage, ''), COALESCE(symptom_terms, ''), COALESCE(likely_causes, ''), COALESCE(process_hint, ''), COALESCE(neighbor_terms, '')
        FROM code_log_statements
        """
    )


def upsert_project(conn: sqlite3.Connection, project: Project) -> None:
    ts = now_iso()
    conn.execute(
        """
        INSERT INTO projects(project_id, project_path, project_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(project_id) DO UPDATE SET
          project_path=excluded.project_path,
          project_name=excluded.project_name,
          updated_at=excluded.updated_at
        """,
        (project.project_id, str(project.root), project.project_name, ts, ts),
    )
    conn.commit()


def write_config(project: Project) -> None:
    config = {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "project_name": project.project_name,
        "memory_home": str(project.memory_home),
        "memory_dir": str(project.memory_dir),
        "runtime": "tools/agent_memory.py",
        "vault": str(project.vault_dir),
        "version": 1,
        "updated_at": now_iso(),
    }
    (project.memory_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_global_config(project: Project) -> None:
    config_path = project.memory_home / "config.json"
    config = {
        "memory_home": str(project.memory_home),
        "layout": "projects/<project_id>",
        "version": 1,
        "updated_at": now_iso(),
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_initialized(project: Project) -> None:
    ensure_dirs(project)
    with connect(project) as conn:
        create_schema(conn)
        upsert_project(conn, project)
    if not (project.memory_home / "config.json").exists():
        write_global_config(project)
    if not (project.memory_dir / "config.json").exists():
        write_config(project)
