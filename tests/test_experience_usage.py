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


class ExperienceUsageTests(unittest.TestCase):
    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

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

    def seed_reflections(self, project: Path) -> None:
        weak_payload = {
            "experience_type": "procedure_experience",
            "task": "ArkTS route blank screen old diagnosis",
            "summary": "Broad old route diagnosis.",
            "lesson": "Inspect many route files broadly.",
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "inspect many route files broadly",
            "verification_method": "manual old case",
            "source_cases": ["old_case:route"],
            "reuse_feedback": "unknown",
            "confidence": 0.7,
        }
        strong_payload = {
            "experience_type": "procedure_experience",
            "task": "ArkTS route blank screen target mismatch",
            "summary": "Specific route target mismatch.",
            "lesson": "Check router.pushUrl target against page registration first.",
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "compare router.pushUrl target and page registration",
            "verification_method": "verified on current route case",
            "source_cases": ["incident_trace:route-target"],
            "reuse_feedback": "reused successfully",
            "confidence": 0.9,
        }
        self.run_memory(project, "reflect", "--payload", json.dumps(weak_payload))
        self.run_memory(project, "reflect", "--payload", json.dumps(strong_payload))

    def test_experience_usage_command_writes_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)

            result = self.run_memory(
                project,
                "experience-usage",
                "--query",
                "ArkTS route blank screen 如何定位",
                "--type",
                "reflection",
                "--id",
                "1",
                "--outcome",
                "misleading",
                "--note",
                "recent but broad advice pulled diagnosis away from target mismatch",
                "--json",
            )
            data = json.loads(result.stdout)

        self.assertEqual("reflection", data["record_type"])
        self.assertEqual(1, data["record_id"])
        self.assertEqual("misleading", data["outcome"])
        self.assertEqual("arkts route blank screen 如何定位", data["normalized_query"])

    def test_context_uses_experience_usage_adjustments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)
            self.run_memory(
                project,
                "experience-usage",
                "--query",
                "ArkTS route blank screen 如何定位",
                "--type",
                "reflection",
                "--id",
                "1",
                "--outcome",
                "misleading",
                "--json",
            )
            self.run_memory(
                project,
                "experience-usage",
                "--query",
                "ArkTS route blank screen 如何定位",
                "--type",
                "reflection",
                "--id",
                "2",
                "--outcome",
                "helpful",
                "--json",
            )

            result = self.run_memory(project, "context", "--query", "ArkTS route blank screen 如何定位", "--json")
            data = json.loads(result.stdout)

        weak = next(item for item in data["reflections"] if item["id"] == 1)
        strong = next(item for item in data["reflections"] if item["id"] == 2)
        self.assertGreater(weak["usage_feedback_penalty"], 0)
        self.assertGreater(strong["usage_feedback_bonus"], 0)
        self.assertLess(weak["rerank_score"], strong["rerank_score"])
        self.assertIn("misleading", weak["usage_feedback_reasons"])

    def test_maintain_plan_reviews_misleading_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)
            self.run_memory(
                project,
                "experience-usage",
                "--query",
                "ArkTS route blank screen 如何定位",
                "--type",
                "reflection",
                "--id",
                "1",
                "--outcome",
                "misleading",
                "--json",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        actions = [action for action in data["actions"] if action["action"] == "review_experience_usage"]
        self.assertEqual(1, len(actions))
        self.assertEqual(1, data["governance_summary"]["experience_usage_reviews"])
        self.assertEqual("misleading", actions[0]["dominant_outcome"])


if __name__ == "__main__":
    unittest.main()
