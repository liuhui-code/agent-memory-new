# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.code_wiki_edges import (
    load_rebuild_symbols,
    load_scoped_rows,
    referenced_symbol_names,
)
from tools.agent_memory_runtime.code_wiki_indexing import write_wiki_index
from tools.agent_memory_runtime.storage import (
    connect,
    ensure_initialized,
    now_iso,
    resolve_project,
)


class ScopeBoundedMaintenanceTests(unittest.TestCase):
    def test_project_edge_counter_tracks_mutations_with_primary_key_lookup(self) -> None:
        from tools.agent_memory_runtime.storage_project_counters import (
            MEMORY_EDGE_COUNTER,
            begin_memory_edge_tracking,
            finish_memory_edge_tracking,
            project_counter_value,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            project = resolve_project(str(root), str(Path(directory) / "memory"))
            ensure_initialized(project)
            with connect(project) as conn:
                begin_memory_edge_tracking(conn)
                insert_edge(conn, "alpha", 1)
                insert_edge(conn, "alpha", 2)
                insert_edge(conn, "beta", 3)
                finish_memory_edge_tracking(conn)
                self.assertEqual(2, project_counter_value(
                    conn, "alpha", MEMORY_EDGE_COUNTER
                ))
                begin_memory_edge_tracking(conn)
                conn.execute(
                    "DELETE FROM memory_edges WHERE project_id = ? AND source_id = ?",
                    ("alpha", 1),
                )
                conn.execute(
                    "UPDATE memory_edges SET project_id = ? "
                    "WHERE project_id = ? AND source_id = ?",
                    ("beta", "alpha", 2),
                )
                finish_memory_edge_tracking(conn)
                self.assertEqual(0, project_counter_value(
                    conn, "alpha", MEMORY_EDGE_COUNTER
                ))
                self.assertEqual(2, project_counter_value(
                    conn, "beta", MEMORY_EDGE_COUNTER
                ))
                plan = [
                    str(row["detail"])
                    for row in conn.execute(
                        "EXPLAIN QUERY PLAN SELECT value FROM project_counters "
                        "WHERE project_id = ? AND counter_name = ?",
                        ("beta", MEMORY_EDGE_COUNTER),
                    )
                ]
        self.assertTrue(any("SEARCH project_counters" in item for item in plan), plan)
        self.assertFalse(any("memory_edges" in item for item in plan), plan)

    def test_counter_schema_backfills_existing_edges_once(self) -> None:
        from tools.agent_memory_runtime.storage_project_counters import (
            MEMORY_EDGE_COUNTER,
            create_project_counter_schema,
            project_counter_value,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            project = resolve_project(str(root), str(Path(directory) / "memory"))
            ensure_initialized(project)
            with connect(project) as conn:
                conn.execute("DELETE FROM project_counters")
                insert_edge(conn, project.project_id, 1)
                insert_edge(conn, project.project_id, 2)
                create_project_counter_schema(conn)
                self.assertEqual(2, project_counter_value(
                    conn, project.project_id, MEMORY_EDGE_COUNTER
                ))

    def test_graph_candidates_ignore_declarations_and_ambiguous_global_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            methods = "\n".join(
                f"  method{index:04d}(): void {{}}" for index in range(1, 101)
            )
            (root / "Changed.ets").write_text(
                "import { ExternalService } from './ExternalService'\n"
                "export class Changed {\n"
                f"{methods}\n"
                "  run(service: ExternalService): void {\n"
                "    ExternalService.execute()\n"
                "    SharedService.execute()\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            project = resolve_project(str(root), str(Path(directory) / "memory"))
            ensure_initialized(project)
            with connect(project) as conn:
                seed_graph_symbols(conn, project.project_id)
                scoped = load_scoped_rows(
                    conn,
                    "code_files",
                    "id, file_path, language",
                    project.project_id,
                    {"Changed.ets"},
                )
                names = referenced_symbol_names(project, scoped)
                symbols = load_rebuild_symbols(
                    conn, project, scoped, {"Changed.ets"}
                )

        self.assertIn("ExternalService", names)
        self.assertIn("SharedService", names)
        self.assertNotIn("method0001", names)
        external = [
            row for row in symbols if str(row["file_path"]) != "Changed.ets"
        ]
        self.assertEqual(
            [("ExternalService.ets", "ExternalService", "class")],
            [
                (str(row["file_path"]), str(row["symbol"]), str(row["symbol_type"]))
                for row in external
            ],
        )

    def test_production_refresh_reports_exact_project_edge_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            source = root / "Service.ets"
            source.write_text(
                "export class Service { run(): void { console.info('first') } }\n",
                encoding="utf-8",
            )
            project = resolve_project(str(root), str(Path(directory) / "memory"))
            ensure_initialized(project)

            initial = write_wiki_index(project, [source], replace=True)
            source.write_text(
                "export class Service { stop(): void { console.info('second') } }\n",
                encoding="utf-8",
            )
            refreshed = write_wiki_index(project, [source])
            with connect(project) as conn:
                actual = int(
                    conn.execute(
                        "SELECT COUNT(*) FROM memory_edges WHERE project_id = ?",
                        (project.project_id,),
                    ).fetchone()[0]
                )

        self.assertEqual("project-counter/v1", initial["memory_edges_total_provider"])
        self.assertEqual(actual, refreshed["memory_edges_total"])


def insert_edge(conn: object, project_id: str, source_id: int) -> None:
    conn.execute(
        "INSERT INTO memory_edges("
        "project_id, source_type, source_id, relation, target_type, target_id, created_at"
        ") VALUES (?, 'code_file', ?, 'contains', 'code_symbol', ?, ?)",
        (project_id, source_id, source_id, now_iso()),
    )


def seed_graph_symbols(conn: object, project_id: str) -> None:
    ts = now_iso()
    conn.execute(
        "INSERT INTO code_files(project_id, file_path, summary, language, updated_at) "
        "VALUES (?, 'Changed.ets', 'changed', 'ArkTS', ?)",
        (project_id, ts),
    )
    local_rows = [
        (project_id, "Changed.ets", f"method{index:04d}", "function", "local", ts)
        for index in range(1, 101)
    ]
    duplicate_rows = [
        (
            project_id,
            f"noise/Noise{copy:02d}_{index:04d}.ets",
            f"method{index:04d}",
            "function",
            "duplicate",
            ts,
        )
        for copy in range(20)
        for index in range(1, 101)
    ]
    reference_rows = [
        (project_id, "ExternalService.ets", "ExternalService", "class", "unique", ts),
        (project_id, "SharedOne.ets", "SharedService", "class", "ambiguous", ts),
        (project_id, "SharedTwo.ets", "SharedService", "class", "ambiguous", ts),
    ]
    conn.executemany(
        "INSERT INTO code_symbols("
        "project_id, file_path, symbol, symbol_type, summary, updated_at"
        ") VALUES (?, ?, ?, ?, ?, ?)",
        [*local_rows, *duplicate_rows, *reference_rows],
    )


if __name__ == "__main__":
    unittest.main()
