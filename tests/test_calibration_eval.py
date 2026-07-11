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


class CalibrationEvalTests(unittest.TestCase):
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

    def write_cases(self, root: Path, cases: list[dict]) -> Path:
        path = root / "calibration-cases.json"
        path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def seed_reflections(self, project: Path) -> None:
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
        weak_payload = {
            "experience_type": "procedure_experience",
            "task": "Old ArkTS route guess",
            "summary": "Old broad route advice.",
            "lesson": "Try broad route checks.",
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "try broad route checks",
            "verification_method": "not verified",
            "source_cases": ["old_case:1"],
            "reuse_feedback": "misleading",
            "confidence": 0.35,
            "misleading_score": 0.8,
        }
        self.run_memory(project, "reflect", "--payload", json.dumps(strong_payload))
        self.run_memory(project, "reflect", "--payload", json.dumps(weak_payload))

    def test_eval_calibration_passes_expected_trust_and_blocks_overtrust(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            project.mkdir()
            self.seed_reflections(project)
            case_file = self.write_cases(
                root,
                [
                    {
                        "name": "arkts-route-trust",
                        "query": "ArkTS route blank screen 如何定位",
                        "expected_trust": [
                            {
                                "type": "reflections",
                                "id": 1,
                                "trust_level": "verified_experience",
                                "min_trust_score": 0.75,
                            }
                        ],
                        "must_not_trust": [
                            {
                                "type": "reflections",
                                "id": 2,
                                "trust_levels": ["verified_experience", "source_truth"],
                            }
                        ],
                    }
                ],
            )

            result = self.run_memory(project, "eval-calibration", "--cases", str(case_file), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("pass", data["quality_gate"])
        self.assertEqual(1.0, data["summary"]["expected_trust_rate"])
        self.assertEqual(1.0, data["summary"]["blocked_overtrust_rate"])
        self.assertEqual([], data["cases"][0]["missed_expected_trust"])
        self.assertEqual([], data["cases"][0]["unexpected_trusted_matches"])

    def test_eval_calibration_reports_missing_expected_trust(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            project.mkdir()
            self.seed_reflections(project)
            case_file = self.write_cases(
                root,
                [
                    {
                        "name": "missing-source-truth",
                        "query": "ArkTS route blank screen 如何定位",
                        "expected_trust": [
                            {
                                "type": "reflections",
                                "id": 1,
                                "trust_level": "source_truth",
                                "min_trust_score": 0.95,
                            }
                        ],
                    }
                ],
            )

            result = self.run_memory(project, "eval-calibration", "--cases", str(case_file), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("fail", data["quality_gate"])
        self.assertEqual(0.0, data["summary"]["expected_trust_rate"])
        self.assertEqual(1, len(data["cases"][0]["missed_expected_trust"]))


if __name__ == "__main__":
    unittest.main()
