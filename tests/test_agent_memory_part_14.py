# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart14Tests(AgentMemoryTestBase):
    def test_search_returns_batched_aggregate_metadata_and_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            for index in range(6):
                self.run_memory(
                    project,
                    "update",
                    "--type",
                    "semantic",
                    "--fact",
                    f"profile timeout investigation note {index}",
                    "--source",
                    "test",
                    "--confidence",
                    "1.0",
                )

            first = json.loads(
                self.run_memory(
                    project,
                    "search",
                    "--query",
                    "profile timeout",
                    "--per-type-limit",
                    "5",
                    "--aggregate-limit",
                    "3",
                    "--json",
                ).stdout
            )
            second = json.loads(
                self.run_memory(
                    project,
                    "search",
                    "--query",
                    "profile timeout",
                    "--per-type-limit",
                    "5",
                    "--aggregate-limit",
                    "3",
                    "--cursor",
                    "3",
                    "--json",
                ).stdout
            )

            self.assertTrue(first["truncated"])
            self.assertEqual(first["next_cursor"], 3)
            self.assertEqual(first["total_candidates_by_type"]["semantic_facts"], 6)
            self.assertEqual(first["returned_counts_by_type"]["semantic_facts"], 3)
            self.assertEqual(len(first["semantic_facts"]), 3)
            self.assertIsNone(first["followup_focus"])
            self.assertIn("profile", first["suggested_followup_terms"])
            self.assertEqual(second["returned_counts_by_type"]["semantic_facts"], 3)
            self.assertIsNone(second["next_cursor"])
            self.assertEqual(len(second["semantic_facts"]), 3)

    def test_context_limits_network_edges_and_reports_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            db_path = self.project_memory_dir(project) / "memory.db"
            with sqlite3.connect(db_path) as conn:
                project_id = conn.execute("SELECT project_id FROM projects").fetchone()[0]
                for index in range(25):
                    conn.execute(
                        """
                        INSERT INTO memory_edges(
                          project_id, source_type, source_id, relation, target_type,
                          target_id, evidence, confidence, created_at
                        )
                        VALUES (?, 'code_log_statement', 1, 'calls', 'code_symbol', ?, 'synthetic', 0.9, '2026-01-01T00:00:00+00:00')
                        """,
                        (project_id, 1000 + index),
                    )

            result = self.run_memory(project, "context", "--query", "retrying job", "--json")
            payload = json.loads(result.stdout)

            self.assertEqual(payload["network_limits"]["max_depth"], 1)
            self.assertEqual(payload["network_limits"]["edge_limit"], 10)
            self.assertNotIn("calls", payload["network_limits"]["allowed_relations"])
            self.assertLessEqual(len(payload["edge_matches"]), 10)
            self.assertTrue(all(edge["relation"] != "calls" for edge in payload["edge_matches"]))

    def test_collect_related_edges_handles_more_than_thousand_targets(self) -> None:
        from tools.agent_memory_runtime.query import collect_related_edges
        from tools.agent_memory_runtime.storage import connect, ensure_initialized, resolve_project

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            project = resolve_project(str(project_path), str(self.memory_home(project_path)))
            ensure_initialized(project)

            with connect(project) as conn:
                for index in range(1200):
                    conn.execute(
                        """
                        INSERT INTO memory_edges(
                          project_id, source_type, source_id, relation, target_type,
                          target_id, evidence, confidence, created_at
                        )
                        VALUES (?, 'code_symbol', ?, 'emits_log', 'code_log_statement', ?, 'synthetic', 0.9, '2026-01-01T00:00:00+00:00')
                        """,
                        (project.project_id, index + 1, index + 1),
                    )
                conn.commit()

            targets = {
                "code_file": set(),
                "code_symbol": set(range(1, 1201)),
                "code_log_statement": set(),
            }
            edges = collect_related_edges(project, targets)

            self.assertLessEqual(len(edges), 10)

    def test_context_returns_raw_edges_and_agent_query_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            result = self.run_memory(project, "context", "--query", "retrying job", "--json")
            payload = json.loads(result.stdout)
            edge = next(
                item for item in payload["edge_matches"]
                if item["relation"] == "emits_log"
            )

            self.assertNotIn("evidence_chains", payload)
            self.assertEqual(edge["target_type"], "code_log_statement")
            self.assertIn("worker.py", edge["evidence"])
            self.assertIn("retrying", payload["query_handoff"]["log_keywords"])
            self.assertTrue(payload["query_handoff"]["log_anchors"])
            self.assertFalse(payload["query_handoff"]["role_boundary"]["runtime_builds_causal_chains"])

    def test_search_limits_large_result_sets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            for index in range(30):
                self.run_memory(
                    project,
                    "update",
                    "--type",
                    "semantic",
                    "--fact",
                    f"Route failure fact {index}",
                    "--source",
                    "test",
                )

            result = self.run_memory(project, "search", "--query", "route failure", "--json")
            payload = json.loads(result.stdout)

            self.assertLessEqual(len(payload["semantic_facts"]), 20)
            self.assertIn("result_limits", payload)
            self.assertEqual(payload["result_limits"]["semantic_facts"], 20)

    def test_context_json_stdout_preserves_chinese_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "页面跳转后白屏需要先查路由",
                "--source",
                "test",
            )

            result = self.run_memory(project, "context", "--query", "页面跳转后白屏", "--json")

            self.assertIn("页面跳转后白屏", result.stdout)
            self.assertNotIn("\\u9875", result.stdout)

    def test_wiki_search_returns_code_log_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            result = self.run_memory(project, "wiki-search", "--query", "retrying job", "--json")
            payload = json.loads(result.stdout)

            self.assertEqual(payload[0]["kind"], "log_statement")
            self.assertEqual(payload[0]["function"], "process_job")

    def test_memory_edges_connect_files_symbols_and_log_statements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            edges = self.list_records(project, "memory-edge")
            relations = {(edge["source_type"], edge["relation"], edge["target_type"]) for edge in edges}

            self.assertIn(("code_file", "contains", "code_symbol"), relations)
            self.assertIn(("code_file", "contains", "code_log_statement"), relations)
            self.assertIn(("code_symbol", "emits_log", "code_log_statement"), relations)

    def test_learn_path_replace_clears_old_code_log_statements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "a").mkdir()
            (project / "b").mkdir()
            (project / "a" / "one.py").write_text(
                "def one():\n    print('old log')\n",
                encoding="utf-8",
            )
            (project / "b" / "two.py").write_text(
                "def two():\n    print('new log')\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "a")
            self.run_memory(project, "learn-path", "--path", "b", "--replace")

            logs = self.list_records(project, "code-log")
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["file_path"], "b/two.py")
            self.assertIn("new log", logs[0]["message_template"])

    def test_vault_export_writes_code_log_network_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            self.run_memory(project, "vault-export")

            logs = self.project_memory_dir(project) / "vault" / "Codebase Wiki" / "log-statements.md"
            edges = self.project_memory_dir(project) / "vault" / "Codebase Wiki" / "memory-edges.md"
            self.assertTrue(logs.exists())
            self.assertTrue(edges.exists())
            self.assertIn("retrying job %s", logs.read_text(encoding="utf-8"))
            self.assertIn("emits_log", edges.read_text(encoding="utf-8"))
