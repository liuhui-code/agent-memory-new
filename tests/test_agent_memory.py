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


if __name__ == "__main__":
    unittest.main()
