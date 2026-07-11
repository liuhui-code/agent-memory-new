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


class QualityPerformanceScoringTests(unittest.TestCase):
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

    def test_quality_scoring_rewards_structured_verified_experience(self) -> None:
        from tools.agent_memory_runtime.quality_scoring import score_reflection_quality

        row = {
            "id": 1,
            "experience_type": "procedure_experience",
            "confidence": 0.9,
            "status": "active",
            "verification_method": "ran targeted unit test",
            "source_cases": '["incident_trace:1"]',
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "inspect router.pushUrl target",
            "reuse_feedback": "reused successfully",
        }

        score = score_reflection_quality(row)

        self.assertGreaterEqual(score["quality_score"], 0.75)
        self.assertIn(score["quality_band"], {"good", "excellent"})
        self.assertGreater(score["score_parts"]["evidence_strength"], 0.8)
        self.assertEqual(score["recommended_action"], "keep_active")

    def test_quality_scoring_penalizes_misleading_stale_experience(self) -> None:
        from tools.agent_memory_runtime.quality_scoring import score_reflection_quality

        row = {
            "id": 2,
            "experience_type": "procedure_experience",
            "confidence": 0.35,
            "status": "stale",
            "is_stale": 1,
            "misleading_score": 0.9,
            "lesson": "broad old advice",
        }

        score = score_reflection_quality(row)

        self.assertLess(score["quality_score"], 0.45)
        self.assertEqual(score["quality_band"], "poor")
        self.assertEqual(score["recommended_action"], "review_or_stale")

    def test_performance_sample_scores_fast_bounded_operation_highly(self) -> None:
        from tools.agent_memory_runtime.performance_scoring import build_performance_sample
        from tools.agent_memory_runtime.storage import resolve_project

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "app"
            project_root.mkdir()
            project = resolve_project(str(project_root), str(self.memory_home(project_root)))

            sample = build_performance_sample(
                project,
                operation="context",
                elapsed_ms=25.0,
                result_counts={"semantic_facts": 2, "reflections": 1},
                token_estimate=900,
                status="ok",
            )

        self.assertEqual(sample["operation"], "context")
        self.assertGreater(sample["performance_score"], 0.8)
        self.assertEqual(sample["performance_band"], "excellent")

    def test_maintain_plan_includes_quality_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            payload = {
                "experience_type": "procedure_experience",
                "task": "Diagnose ArkTS route blank screen",
                "summary": "Route target mismatch was found through incident trace.",
                "lesson": "When ArkTS navigation opens a blank page, inspect router.pushUrl target and page registration first.",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "verification_method": "ran targeted route test",
                "source_cases": ["incident_trace:1"],
                "reuse_feedback": "reused successfully",
                "confidence": 0.9,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(payload))
            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        self.assertIn("quality_summary", data)
        self.assertGreaterEqual(data["quality_summary"]["scored_records"], 1)
        self.assertGreaterEqual(data["quality_summary"]["high_value_records"], 1)
        high_value_ids = {item["record_id"] for item in data["high_value_records"]}
        self.assertIn(1, high_value_ids)

    def test_maintain_health_includes_runtime_performance_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()

            self.run_memory(project, "init")
            self.run_memory(project, "context", "--query", "no matching memory", "--json")
            self.run_memory(project, "maintain-plan", "--json")
            result = self.run_memory(project, "maintain-health", "--json")
            data = json.loads(result.stdout)

        self.assertIn("runtime_performance", data)
        self.assertGreaterEqual(data["runtime_performance"]["sample_count"], 1)
        self.assertIn("context", data["runtime_performance"]["operations"])
        self.assertIn("maintain-plan", data["runtime_performance"]["operations"])
