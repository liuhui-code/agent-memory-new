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


class ExperienceEvidenceEvalTests(unittest.TestCase):
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

    def test_eval_experience_evidence_passes_complete_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases = root / "golden-experience-evidence.json"
            project.mkdir()
            payload = {
                "experience_type": "procedure_experience",
                "task": "ArkTS route blank screen diagnosis",
                "summary": "Route target mismatch diagnosis.",
                "lesson": "Inspect router.pushUrl target and page registration first.",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "verification_method": "ran route navigation test",
                "source_cases": ["incident_trace:7"],
                "negative_preconditions": ["does not apply to pure resource failures"],
                "confidence": 0.9,
            }
            cases.write_text(
                json.dumps(
                    [
                        {
                            "name": "complete-route-procedure",
                            "match": {"text": "router.pushUrl"},
                            "min_profile_score": 1.0,
                            "expected_verification_status": "verified",
                            "required_true": ["has_evidence", "has_applicability", "has_counter_evidence"],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.run_memory(project, "reflect", "--payload", json.dumps(payload))
            result = self.run_memory(project, "eval-experience-evidence", "--cases", str(cases), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("pass", data["quality_gate"])
        self.assertEqual(1.0, data["summary"]["average_profile_score"])
        self.assertEqual("verified", data["cases"][0]["verification_status"])

    def test_eval_experience_evidence_fails_missing_counter_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases = root / "golden-experience-evidence.json"
            project.mkdir()
            payload = {
                "experience_type": "procedure_experience",
                "task": "ArkTS route blank screen diagnosis",
                "summary": "Route target mismatch diagnosis.",
                "lesson": "Inspect router.pushUrl target.",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "verification_method": "ran route navigation test",
                "source_cases": ["incident_trace:7"],
                "confidence": 0.9,
            }
            cases.write_text(
                json.dumps(
                    [
                        {
                            "name": "missing-counter-evidence",
                            "match": {"text": "router.pushUrl"},
                            "min_profile_score": 1.0,
                            "required_true": ["has_counter_evidence"],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.run_memory(project, "reflect", "--payload", json.dumps(payload))
            result = self.run_memory(project, "eval-experience-evidence", "--cases", str(cases), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("fail", data["quality_gate"])
        self.assertIn("has_counter_evidence", data["cases"][0]["missing_required_true"])


if __name__ == "__main__":
    unittest.main()
