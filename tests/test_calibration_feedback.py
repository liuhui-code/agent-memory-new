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


class CalibrationFeedbackTests(unittest.TestCase):
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

    def seed_reflection(self, project: Path, confidence: float = 0.55) -> None:
        payload = {
            "experience_type": "procedure_experience",
            "task": "ArkTS route blank screen",
            "summary": "Route target mismatch diagnosis.",
            "lesson": "Inspect router.pushUrl target and page registration first.",
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "inspect router.pushUrl target",
            "verification_method": "manual smoke test",
            "source_cases": ["incident_trace:3"],
            "confidence": confidence,
        }
        self.run_memory(project, "reflect", "--payload", json.dumps(payload))

    def test_verified_useful_feedback_raises_calibrated_trust(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflection(project, confidence=0.55)
            before = json.loads(
                self.run_memory(project, "context", "--query", "ArkTS route blank screen", "--json").stdout
            )["reflections"][0]

            self.run_memory(
                project,
                "retrieval-feedback",
                "--query",
                "ArkTS route blank screen",
                "--type",
                "reflection",
                "--id",
                "1",
                "--reason",
                "verified_useful",
                "--json",
            )
            after = json.loads(
                self.run_memory(project, "context", "--query", "ArkTS route blank screen", "--json").stdout
            )["reflections"][0]

        self.assertGreater(after["trust_score"], before["trust_score"])
        self.assertGreater(after["calibration_feedback_bonus"], 0)
        self.assertIn("verified_useful", after["calibration_feedback_reasons"])

    def test_overtrusted_feedback_lowers_trust_and_emits_review_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflection(project, confidence=0.95)
            before = json.loads(
                self.run_memory(project, "context", "--query", "ArkTS route blank screen", "--json").stdout
            )["reflections"][0]

            self.run_memory(
                project,
                "retrieval-feedback",
                "--query",
                "ArkTS route blank screen",
                "--type",
                "reflection",
                "--id",
                "1",
                "--reason",
                "overtrusted",
                "--json",
            )
            after = json.loads(
                self.run_memory(project, "context", "--query", "ArkTS route blank screen", "--json").stdout
            )["reflections"][0]
            maintain = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)

        self.assertLess(after["trust_score"], before["trust_score"])
        self.assertGreater(after["calibration_feedback_penalty"], 0)
        actions = [action for action in maintain["actions"] if action["action"] == "review_overtrusted_memory"]
        self.assertEqual(1, len(actions))
        self.assertEqual(1, maintain["governance_summary"]["overtrusted_memory_reviews"])


if __name__ == "__main__":
    unittest.main()
