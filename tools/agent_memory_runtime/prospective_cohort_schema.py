# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3


def create_prospective_cohort_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS prospective_cohorts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          cohort_id TEXT NOT NULL,
          protocol_json TEXT NOT NULL,
          protocol_digest TEXT NOT NULL,
          task_type TEXT NOT NULL CHECK(task_type = 'diagnosis'),
          target_presented_tasks INTEGER NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('registered', 'running', 'completed')),
          presented_count INTEGER NOT NULL DEFAULT 0,
          eligible_count INTEGER NOT NULL DEFAULT 0,
          excluded_count INTEGER NOT NULL DEFAULT 0,
          chain_head_digest TEXT NOT NULL,
          registered_at TEXT NOT NULL,
          started_at TEXT,
          finalized_at TEXT,
          report_json TEXT,
          report_digest TEXT,
          UNIQUE(project_id, cohort_id)
        );

        CREATE TABLE IF NOT EXISTS prospective_cohort_tasks (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          cohort_pk INTEGER NOT NULL,
          sequence_no INTEGER NOT NULL,
          task_id TEXT NOT NULL,
          task_digest TEXT NOT NULL,
          eligibility TEXT NOT NULL CHECK(eligibility IN ('eligible', 'excluded')),
          exclusion_reason TEXT,
          opportunity TEXT NOT NULL CHECK(opportunity IN ('present', 'absent', 'unknown')),
          evidence_refs_json TEXT NOT NULL,
          memory_available_at TEXT NOT NULL,
          memory_manifest_json TEXT NOT NULL,
          memory_manifest_digest TEXT NOT NULL,
          source_snapshot_json TEXT NOT NULL,
          paired_replay_json TEXT NOT NULL DEFAULT '{}',
          replay_eligible INTEGER NOT NULL DEFAULT 0,
          previous_entry_digest TEXT NOT NULL,
          entry_digest TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('active', 'completed', 'excluded')),
          usage_sample_id TEXT,
          outcome TEXT,
          verification TEXT,
          usage_metrics_json TEXT,
          benchmark_metrics_json TEXT,
          result_digest TEXT,
          enrolled_at TEXT NOT NULL,
          completed_at TEXT,
          UNIQUE(cohort_pk, sequence_no),
          UNIQUE(cohort_pk, task_id)
        );

        CREATE INDEX IF NOT EXISTS idx_prospective_cohorts_project_status
        ON prospective_cohorts(project_id, status, registered_at);

        CREATE INDEX IF NOT EXISTS idx_prospective_cohort_tasks_status
        ON prospective_cohort_tasks(cohort_pk, status, sequence_no);
        """
    )
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(prospective_cohort_tasks)")}
    if "paired_replay_json" not in columns:
        conn.execute("ALTER TABLE prospective_cohort_tasks ADD COLUMN paired_replay_json TEXT NOT NULL DEFAULT '{}'")
