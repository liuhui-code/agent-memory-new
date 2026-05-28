import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"


class AgentMemoryRuntimeTests(unittest.TestCase):
    def run_memory(self, project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNTIME), *args, "--project", str(project)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

    def list_code_files(self, project: Path) -> set[str]:
        result = self.run_memory(
            project,
            "list",
            "--type",
            "code-file",
            "--json",
        )
        return {row["file_path"] for row in json.loads(result.stdout)}

    def list_records(self, project: Path, kind: str) -> list[dict]:
        result = self.run_memory(
            project,
            "list",
            "--type",
            kind,
            "--json",
        )
        return json.loads(result.stdout)

    def miss_list(self, project: Path) -> list[dict]:
        result = self.run_memory(project, "miss-list", "--json")
        return json.loads(result.stdout)

    def test_learn_path_merges_index_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "a").mkdir()
            (project / "b").mkdir()
            (project / "a" / "one.py").write_text("def one():\n    return 1\n", encoding="utf-8")
            (project / "b" / "two.py").write_text("def two():\n    return 2\n", encoding="utf-8")

            self.run_memory(project, "learn-path", "--path", "a")
            self.run_memory(project, "learn-path", "--path", "b")

            self.assertEqual(self.list_code_files(project), {"a/one.py", "b/two.py"})

    def test_learn_path_replace_keeps_only_latest_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "a").mkdir()
            (project / "b").mkdir()
            (project / "a" / "one.py").write_text("def one():\n    return 1\n", encoding="utf-8")
            (project / "b" / "two.py").write_text("def two():\n    return 2\n", encoding="utf-8")

            self.run_memory(project, "learn-path", "--path", "a")
            self.run_memory(project, "learn-path", "--path", "b", "--replace")

            self.assertEqual(self.list_code_files(project), {"b/two.py"})

    def test_maintain_status_marks_semantic_stale_and_context_excludes_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "SQLite source of truth",
                "--source",
                "test",
                "--confidence",
                "1.0",
            )

            self.run_memory(
                project,
                "maintain-status",
                "--type",
                "semantic",
                "--id",
                "1",
                "--status",
                "stale",
                "--reason",
                "test stale",
            )
            context = self.run_memory(project, "context", "--query", "SQLite", "--json")

            facts = self.list_records(project, "semantic")
            self.assertEqual(facts[0]["status"], "stale")
            self.assertEqual(json.loads(context.stdout)["semantic_facts"], [])

    def test_maintain_promote_episode_to_semantic_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "update",
                "--type",
                "episode",
                "--task",
                "review task",
                "--summary",
                "learned durable fact",
            )

            result = self.run_memory(
                project,
                "maintain-promote",
                "--episode-id",
                "1",
                "--fact",
                "Durable promoted fact",
                "--json",
            )

            payload = json.loads(result.stdout)
            facts = self.list_records(project, "semantic")
            episodes = self.list_records(project, "episode")
            self.assertEqual(payload["semantic_fact_id"], 1)
            self.assertEqual(facts[0]["fact"], "Durable promoted fact")
            self.assertEqual(episodes[0]["derived_facts"], "[1]")

    def test_maintain_merge_marks_old_semantic_records_merged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            for fact in ("Skill calls runtime script", "Skills call runtime script"):
                self.run_memory(
                    project,
                    "update",
                    "--type",
                    "semantic",
                    "--fact",
                    fact,
                    "--source",
                    "test",
                )

            result = self.run_memory(
                project,
                "maintain-merge",
                "--type",
                "semantic",
                "--ids",
                "1,2",
                "--fact",
                "Skills call the runtime script.",
                "--json",
            )

            payload = json.loads(result.stdout)
            facts = sorted(self.list_records(project, "semantic"), key=lambda row: row["id"])
            self.assertEqual(payload["merged_into_id"], 3)
            self.assertEqual([facts[0]["status"], facts[1]["status"], facts[2]["status"]], ["merged", "merged", "active"])
            self.assertEqual([facts[0]["merged_into_id"], facts[1]["merged_into_id"]], [3, 3])

    def test_maintain_plan_outputs_confirmable_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            for fact in ("Runtime uses SQLite", "Runtime uses SQLite"):
                self.run_memory(
                    project,
                    "update",
                    "--type",
                    "semantic",
                    "--fact",
                    fact,
                    "--source",
                    "test",
                )
            self.run_memory(
                project,
                "update",
                "--type",
                "episode",
                "--task",
                "planned review",
                "--summary",
                "may contain durable knowledge",
            )
            self.run_memory(
                project,
                "maintain-status",
                "--type",
                "semantic",
                "--id",
                "2",
                "--status",
                "stale",
                "--reason",
                "test stale",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            payload = json.loads(result.stdout)
            actions = payload["actions"]

            self.assertEqual(payload["summary"]["stale"], 1)
            self.assertTrue(all(action["requires_confirmation"] for action in actions))
            self.assertIn("archive", {action["action"] for action in actions})
            self.assertIn("promote_or_archive", {action["action"] for action in actions})
            self.assertTrue(any(action["type"] == "semantic" and action["id"] == 2 for action in actions))

    def test_reflect_writes_actionable_quality_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(
                project,
                "reflect",
                "--task",
                "change runtime command",
                "--lesson",
                "Command behavior changes need tests and docs.",
                "--future-rule",
                "Update parser, tests, skill docs, usage guide, and gitlog together.",
                "--trigger-condition",
                "When changing runtime CLI behavior",
                "--anti-pattern",
                "Only update parser implementation",
                "--repair-action",
                "Update tests, docs, and skill instructions in the same change",
                "--applies-to",
                "runtime command behavior changes",
                "--does-not-apply-to",
                "docs-only edits",
            )

            reflection = self.list_records(project, "reflection")[0]
            self.assertEqual(reflection["trigger_condition"], "When changing runtime CLI behavior")
            self.assertEqual(reflection["anti_pattern"], "Only update parser implementation")
            self.assertEqual(reflection["repair_action"], "Update tests, docs, and skill instructions in the same change")
            self.assertEqual(reflection["applies_to"], "runtime command behavior changes")
            self.assertEqual(reflection["does_not_apply_to"], "docs-only edits")

    def test_reflect_updates_used_reflection_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "old lesson",
                "--lesson",
                "Use maintain-plan before memory mutations.",
            )

            self.run_memory(
                project,
                "reflect",
                "--task",
                "new task",
                "--lesson",
                "The old lesson helped this task.",
                "--used-reflection-ids",
                "1",
                "--reflection-outcome",
                "helped",
            )

            old_reflection = sorted(self.list_records(project, "reflection"), key=lambda row: row["id"])[0]
            self.assertEqual(old_reflection["applied_count"], 1)
            self.assertEqual(old_reflection["last_outcome"], "helped")
            self.assertIsNotNone(old_reflection["last_applied_at"])

    def test_reflect_review_reports_missing_actionability(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "thin reflection",
                "--lesson",
                "Be careful.",
            )

            result = self.run_memory(project, "reflect-review", "--json")
            payload = json.loads(result.stdout)
            item = payload["reflections"][0]

            self.assertEqual(item["id"], 1)
            self.assertIn("missing_trigger_condition", item["issues"])
            self.assertIn("missing_repair_action", item["issues"])
            self.assertEqual(item["suggested_action"], "rewrite")

    def test_maintain_plan_includes_reflection_quality_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "thin reflection",
                "--lesson",
                "Be careful.",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            self.assertTrue(any(action["action"] == "rewrite_reflection" and action["id"] == 1 for action in actions))

    def test_maintain_plan_marks_misleading_reflection_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "bad lesson",
                "--lesson",
                "Use stale data first.",
            )
            self.run_memory(
                project,
                "reflect",
                "--task",
                "later task",
                "--lesson",
                "That lesson misled the task.",
                "--used-reflection-ids",
                "1",
                "--reflection-outcome",
                "misleading",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            self.assertTrue(any(action["action"] == "mark_stale" and action["id"] == 1 for action in actions))

    def test_maintain_promote_reflection_to_semantic_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "durable workflow",
                "--lesson",
                "Runtime changes need parser tests and skill docs.",
            )

            result = self.run_memory(
                project,
                "maintain-promote",
                "--reflection-id",
                "1",
                "--fact",
                "Runtime changes must update parser tests and skill docs.",
                "--json",
            )

            payload = json.loads(result.stdout)
            facts = self.list_records(project, "semantic")
            reflection = self.list_records(project, "reflection")[0]
            self.assertEqual(payload["semantic_fact_id"], 1)
            self.assertEqual(facts[0]["source"], "reflection:1")
            self.assertIsNotNone(reflection["reviewed_at"])

    def test_vault_export_writes_reflection_quality_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "thin reflection",
                "--lesson",
                "Be careful.",
            )

            self.run_memory(project, "vault-export")

            dashboard = project / ".agent-memory" / "vault" / "Governance" / "Reflection Quality.md"
            self.assertTrue(dashboard.exists())
            self.assertIn("missing_trigger_condition", dashboard.read_text(encoding="utf-8"))

    def test_context_records_query_miss_when_all_result_sets_are_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(project, "context", "--query", "no-such-memory-token", "--json")

            misses = self.miss_list(project)
            self.assertEqual(len(misses), 1)
            self.assertEqual(misses[0]["query"], "no-such-memory-token")
            self.assertEqual(misses[0]["source"], "context")
            self.assertEqual(misses[0]["status"], "open")
            self.assertEqual(json.loads(misses[0]["result_counts"])["semantic_facts"], 0)

    def test_context_does_not_record_query_miss_when_memory_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "SQLite remains the source of truth.",
                "--source",
                "test",
            )

            self.run_memory(project, "context", "--query", "SQLite", "--json")

            self.assertEqual(self.miss_list(project), [])

    def test_wiki_search_records_query_miss_when_no_wiki_match_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(project, "wiki-search", "--query", "missing-wiki-token", "--json")

            misses = self.miss_list(project)
            self.assertEqual(len(misses), 1)
            self.assertEqual(misses[0]["source"], "wiki-search")

    def test_miss_status_updates_query_miss_review_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "context", "--query", "unanswered-question", "--json")

            self.run_memory(
                project,
                "miss-status",
                "--id",
                "1",
                "--status",
                "resolved",
                "--resolution",
                "added semantic fact",
            )

            miss = self.miss_list(project)[0]
            self.assertEqual(miss["status"], "resolved")
            self.assertEqual(miss["resolution"], "added semantic fact")
            self.assertIsNotNone(miss["reviewed_at"])

    def test_maintain_plan_includes_open_query_miss_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "context", "--query", "unanswered-question", "--json")

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            self.assertTrue(any(action["action"] == "review_query_miss" and action["id"] == 1 for action in actions))

    def test_vault_export_writes_query_misses_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "context", "--query", "unanswered-question", "--json")

            self.run_memory(project, "vault-export")

            dashboard = project / ".agent-memory" / "vault" / "Governance" / "Query Misses.md"
            self.assertTrue(dashboard.exists())
            self.assertIn("unanswered-question", dashboard.read_text(encoding="utf-8"))

    def test_learn_path_extracts_python_print_and_logger_statements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "service.py").write_text(
                "import logging\n"
                "logger = logging.getLogger(__name__)\n\n"
                "def sync_user(user_id):\n"
                "    print('starting sync', user_id)\n"
                "    logger.error('sync failed for user %s', user_id)\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", ".")

            logs = sorted(self.list_records(project, "code-log"), key=lambda row: row["line"])
            self.assertEqual([log["level"] for log in logs], ["print", "error"])
            self.assertEqual([log["function"] for log in logs], ["sync_user", "sync_user"])
            self.assertIn("sync failed for user %s", logs[1]["message_template"])

    def test_learn_path_extracts_javascript_console_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "app.js").write_text(
                "function loadUser(id) {\n"
                "  console.error('load failed', id);\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", ".")

            logs = self.list_records(project, "code-log")
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["level"], "error")
            self.assertEqual(logs[0]["function"], "loadUser")
            self.assertIn("load failed", logs[0]["message_template"])

    def test_learn_path_extracts_arkts_symbols_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import hilog from '@ohos.hilog';\n\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  aboutToAppear(): void {\n"
                "    console.error('load account failed');\n"
                "    hilog.info(0x0000, 'Index', 'page ready %{public}s', 'ok');\n"
                "  }\n"
                "  build() {\n"
                "    Column() {}\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            files = self.list_code_files(project)
            symbols = self.list_records(project, "code-symbol")
            logs = sorted(self.list_records(project, "code-log"), key=lambda row: row["line"])

            self.assertEqual(files, {"pages/Index.ets"})
            self.assertTrue(any(row["symbol"] == "Index" and row["symbol_type"] == "component" for row in symbols))
            self.assertTrue(any(row["symbol"] == "aboutToAppear" and row["symbol_type"] == "function" for row in symbols))
            self.assertEqual([log["level"] for log in logs], ["error", "info"])
            self.assertEqual([log["function"] for log in logs], ["aboutToAppear", "aboutToAppear"])
            self.assertEqual(logs[1]["logger"], "hilog")
            self.assertIn("page ready %{public}s", logs[1]["message_template"])

    def test_learn_entry_follows_arkts_relative_imports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "model").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import { UserModel } from '../model/UserModel';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  build() {}\n"
                "}\n",
                encoding="utf-8",
            )
            (project / "model" / "UserModel.ets").write_text(
                "export class UserModel {\n"
                "  name: string = '';\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-entry", "--entry", "pages/Index.ets", "--depth", "1", "--json")

            self.assertEqual(self.list_code_files(project), {"pages/Index.ets", "model/UserModel.ets"})

    def test_context_returns_code_log_and_related_edge_matches(self) -> None:
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

            self.assertEqual(payload["code_log_matches"][0]["file_path"], "worker.py")
            self.assertEqual(payload["code_log_matches"][0]["function"], "process_job")
            self.assertTrue(
                any(edge["relation"] == "emits_log" for edge in payload["edge_matches"])
            )

    def test_context_limits_network_edges_and_reports_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            db_path = project / ".agent-memory" / "memory.db"
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

    def test_context_returns_one_hop_evidence_chains(self) -> None:
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
            chain = next(
                item for item in payload["evidence_chains"]
                if item["relation"] == "emits_log"
            )

            self.assertEqual(chain["depth"], 1)
            self.assertEqual(chain["reason"], "matched log statement emitted by symbol")
            self.assertEqual(chain["target_type"], "code_log_statement")
            self.assertIn("worker.py", chain["evidence"])

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

            logs = project / ".agent-memory" / "vault" / "Codebase Wiki" / "log-statements.md"
            edges = project / ".agent-memory" / "vault" / "Codebase Wiki" / "memory-edges.md"
            self.assertTrue(logs.exists())
            self.assertTrue(edges.exists())
            self.assertIn("retrying job %s", logs.read_text(encoding="utf-8"))
            self.assertIn("emits_log", edges.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
