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


class RetrievalFeedbackTests(unittest.TestCase):
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
            "task": "ArkTS route blank screen",
            "summary": "Broad route advice.",
            "lesson": "Try broad route checks.",
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "try broad route checks",
            "verification_method": "not verified on current source",
            "source_cases": ["old_case:1"],
            "reuse_feedback": "misleading",
            "confidence": 0.4,
            "misleading_score": 0.4,
        }
        strong_payload = {
            "experience_type": "procedure_experience",
            "task": "ArkTS route blank screen diagnosis",
            "summary": "Verified route target mismatch diagnosis.",
            "lesson": "For ArkTS route blank screen, inspect router.pushUrl target and page registration first.",
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "inspect router.pushUrl target",
            "verification_method": "ran route navigation test",
            "source_cases": ["incident_trace:7"],
            "reuse_feedback": "reused successfully",
            "confidence": 0.95,
        }
        self.run_memory(project, "reflect", "--payload", json.dumps(weak_payload))
        self.run_memory(project, "reflect", "--payload", json.dumps(strong_payload))

    def test_retrieval_feedback_command_writes_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)

            result = self.run_memory(
                project,
                "retrieval-feedback",
                "--query",
                "ArkTS route blank screen 如何定位",
                "--type",
                "reflection",
                "--id",
                "1",
                "--reason",
                "weak_related",
                "--replacement-type",
                "reflection",
                "--replacement-id",
                "2",
                "--json",
            )
            data = json.loads(result.stdout)

        self.assertEqual("reflection", data["record_type"])
        self.assertEqual(1, data["record_id"])
        self.assertEqual("weak_related", data["reason"])

    def test_context_penalizes_feedbacked_reflection_for_similar_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)
            self.run_memory(
                project,
                "retrieval-feedback",
                "--query",
                "ArkTS route blank screen 如何定位",
                "--type",
                "reflection",
                "--id",
                "1",
                "--reason",
                "weak_related",
                "--json",
            )

            result = self.run_memory(project, "context", "--query", "ArkTS route blank screen 如何定位", "--json")
            data = json.loads(result.stdout)

        weak = next(item for item in data["reflections"] if item["id"] == 1)
        strong = next(item for item in data["reflections"] if item["id"] == 2)
        self.assertGreater(weak["feedback_penalty"], 0)
        self.assertLess(weak["rerank_score"], strong["rerank_score"])

    def test_maintain_plan_reviews_open_retrieval_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)
            self.run_memory(
                project,
                "retrieval-feedback",
                "--query",
                "ArkTS route blank screen 如何定位",
                "--type",
                "reflection",
                "--id",
                "1",
                "--reason",
                "misleading",
                "--json",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        actions = [action for action in data["actions"] if action["action"] == "review_retrieval_feedback"]
        self.assertEqual(1, len(actions))
        self.assertEqual(1, data["governance_summary"]["retrieval_feedback_reviews"])
        self.assertEqual("misleading", actions[0]["reason_code"])
