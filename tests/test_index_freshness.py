# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.index_freshness import filter_fresh_path_context
from tools.agent_memory_runtime.storage import resolve_project


class IndexFreshnessTests(AgentMemoryTestBase):
    def write_source(self, project: Path, message: str) -> Path:
        source = project / "pages" / "SessionManager.ets"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            "export class SessionManager {\n"
            "  release(): void {\n"
            f"    console.error('{message}')\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        return source

    def learn(self, project: Path) -> None:
        self.run_memory(project, "learn-path", "--path", "pages", "--json")

    def database(self, project: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(self.project_memory_dir(project) / "memory.db")
        conn.row_factory = sqlite3.Row
        return conn

    def context(self, project: Path, query: str, compact: bool = False) -> dict:
        args = ["context", "--query", query]
        if compact:
            args.append("--compact")
        args.append("--json")
        return json.loads(self.run_memory(project, *args).stdout)

    def test_learning_stamps_derived_rows_with_digest_and_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            source = self.write_source(project, "session release failed")
            self.learn(project)
            expected_digest = hashlib.sha256(source.read_bytes()).hexdigest()
            with self.database(project) as conn:
                state = dict(conn.execute(
                    "SELECT * FROM code_index_state WHERE project_id = ?",
                    (self.project_id(project),),
                ).fetchone())
                rows = {
                    table: dict(conn.execute(
                        f"SELECT source_digest, index_generation FROM {table} "
                        "WHERE project_id = ? LIMIT 1",
                        (self.project_id(project),),
                    ).fetchone())
                    for table in ("code_files", "code_symbols", "code_log_statements")
                }

        self.assertEqual("active", state["status"])
        self.assertGreaterEqual(state["generation"], 1)
        for row in rows.values():
            self.assertEqual(expected_digest, row["source_digest"])
            self.assertEqual(state["generation"], row["index_generation"])

    def test_changed_candidate_is_blocked_before_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write_source(project, "session release failed")
            self.learn(project)
            self.write_source(project, "session release completed")

            payload = self.context(project, "session release failed")
            compact = self.context(project, "session release failed", compact=True)

        freshness = payload["source_freshness"]
        self.assertEqual("partial_current", freshness["status"])
        self.assertEqual(["pages/SessionManager.ets"], freshness["stale_paths"])
        self.assertGreater(freshness["blocked_rows"], 0)
        self.assertFalse(any(
            row.get("file_path") == "pages/SessionManager.ets"
            for row in payload["wiki_matches"] + payload["code_log_matches"]
        ))
        self.assertEqual("partial_current", compact["source_freshness"]["status"])
        self.assertEqual(
            {"status", "generation", "blocked_rows", "stale_paths"},
            set(compact["source_freshness"]),
        )
        self.assertFalse(any(
            row.get("file_path") == "pages/SessionManager.ets"
            for row in compact["query_handoff"]["code_anchors"]
        ))
        self.assertEqual(
            [],
            compact["query_handoff"]["path_context"]["path_candidates"],
        )

    def test_changed_only_refresh_activates_a_new_current_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write_source(project, "session release failed")
            self.learn(project)
            before = self.context(project, "session release failed")["source_freshness"]
            self.write_source(project, "session release completed")

            self.run_memory(
                project,
                "maintain-refresh-scope",
                "--changed-only",
                "--json",
            )
            after = self.context(project, "session release completed")["source_freshness"]

        self.assertEqual("current", before["status"])
        self.assertEqual("current", after["status"])
        self.assertGreater(after["generation"], before["generation"])
        self.assertEqual([], after["stale_paths"])

    def test_deleted_candidate_is_blocked_before_scope_maintenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            source = self.write_source(project, "session release failed")
            self.learn(project)
            source.unlink()

            payload = self.context(project, "session release failed")

        self.assertEqual("partial_current", payload["source_freshness"]["status"])
        self.assertEqual(["pages/SessionManager.ets"], payload["source_freshness"]["missing_paths"])
        self.assertEqual([], payload["code_log_matches"])

    def test_path_only_candidate_is_validated_before_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self.write_source(project_root, "session release failed")
            self.learn(project_root)
            self.write_source(project_root, "session release completed")
            project = resolve_project(
                str(project_root), str(self.memory_home(project_root))
            )
            path_context = {
                "path_candidates": [{
                    "nodes": [{"file_path": "pages/SessionManager.ets"}],
                }],
                "gaps": {},
            }

            filtered, freshness = filter_fresh_path_context(
                project, path_context, {}
            )

        self.assertEqual([], filtered["path_candidates"])
        self.assertEqual("partial_current", freshness["status"])
        self.assertEqual(
            ["pages/SessionManager.ets"],
            filtered["gaps"]["stale_source_paths"],
        )

    def test_legacy_rows_are_reported_unverified_without_false_current_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write_source(project, "session release failed")
            self.learn(project)
            with self.database(project) as conn:
                for table in ("code_files", "code_symbols", "code_log_statements"):
                    conn.execute(
                        f"UPDATE {table} SET source_digest = NULL WHERE project_id = ?",
                        (self.project_id(project),),
                    )
                conn.commit()

            payload = self.context(project, "session release failed")

        self.assertEqual("unverified", payload["source_freshness"]["status"])
        self.assertEqual(["pages/SessionManager.ets"], payload["source_freshness"]["unverified_paths"])
        self.assertTrue(payload["code_log_matches"])

    def test_external_source_scope_validates_against_source_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "archive"
            source = root / "external"
            archive.mkdir()
            external_file = self.write_source(source, "external session release")

            self.run_memory(
                archive,
                "learn-path",
                "--source",
                str(source),
                "--path",
                "pages",
                "--json",
            )
            current = self.context(archive, "external session release")
            external_file.write_text(
                "export class SessionManager {}\n",
                encoding="utf-8",
            )
            changed = self.context(archive, "external session release")

        self.assertEqual("current", current["source_freshness"]["status"])
        self.assertTrue(current["code_log_matches"])
        self.assertEqual("partial_current", changed["source_freshness"]["status"])
        self.assertEqual(["pages/SessionManager.ets"], changed["source_freshness"]["stale_paths"])

    def test_health_exposes_active_generation_and_digest_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write_source(project, "session release failed")
            self.learn(project)

            health = json.loads(
                self.run_memory(project, "maintain-health", "--json").stdout
            )

        self.assertEqual("active", health["code_index"]["status"])
        self.assertGreaterEqual(health["code_index"]["generation"], 1)
        self.assertEqual(0, health["code_index"]["unverified_rows"])
        self.assertGreater(health["code_index"]["total_rows"], 0)
        self.assertEqual(
            health["code_index"]["total_rows"],
            health["code_index"]["verified_rows"],
        )
        self.assertEqual(1.0, health["code_index"]["digest_coverage"])
        self.assertEqual(1, health["code_index"]["indexed_file_count"])


if __name__ == "__main__":
    import unittest

    unittest.main()
