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


class MemoryCalibrationTests(unittest.TestCase):
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

    def test_verified_reflection_calibrates_as_verified_experience(self) -> None:
        from tools.agent_memory_runtime.memory_calibration import calibrate_record

        item = {
            "id": 1,
            "experience_type": "procedure_experience",
            "memory_lane": "reusable_procedure",
            "confidence": 0.92,
            "quality_score": 0.86,
            "verification_method": "ran targeted test",
            "source_cases": ["incident_trace:7"],
            "gate_reasons": ["procedure_lane_matches_intent"],
        }

        calibrated = calibrate_record("reflections", item)

        self.assertEqual("verified_experience", calibrated["trust_level"])
        self.assertGreaterEqual(calibrated["trust_score"], 0.75)
        self.assertIn("verified", " ".join(calibrated["trust_reasons"]))
        self.assertEqual("reflections", calibrated["retrieval_explanation"]["group"])

    def test_stale_feedback_penalized_record_calibrates_as_possibly_stale(self) -> None:
        from tools.agent_memory_runtime.memory_calibration import calibrate_record

        item = {
            "id": 2,
            "confidence": 0.35,
            "quality_score": 0.3,
            "status": "stale",
            "is_stale": 1,
            "feedback_penalty": 35,
            "feedback_reasons": ["misleading"],
        }

        calibrated = calibrate_record("reflections", item)

        self.assertEqual("possibly_stale", calibrated["trust_level"])
        self.assertLess(calibrated["trust_score"], 0.5)
        self.assertIn("stale", " ".join(calibrated["trust_reasons"]))
        self.assertIn("feedback penalty", " ".join(calibrated["trust_reasons"]))

    def test_context_output_includes_memory_policy_and_calibrated_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            payload = {
                "experience_type": "procedure_experience",
                "task": "Diagnose ArkTS route blank screen",
                "summary": "Route target mismatch was verified.",
                "lesson": "Inspect router.pushUrl target and page registration first.",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "verification_method": "ran route navigation test",
                "source_cases": ["incident_trace:1"],
                "reuse_feedback": "reused successfully",
                "confidence": 0.95,
            }

            self.run_memory(project, "init")
            self.run_memory(project, "reflect", "--payload", json.dumps(payload))
            result = self.run_memory(project, "context", "--query", "ArkTS route blank screen", "--json")
            data = json.loads(result.stdout)

        self.assertIn("memory_use_policy", data)
        self.assertEqual("advisory", data["memory_use_policy"]["mode"])
        self.assertGreaterEqual(len(data["reflections"]), 1)
        first = data["reflections"][0]
        self.assertIn("trust_level", first)
        self.assertIn("trust_reasons", first)
        self.assertIn("retrieval_explanation", first)
        self.assertIn("experience_evidence_profile", first)
        self.assertTrue(first["experience_evidence_profile"]["has_evidence"])
        self.assertEqual("verified", first["experience_evidence_profile"]["verification_status"])
        self.assertIn("experience_evidence_profile", first["retrieval_explanation"])
        self.assertIn(first["trust_level"], {"verified_experience", "usable_hint"})


if __name__ == "__main__":
    unittest.main()
