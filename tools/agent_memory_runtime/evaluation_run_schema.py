# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3


def create_evaluation_run_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS evaluation_runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id TEXT NOT NULL,
          run_kind TEXT NOT NULL CHECK(run_kind IN ('context_capability', 'agent_benchmark')),
          seal_digest TEXT NOT NULL,
          case_file TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
          gate_status TEXT,
          result_digest TEXT,
          error_class TEXT,
          started_at TEXT NOT NULL,
          finished_at TEXT,
          UNIQUE(project_id, run_kind, seal_digest)
        );

        CREATE INDEX IF NOT EXISTS idx_evaluation_runs_project_status
        ON evaluation_runs(project_id, status, started_at);
        """
    )
