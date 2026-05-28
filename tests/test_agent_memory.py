import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import os
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"


class AgentMemoryRuntimeTests(unittest.TestCase):
    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

    def project_memory_dir(self, project: Path) -> Path:
        project_id = self.project_id(project)
        return self.memory_home(project) / "projects" / project_id

    def project_id(self, project: Path) -> str:
        import hashlib

        return hashlib.sha256(str(project.resolve()).encode("utf-8")).hexdigest()[:16]

    def run_memory(
        self,
        project: Path,
        *args: str,
        memory_home: Optional[Path] = None,
        use_memory_home_arg: bool = True,
        env: Optional[dict[str, str]] = None,
        cwd: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(RUNTIME), *args, "--project", str(project)]
        if use_memory_home_arg:
            command.extend(["--memory-home", str(memory_home or self.memory_home(project))])
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        return subprocess.run(
            command,
            cwd=cwd or REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
            env=process_env,
        )

    def list_code_files(self, project: Path, memory_home: Optional[Path] = None) -> set[str]:
        result = self.run_memory(
            project,
            "list",
            "--type",
            "code-file",
            "--json",
            memory_home=memory_home,
        )
        return {row["file_path"] for row in json.loads(result.stdout)}

    def list_records(self, project: Path, kind: str, memory_home: Optional[Path] = None) -> list[dict]:
        result = self.run_memory(
            project,
            "list",
            "--type",
            kind,
            "--json",
            memory_home=memory_home,
        )
        return json.loads(result.stdout)

    def miss_list(self, project: Path, memory_home: Optional[Path] = None) -> list[dict]:
        result = self.run_memory(project, "miss-list", "--json", memory_home=memory_home)
        return json.loads(result.stdout)

    def test_init_uses_configured_global_memory_home_without_project_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            memory_home = root / "global-memory"
            project.mkdir()

            self.run_memory(project, "init", memory_home=memory_home)

            project_memory = memory_home / "projects" / self.project_id(project)
            self.assertTrue((project_memory / "memory.db").exists())
            self.assertTrue((project_memory / "runtime").exists())
            self.assertTrue((project_memory / "vault").exists())
            self.assertFalse((project / ".agent-memory").exists())

    def test_environment_memory_home_is_used_when_cli_option_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            memory_home = root / "env-memory"
            project.mkdir()

            self.run_memory(
                project,
                "init",
                use_memory_home_arg=False,
                env={"AGENT_MEMORY_HOME": str(memory_home)},
            )

            self.assertTrue((memory_home / "projects" / self.project_id(project) / "memory.db").exists())
            self.assertFalse((project / ".agent-memory").exists())

    def test_default_memory_home_is_current_workspace_agent_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            project = workspace / "app"
            project.mkdir()

            command = [sys.executable, str(RUNTIME), "init", "--project", str(project)]
            process_env = os.environ.copy()
            process_env.pop("AGENT_MEMORY_HOME", None)
            subprocess.run(
                command,
                cwd=workspace,
                text=True,
                capture_output=True,
                check=True,
                env=process_env,
            )

            self.assertTrue((workspace / ".agent-memory" / "projects" / self.project_id(project) / "memory.db").exists())
            self.assertFalse((Path.home() / ".agent-memory" / "projects" / self.project_id(project) / "memory.db").exists())

    def test_global_memory_home_keeps_project_databases_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory_home = root / "memory"
            project_a = root / "app-a"
            project_b = root / "app-b"
            project_a.mkdir()
            project_b.mkdir()

            self.run_memory(
                project_a,
                "update",
                "--type",
                "semantic",
                "--fact",
                "Project A fact",
                "--source",
                "test",
                memory_home=memory_home,
            )
            self.run_memory(
                project_b,
                "update",
                "--type",
                "semantic",
                "--fact",
                "Project B fact",
                "--source",
                "test",
                memory_home=memory_home,
            )

            facts_a = self.list_records(project_a, "semantic", memory_home=memory_home)
            facts_b = self.list_records(project_b, "semantic", memory_home=memory_home)
            self.assertEqual([row["fact"] for row in facts_a], ["Project A fact"])
            self.assertEqual([row["fact"] for row in facts_b], ["Project B fact"])

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

    def test_learn_path_can_archive_external_source_into_current_project_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "memory-archive"
            source = root / "external-app"
            archive.mkdir()
            (source / "lib").mkdir(parents=True)
            (source / "lib" / "main.py").write_text(
                "def bootstrap():\n"
                "    return 'external app'\n",
                encoding="utf-8",
            )

            self.run_memory(archive, "learn-path", "--source", str(source), "--path", "lib", "--json")

            self.assertEqual(self.list_code_files(archive), {"lib/main.py"})
            self.assertEqual(self.list_code_files(source, memory_home=self.memory_home(archive)), set())
            result = self.run_memory(archive, "context", "--query", "bootstrap external app", "--json")
            payload = json.loads(result.stdout)
            self.assertTrue(any(row["file_path"] == "lib/main.py" for row in payload["wiki_matches"]))

    def test_learn_entry_follows_imports_inside_external_source_but_archives_current_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "memory-archive"
            source = root / "external-harmony"
            archive.mkdir()
            (source / "pages").mkdir(parents=True)
            (source / "model").mkdir()
            (source / "pages" / "Index.ets").write_text(
                "import { UserModel } from '../model/UserModel';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index { build() {} }\n",
                encoding="utf-8",
            )
            (source / "model" / "UserModel.ets").write_text(
                "export class UserModel {}\n",
                encoding="utf-8",
            )

            self.run_memory(
                archive,
                "learn-entry",
                "--source",
                str(source),
                "--entry",
                "pages/Index.ets",
                "--depth",
                "1",
                "--json",
            )

            self.assertEqual(self.list_code_files(archive), {"pages/Index.ets", "model/UserModel.ets"})
            self.assertEqual(self.list_code_files(source, memory_home=self.memory_home(archive)), set())

    def test_wiki_index_can_replace_archive_from_external_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "memory-archive"
            source = root / "external-app"
            archive.mkdir()
            (source / "feature").mkdir(parents=True)
            (source / "feature" / "page.ets").write_text(
                "@Component\n"
                "struct FeaturePage { build() {} }\n",
                encoding="utf-8",
            )

            self.run_memory(archive, "wiki-index", "--source", str(source))

            self.assertEqual(self.list_code_files(archive), {"feature/page.ets"})

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

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Reflection Quality.md"
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

    def test_repeated_query_miss_updates_existing_open_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(project, "context", "--query", "No Such Memory Token", "--json")
            self.run_memory(project, "context", "--query", "  no   such memory token  ", "--json")

            misses = self.miss_list(project)
            self.assertEqual(len(misses), 1)
            self.assertEqual(misses[0]["query"], "No Such Memory Token")
            self.assertEqual(misses[0]["normalized_query"], "no such memory token")
            self.assertEqual(misses[0]["miss_count"], 2)
            self.assertIsNotNone(misses[0]["last_seen_at"])

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

            action = next(action for action in actions if action["action"] == "review_query_miss" and action["id"] == 1)
            self.assertEqual(action["miss_count"], 1)

    def test_vault_export_writes_query_misses_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "context", "--query", "unanswered-question", "--json")

            self.run_memory(project, "vault-export")

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Query Misses.md"
            self.assertTrue(dashboard.exists())
            self.assertIn("unanswered-question", dashboard.read_text(encoding="utf-8"))

    def test_vault_export_writes_query_misses_codebase_wiki_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "context", "--query", "arkts route miss", "--json")
            self.run_memory(project, "context", "--query", "arkts   route miss", "--json")

            self.run_memory(project, "vault-export")

            wiki_page = self.project_memory_dir(project) / "vault" / "Codebase Wiki" / "query-misses.md"
            index = self.project_memory_dir(project) / "vault" / "index.md"
            self.assertTrue(wiki_page.exists())
            content = wiki_page.read_text(encoding="utf-8")
            self.assertIn("arkts route miss", content)
            self.assertIn("misses 2", content)
            self.assertIn("[[Codebase Wiki/query-misses]]", index.read_text(encoding="utf-8"))

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

    def test_learn_path_extracts_harmonyos_json5_config_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "entry" / "src" / "main").mkdir(parents=True)
            (project / "entry" / "oh-package.json5").write_text(
                "{\n"
                "  \"dependencies\": {\n"
                "    \"@ohos/axios\": \"^2.2.0\"\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            (project / "entry" / "src" / "main" / "module.json5").write_text(
                "{\n"
                "  \"module\": {\n"
                "    \"name\": \"entry\",\n"
                "    \"abilities\": [{ \"name\": \"EntryAbility\" }],\n"
                "    \"requestPermissions\": [{ \"name\": \"ohos.permission.INTERNET\" }],\n"
                "    \"pages\": \"$profile:main_pages\"\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "entry")

            symbols = self.list_records(project, "code-symbol")
            symbol_pairs = {(row["symbol"], row["symbol_type"]) for row in symbols}
            self.assertIn(("EntryAbility", "ability"), symbol_pairs)
            self.assertIn(("ohos.permission.INTERNET", "permission"), symbol_pairs)
            self.assertIn(("@ohos/axios", "dependency"), symbol_pairs)

    def test_learn_path_extracts_arkts_router_and_resource_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  build() {\n"
                "    Text($r('app.string.home_title'))\n"
                "    Image($r(\"app.media.logo\"))\n"
                "  }\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            symbols = self.list_records(project, "code-symbol")
            symbol_pairs = {(row["symbol"], row["symbol_type"]) for row in symbols}
            self.assertIn(("pages/Detail", "route"), symbol_pairs)
            self.assertIn(("app.string.home_title", "resource"), symbol_pairs)
            self.assertIn(("app.media.logo", "resource"), symbol_pairs)

    def test_arkts_learning_writes_knowledge_summaries_for_files_and_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  build() {\n"
                "    Text($r('app.string.home_title'))\n"
                "  }\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            files = self.list_records(project, "code-file")
            symbols = self.list_records(project, "code-symbol")
            file_summary = files[0]["summary"]
            symbol_summaries = {
                (row["symbol"], row["symbol_type"]): row["summary"]
                for row in symbols
            }

            self.assertIn("components: Index", file_summary)
            self.assertIn("routes: pages/Detail", file_summary)
            self.assertIn("resources: app.string.home_title", file_summary)
            self.assertIn("ArkTS component", symbol_summaries[("Index", "component")])
            self.assertIn("route target", symbol_summaries[("pages/Detail", "route")])
            self.assertIn("resource", symbol_summaries[("app.string.home_title", "resource")])

    def test_chinese_problem_query_expands_to_arkts_route_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            result = self.run_memory(project, "context", "--query", "页面跳转后白屏", "--json")
            data = json.loads(result.stdout)
            matched = [
                item
                for item in data["wiki_matches"]
                if item.get("symbol") == "pages/Detail" or item.get("file_path") == "pages/Index.ets"
            ]
            self.assertTrue(matched)
            self.assertTrue(any(item.get("match_reasons") for item in matched))
            self.assertTrue(any("expanded_query" in reason for item in matched for reason in item["match_reasons"]))

    def test_chinese_problem_query_expands_to_arkts_resource_and_log_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import hilog from '@ohos.hilog';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  build() {\n"
                "    Image($r('app.media.logo'))\n"
                "  }\n"
                "  aboutToAppear() {\n"
                "    hilog.error(0x0000, 'Index', 'load profile failed');\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            resource_result = self.run_memory(project, "context", "--query", "图片资源显示不出来", "--json")
            resource_data = json.loads(resource_result.stdout)
            self.assertTrue(
                any(item.get("symbol") == "app.media.logo" for item in resource_data["wiki_matches"])
            )
            resource_match = next(item for item in resource_data["wiki_matches"] if item.get("symbol") == "app.media.logo")
            self.assertIn("resource", resource_match["search_terms"])

            log_result = self.run_memory(project, "context", "--query", "加载用户资料失败日志", "--json")
            log_data = json.loads(log_result.stdout)
            self.assertTrue(
                any(item.get("message_template") == "load profile failed" for item in log_data["code_log_matches"])
            )
            log_match = next(item for item in log_data["code_log_matches"] if item.get("message_template") == "load profile failed")
            self.assertTrue(any("log" in reason for reason in log_match["match_reasons"]))

    def test_query_reranks_exact_file_path_above_expanded_summary_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            (project / "pages" / "Detail.ets").write_text(
                "@Entry\n"
                "@Component\n"
                "struct Detail {\n"
                "  build() {}\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            result = self.run_memory(project, "context", "--query", "pages/Detail.ets", "--json")
            data = json.loads(result.stdout)

            self.assertEqual(data["wiki_matches"][0]["file_path"], "pages/Detail.ets")
            self.assertIn("exact_file_path", data["wiki_matches"][0]["match_reasons"])

    def test_learn_business_writes_business_semantics_to_existing_code_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "summary": "ArkTS profile detail page",
                        "business_summary": "个人信息详情页，负责加载用户资料并展示头像。",
                        "business_terms": ["个人信息", "用户资料", "profile", "头像", "avatar"],
                        "symbols": [
                            {
                                "symbol": "loadUserProfile",
                                "symbol_type": "function",
                                "business_summary": "加载用户资料的方法。",
                                "business_terms": ["加载用户资料", "profile", "load profile"],
                            }
                        ],
                        "logs": [
                            {
                                "message_template": "load profile failed",
                                "function": "loadUserProfile",
                                "level": "error",
                                "logger": "hilog",
                                "business_summary": "用户资料加载失败时输出的错误日志。",
                                "business_terms": ["用户资料加载失败", "profile failed", "load profile failed"],
                            }
                        ],
                    }
                ]
            }

            self.run_memory(project, "learn-business", "--payload", json.dumps(payload, ensure_ascii=False), "--json")

            files = self.list_records(project, "code-file")
            symbols = self.list_records(project, "code-symbol")
            logs = self.list_records(project, "code-log")
            self.assertEqual(files[0]["business_summary"], "个人信息详情页，负责加载用户资料并展示头像。")
            self.assertIn("头像", json.loads(files[0]["business_terms"]))
            self.assertEqual(symbols[0]["business_summary"], "加载用户资料的方法。")
            self.assertEqual(logs[0]["business_summary"], "用户资料加载失败时输出的错误日志。")

    def test_business_terms_are_high_signal_query_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "business_summary": "个人信息详情页，负责加载用户资料并展示头像。",
                        "business_terms": ["个人信息", "用户资料", "profile", "头像", "avatar"],
                        "symbols": [
                            {
                                "symbol": "loadUserProfile",
                                "symbol_type": "function",
                                "business_summary": "加载用户资料的方法。",
                                "business_terms": ["加载用户资料", "profile", "load profile"],
                            }
                        ],
                        "logs": [
                            {
                                "message_template": "load profile failed",
                                "function": "loadUserProfile",
                                "level": "error",
                                "business_summary": "用户资料加载失败时输出的错误日志。",
                                "business_terms": ["用户资料加载失败", "profile failed"],
                            }
                        ],
                    }
                ]
            }
            self.run_memory(project, "learn-business", "--payload", json.dumps(payload, ensure_ascii=False), "--json")

            result = self.run_memory(project, "context", "--query", "个人信息头像加载失败", "--json")
            data = json.loads(result.stdout)

            self.assertEqual(data["wiki_matches"][0]["file_path"], "pages/ProfileDetail.ets")
            self.assertIn("头像", data["wiki_matches"][0]["business_terms"])
            self.assertTrue(any("business_terms" in reason for reason in data["wiki_matches"][0]["match_reasons"]))
            self.assertTrue(any(log["message_template"] == "load profile failed" for log in data["code_log_matches"]))

    def test_vault_and_health_include_code_business_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "business_summary": "个人信息详情页，负责加载用户资料并展示头像。",
                        "business_terms": ["个人信息", "profile", "头像"],
                    }
                ]
            }
            self.run_memory(project, "learn-business", "--payload", json.dumps(payload, ensure_ascii=False), "--json")
            self.run_memory(project, "learn-business", "--payload", json.dumps({"files": [{"file_path": "pages/Empty.ets"}]}), "--json")

            health = json.loads(self.run_memory(project, "maintain-health", "--json").stdout)
            self.assertEqual(health["counts"]["code_files_missing_business_terms"], 1)

            self.run_memory(project, "vault-export")
            files_page = self.project_memory_dir(project) / "vault" / "Codebase Wiki" / "files.md"
            content = files_page.read_text(encoding="utf-8")
            self.assertIn("Business: 个人信息详情页", content)
            self.assertIn("Terms: 个人信息, profile, 头像", content)

    def test_arkts_memory_edges_connect_imports_routes_and_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "model").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import { UserModel } from '../model/UserModel';\n"
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  build() {\n"
                "    Text($r('app.string.home_title'))\n"
                "  }\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            (project / "pages" / "Detail.ets").write_text(
                "@Component\n"
                "struct Detail { build() {} }\n",
                encoding="utf-8",
            )
            (project / "model" / "UserModel.ets").write_text(
                "export class UserModel {}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-entry", "--entry", "pages/Index.ets", "--depth", "1", "--json")

            edges = self.list_records(project, "memory-edge")
            relations = {(edge["source_type"], edge["relation"], edge["target_type"]) for edge in edges}
            evidence_by_relation = {edge["relation"]: edge["evidence"] for edge in edges}

            self.assertIn(("code_file", "imports", "code_file"), relations)
            self.assertIn(("code_file", "routes_to", "code_file"), relations)
            self.assertIn(("code_file", "uses_resource", "code_symbol"), relations)
            self.assertIn("pages/Index.ets -> model/UserModel.ets", evidence_by_relation["imports"])
            self.assertIn("pages/Index.ets -> pages/Detail.ets", evidence_by_relation["routes_to"])
            self.assertIn("app.string.home_title", evidence_by_relation["uses_resource"])

    def test_learn_entry_follows_arkts_router_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "  build() {}\n"
                "}\n",
                encoding="utf-8",
            )
            (project / "pages" / "Detail.ets").write_text(
                "@Component\n"
                "struct Detail {\n"
                "  build() {}\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-entry", "--entry", "pages/Index.ets", "--depth", "1", "--json")

            self.assertEqual(self.list_code_files(project), {"pages/Index.ets", "pages/Detail.ets"})

    def test_learn_entry_returns_parse_stats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  aboutToAppear(): void {\n"
                "    console.error('load failed');\n"
                "  }\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "  build() {\n"
                "    Text($r('app.string.home_title'))\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            result = self.run_memory(project, "learn-entry", "--entry", "pages/Index.ets", "--depth", "0", "--json")
            stats = json.loads(result.stdout)["parse_stats"]

            self.assertEqual(stats["files_indexed"], 1)
            self.assertEqual(stats["languages"]["ArkTS"], 1)
            self.assertEqual(stats["symbols_by_type"]["component"], 1)
            self.assertEqual(stats["symbols_by_type"]["route"], 1)
            self.assertEqual(stats["symbols_by_type"]["resource"], 1)
            self.assertEqual(stats["code_logs_total"], 1)
            self.assertEqual(stats["code_logs_by_level"]["error"], 1)
            self.assertGreaterEqual(stats["memory_edges_total"], 1)

    def test_learn_path_json_returns_parse_stats_for_harmonyos_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "entry").mkdir()
            (project / "entry" / "oh-package.json5").write_text(
                "{\n"
                "  \"dependencies\": {\n"
                "    \"@ohos/axios\": \"^2.2.0\"\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            result = self.run_memory(project, "learn-path", "--path", "entry", "--json")
            payload = json.loads(result.stdout)

            self.assertEqual(payload["parse_stats"]["files_indexed"], 1)
            self.assertEqual(payload["parse_stats"]["languages"]["HarmonyOS Config"], 1)
            self.assertEqual(payload["parse_stats"]["symbols_by_type"]["dependency"], 1)

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

            logs = self.project_memory_dir(project) / "vault" / "Codebase Wiki" / "log-statements.md"
            edges = self.project_memory_dir(project) / "vault" / "Codebase Wiki" / "memory-edges.md"
            self.assertTrue(logs.exists())
            self.assertTrue(edges.exists())
            self.assertIn("retrying job %s", logs.read_text(encoding="utf-8"))
            self.assertIn("emits_log", edges.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
