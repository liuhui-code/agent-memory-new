# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"


class AutoReflectionSummaryTests(unittest.TestCase):
    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

    def runtime_dir(self, project: Path) -> Path:
        projects = self.memory_home(project) / "projects"
        matches = list(projects.glob("*/runtime"))
        if not matches:
            raise AssertionError("runtime directory not found")
        return matches[0]

    def run_memory(
        self,
        project: Path,
        *args: str,
        memory_home: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(RUNTIME), *args, "--project", str(project)]
        command.extend(["--memory-home", str(memory_home or self.memory_home(project))])
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
            env=os.environ.copy(),
        )

    def test_context_writes_last_task_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "ArkTS route diagnosis checks router.pushUrl.",
                "--source",
                "test",
            )

            self.run_memory(project, "context", "--query", "ArkTS route diagnosis", "--json")
            trace = json.loads((self.runtime_dir(project) / "last_task_trace.json").read_text(encoding="utf-8"))

        self.assertEqual("memory_query", trace["intent"])
        self.assertEqual(["arkts route diagnosis"], trace["queries"])
        self.assertIn("context: arkts route diagnosis", trace["context_used"])
        self.assertIn("reflection_payload_template", trace)
        self.assertIn("candidate_evidence", trace)
        self.assertIn("auto_summary_quality", trace)
        self.assertIn("reflection_payload_placeholders", trace)
        self.assertIn("verification_method", trace["reflection_payload_placeholders"])
        self.assertIn("counter_evidence", trace["auto_summary_quality"]["missing_fields"])

    def test_reflect_from_last_task_uses_trace_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "ArkTS route diagnosis checks router.pushUrl.",
                "--source",
                "test",
            )
            self.run_memory(project, "context", "--query", "ArkTS route diagnosis", "--json")

            result = self.run_memory(
                project,
                "reflect",
                "--from-last-task",
                "--task",
                "Review ArkTS route diagnosis memory",
                "--lesson",
                "Use the current route diagnosis context before widening the search.",
                "--json",
            )
            data = json.loads(result.stdout)

        self.assertEqual(1, data["id"])
        self.assertEqual("arkts route diagnosis", data["problem"])
        self.assertIn("context: arkts route diagnosis", data["context_used"])
        self.assertIn("context: arkts route diagnosis", data["evidence"])

    def test_maintain_plan_reviews_unreflected_task_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "ArkTS route diagnosis checks router.pushUrl.",
                "--source",
                "test",
            )
            self.run_memory(project, "context", "--query", "ArkTS route diagnosis", "--json")

            plan = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)
            actions = [action for action in plan["actions"] if action["action"] == "review_unreflected_task_trace"]

        self.assertEqual(1, len(actions))
        self.assertEqual("auto_reflection", actions[0]["governance_lane"])
        self.assertIn("--from-last-task", actions[0]["command_template"])
        self.assertEqual(1, plan["governance_summary"]["unreflected_task_trace_reviews"])

    def test_maintain_plan_reviews_low_evidence_auto_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "ArkTS route diagnosis checks router.pushUrl.",
                "--source",
                "test",
            )
            self.run_memory(project, "context", "--query", "ArkTS route diagnosis", "--json")

            plan = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)
            actions = [action for action in plan["actions"] if action["action"] == "review_low_evidence_auto_summary"]

        self.assertEqual(1, len(actions))
        self.assertEqual("auto_reflection", actions[0]["governance_lane"])
        self.assertIn("verification_method", actions[0]["auto_summary_quality"]["missing_fields"])
        self.assertIn("counter_evidence", actions[0]["auto_summary_quality"]["missing_fields"])
        self.assertIn("negative_preconditions", actions[0]["reflection_payload_placeholders"])
        self.assertEqual(1, plan["governance_summary"]["low_evidence_auto_summary_reviews"])

    def test_maintain_plan_omits_task_trace_after_reflection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "ArkTS route diagnosis checks router.pushUrl.",
                "--source",
                "test",
            )
            self.run_memory(project, "context", "--query", "ArkTS route diagnosis", "--json")
            self.run_memory(
                project,
                "reflect",
                "--from-last-task",
                "--task",
                "Review ArkTS route diagnosis memory",
                "--lesson",
                "Use route diagnosis context before widening.",
                "--json",
            )

            plan = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)
            actions = [action for action in plan["actions"] if action["action"] == "review_unreflected_task_trace"]
            low_evidence_actions = [action for action in plan["actions"] if action["action"] == "review_low_evidence_auto_summary"]

        self.assertEqual([], actions)
        self.assertEqual([], low_evidence_actions)
        self.assertEqual(0, plan["governance_summary"]["unreflected_task_trace_reviews"])
        self.assertEqual(0, plan["governance_summary"]["low_evidence_auto_summary_reviews"])


if __name__ == "__main__":
    unittest.main()
