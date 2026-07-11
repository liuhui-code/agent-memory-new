# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3


def create_incident_trace_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS incident_traces (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          trace_key TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'open',
          symptom TEXT NOT NULL,
          goal TEXT,
          arkts_scene TEXT NOT NULL DEFAULT 'unknown',
          time_window TEXT,
          entry_log_text TEXT,
          normalized_error TEXT,
          dominant_log_events TEXT,
          diagnosis_summary TEXT,
          suspected_chain TEXT,
          root_cause_hypothesis TEXT,
          resolution TEXT,
          confidence REAL DEFAULT 0.7,
          source TEXT DEFAULT 'incident-trace',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS incident_trace_links (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          trace_id INTEGER NOT NULL,
          target_type TEXT NOT NULL,
          target_id INTEGER,
          target_key TEXT,
          relation TEXT NOT NULL,
          score REAL DEFAULT 0.0,
          evidence TEXT,
          created_at TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_incident_traces_project_key
        ON incident_traces(project_id, trace_key);

        CREATE INDEX IF NOT EXISTS idx_incident_traces_project_status
        ON incident_traces(project_id, status, updated_at);

        CREATE INDEX IF NOT EXISTS idx_incident_traces_project_scene
        ON incident_traces(project_id, arkts_scene, updated_at);

        CREATE INDEX IF NOT EXISTS idx_incident_trace_links_trace
        ON incident_trace_links(project_id, trace_id);

        CREATE INDEX IF NOT EXISTS idx_incident_trace_links_target
        ON incident_trace_links(project_id, target_type, target_id);

        CREATE VIRTUAL TABLE IF NOT EXISTS incident_trace_fts USING fts5(
          project_id UNINDEXED,
          symptom,
          goal,
          arkts_scene,
          entry_log_text,
          normalized_error,
          dominant_log_events,
          diagnosis_summary,
          suspected_chain,
          root_cause_hypothesis,
          resolution
        );

        CREATE TRIGGER IF NOT EXISTS incident_trace_fts_ai AFTER INSERT ON incident_traces BEGIN
          INSERT INTO incident_trace_fts(
            rowid, project_id, symptom, goal, arkts_scene, entry_log_text,
            normalized_error, dominant_log_events, diagnosis_summary,
            suspected_chain, root_cause_hypothesis, resolution
          )
          VALUES (
            new.id, new.project_id, new.symptom, new.goal, new.arkts_scene,
            new.entry_log_text, new.normalized_error, new.dominant_log_events,
            new.diagnosis_summary, new.suspected_chain,
            new.root_cause_hypothesis, new.resolution
          );
        END;

        CREATE TRIGGER IF NOT EXISTS incident_trace_fts_ad AFTER DELETE ON incident_traces BEGIN
          DELETE FROM incident_trace_fts WHERE rowid = old.id;
        END;

        CREATE TRIGGER IF NOT EXISTS incident_trace_fts_au AFTER UPDATE ON incident_traces BEGIN
          DELETE FROM incident_trace_fts WHERE rowid = old.id;
          INSERT INTO incident_trace_fts(
            rowid, project_id, symptom, goal, arkts_scene, entry_log_text,
            normalized_error, dominant_log_events, diagnosis_summary,
            suspected_chain, root_cause_hypothesis, resolution
          )
          VALUES (
            new.id, new.project_id, new.symptom, new.goal, new.arkts_scene,
            new.entry_log_text, new.normalized_error, new.dominant_log_events,
            new.diagnosis_summary, new.suspected_chain,
            new.root_cause_hypothesis, new.resolution
          );
        END;
        """
    )

