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


class RetrievalEvalTests(unittest.TestCase):
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
        path = root / "golden-cases.json"
        path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def test_eval_retrieval_reports_expected_hits_and_blocks_bad_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            project.mkdir()
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
                "experience_type": "correction_experience",
                "task": "Old ArkTS route guess",
                "summary": "Old broad route advice.",
                "lesson": "Try broad route checks.",
                "old_hypothesis": "all ArkTS blank screens are resource issues",
                "corrected_understanding": "route blank screens should inspect router target first",
                "correction_scope": "ArkTS route diagnosis",
                "trigger_condition": "ArkTS route blank screen",
                "anti_pattern": "treating every blank screen as a resource issue",
                "repair_action": "try broad route checks",
                "verification_method": "not verified",
                "source_cases": ["old_case:1"],
                "reuse_feedback": "misleading",
                "confidence": 0.4,
                "misleading_score": 0.6,
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(strong_payload))
            self.run_memory(project, "reflect", "--payload", json.dumps(weak_payload))
            case_file = self.write_cases(
                root,
                [
                    {
                        "name": "arkts-route-blank-screen",
                        "query": "ArkTS route blank screen 如何定位",
                        "expected": [
                            {"type": "reflections", "id": 1},
                            {"type": "reflections", "text": "router.pushUrl"},
                        ],
                        "must_not_include": [
                            {"type": "reflections", "id": 2},
                        ],
                    }
                ],
            )

            result = self.run_memory(project, "eval-retrieval", "--cases", str(case_file), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("pass", data["quality_gate"])
        self.assertEqual(1, data["summary"]["case_count"])
        self.assertEqual(1.0, data["summary"]["expected_hit_rate"])
        self.assertEqual(1.0, data["summary"]["blocked_bad_rate"])
        self.assertEqual([], data["cases"][0]["missed_expected"])
        self.assertEqual([], data["cases"][0]["unexpected_bad_matches"])

    def test_eval_retrieval_reports_missed_expected_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            project.mkdir()
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "ArkTS route issues are diagnosed through router.pushUrl targets.",
                "--source",
                "test",
                "--confidence",
                "0.9",
            )
            case_file = self.write_cases(
                root,
                [
                    {
                        "name": "missing-reflection",
                        "query": "ArkTS route blank screen",
                        "expected": [
                            {"type": "reflections", "text": "router.pushUrl"},
                        ],
                    }
                ],
            )

            result = self.run_memory(project, "eval-retrieval", "--cases", str(case_file), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("fail", data["quality_gate"])
        self.assertEqual(0.0, data["summary"]["expected_hit_rate"])
        self.assertEqual(1, len(data["cases"][0]["missed_expected"]))

    def test_eval_retrieval_reports_top_anchor_rank_and_experience_noise(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            project.mkdir()
            exact_payload = {
                "experience_type": "procedure_experience",
                "task": "ArkTS Profile route blank screen",
                "summary": "Profile route mismatch verified.",
                "lesson": "Inspect pages/Profile route registration first.",
                "trigger_condition": "ArkTS Profile route blank screen",
                "repair_action": "inspect pages/Profile route registration",
                "verification_method": "ran navigation test",
                "source_cases": ["incident_trace:31"],
                "negative_preconditions": ["does not apply to image resource failures"],
                "confidence": 0.92,
            }
            noisy_payload = {
                "experience_type": "procedure_experience",
                "task": "Generic blank screen cleanup habit",
                "summary": "Clean build cache for every blank screen.",
                "lesson": "Clean build cache first.",
                "trigger_condition": "blank screen",
                "repair_action": "clean build cache",
                "verification_method": "old one-off run",
                "source_cases": ["old_case:1"],
                "confidence": 0.95,
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(exact_payload))
            self.run_memory(project, "reflect", "--payload", json.dumps(noisy_payload))
            case_file = self.write_cases(
                root,
                [
                    {
                        "name": "exact-profile-route-first",
                        "query": "ArkTS Profile route blank screen 报错如何定位",
                        "expected_top": [
                            {"type": "reflections", "id": 1},
                        ],
                        "noise": [
                            {"type": "reflections", "id": 2},
                        ],
                    }
                ],
            )

            result = self.run_memory(project, "eval-retrieval", "--cases", str(case_file), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("pass", data["quality_gate"])
        self.assertEqual(1, data["summary"]["exact_anchor_rank"])
        self.assertEqual(0.0, data["summary"]["experience_noise_rate"])
        self.assertEqual([1], data["cases"][0]["expected_top_ranks"])
        self.assertEqual([], data["cases"][0]["unexpected_noise_matches"])
