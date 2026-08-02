# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3


MEMORY_EDGE_COUNTER = "memory_edges"


def create_project_counter_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_counters (
          project_id TEXT NOT NULL,
          counter_name TEXT NOT NULL,
          value INTEGER NOT NULL DEFAULT 0,
          updated_at TEXT NOT NULL,
          PRIMARY KEY(project_id, counter_name)
        )
        """
    )
    missing = conn.execute(
        """
        SELECT projects.project_id
        FROM projects
        LEFT JOIN project_counters counters
          ON counters.project_id = projects.project_id
         AND counters.counter_name = ?
        WHERE counters.project_id IS NULL
        """,
        (MEMORY_EDGE_COUNTER,),
    ).fetchall()
    for row in missing:
        rebuild_memory_edge_counter(conn, str(row["project_id"]))


def begin_memory_edge_tracking(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TEMP TABLE IF NOT EXISTS memory_edge_counter_delta (
          project_id TEXT PRIMARY KEY,
          value INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute("DELETE FROM memory_edge_counter_delta")
    conn.execute(
        """
        CREATE TEMP TRIGGER IF NOT EXISTS memory_edge_delta_ai
        AFTER INSERT ON memory_edges BEGIN
          INSERT INTO memory_edge_counter_delta(project_id, value)
          VALUES (new.project_id, 1)
          ON CONFLICT(project_id) DO UPDATE SET value = value + 1;
        END
        """
    )
    conn.execute(
        """
        CREATE TEMP TRIGGER IF NOT EXISTS memory_edge_delta_ad
        AFTER DELETE ON memory_edges BEGIN
          INSERT INTO memory_edge_counter_delta(project_id, value)
          VALUES (old.project_id, -1)
          ON CONFLICT(project_id) DO UPDATE SET value = value - 1;
        END
        """
    )
    conn.execute(
        """
        CREATE TEMP TRIGGER IF NOT EXISTS memory_edge_delta_au
        AFTER UPDATE OF project_id ON memory_edges
        WHEN old.project_id != new.project_id BEGIN
          INSERT INTO memory_edge_counter_delta(project_id, value)
          VALUES (old.project_id, -1)
          ON CONFLICT(project_id) DO UPDATE SET value = value - 1;
          INSERT INTO memory_edge_counter_delta(project_id, value)
          VALUES (new.project_id, 1)
          ON CONFLICT(project_id) DO UPDATE SET value = value + 1;
        END
        """
    )


def finish_memory_edge_tracking(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT project_id, value FROM memory_edge_counter_delta"
    ).fetchall()
    for row in rows:
        adjust_project_counter(
            conn, str(row["project_id"]), MEMORY_EDGE_COUNTER, int(row["value"])
        )
    conn.execute("DROP TRIGGER IF EXISTS memory_edge_delta_ai")
    conn.execute("DROP TRIGGER IF EXISTS memory_edge_delta_ad")
    conn.execute("DROP TRIGGER IF EXISTS memory_edge_delta_au")
    conn.execute("DROP TABLE IF EXISTS memory_edge_counter_delta")


def adjust_project_counter(
    conn: sqlite3.Connection,
    project_id: str,
    counter_name: str,
    delta: int,
) -> None:
    current = project_counter_value(conn, project_id, counter_name)
    set_project_counter(conn, project_id, counter_name, current + delta)


def set_project_counter(
    conn: sqlite3.Connection,
    project_id: str,
    counter_name: str,
    value: int,
) -> None:
    conn.execute(
        """
        INSERT INTO project_counters(project_id, counter_name, value, updated_at)
        VALUES (?, ?, MAX(0, ?), CURRENT_TIMESTAMP)
        ON CONFLICT(project_id, counter_name) DO UPDATE SET
          value = excluded.value,
          updated_at = CURRENT_TIMESTAMP
        """,
        (project_id, counter_name, value),
    )


def rebuild_memory_edge_counter(conn: sqlite3.Connection, project_id: str) -> None:
    count = int(conn.execute(
        "SELECT COUNT(*) AS count FROM memory_edges WHERE project_id = ?",
        (project_id,),
    ).fetchone()["count"])
    set_project_counter(conn, project_id, MEMORY_EDGE_COUNTER, count)


def project_counter_value(
    conn: sqlite3.Connection,
    project_id: str,
    counter_name: str,
) -> int:
    row = conn.execute(
        "SELECT value FROM project_counters "
        "WHERE project_id = ? AND counter_name = ?",
        (project_id, counter_name),
    ).fetchone()
    return int(row["value"] or 0) if row else 0
