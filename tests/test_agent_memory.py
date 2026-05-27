import json
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


if __name__ == "__main__":
    unittest.main()
