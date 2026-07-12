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


class QualityGateEvalTests(unittest.TestCase):
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

    def test_eval_quality_runs_available_gates_and_skips_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases_dir = root / "eval"
            project.mkdir()
            cases_dir.mkdir()
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
            (cases_dir / "golden-retrieval.json").write_text(
                json.dumps(
                    [
                        {
                            "name": "route-anchor",
                            "query": "ArkTS route diagnosis",
                            "expected": [{"type": "semantic_facts", "text": "router.pushUrl"}],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (cases_dir / "golden-log-signal.json").write_text(
                json.dumps(
                    [
                        {
                            "name": "good-log",
                            "logs": [
                                "07-11 12:00:00.100 EntryAbility E Router: event=route_failed route=pages/Profile request_id=req-1 reason=target_missing result=failed"
                            ],
                            "min_good_rate": 1.0,
                            "max_low_signal_rate": 0.0,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("pass", data["quality_gate"])
        self.assertEqual(2, data["summary"]["gate_count"])
        self.assertEqual(2, data["summary"]["passed_gates"])
        self.assertEqual(3, data["summary"]["skipped_gates"])
        self.assertEqual(["retrieval", "log_signal"], data["summary"]["passed_gate_names"])
        self.assertEqual([], data["summary"]["failed_gate_names"])
        calibration = next(gate for gate in data["gates"] if gate["name"] == "calibration")
        self.assertEqual("skipped", calibration["status"])
        self.assertIn("eval-calibration", calibration["next_command_template"])

    def test_eval_quality_fails_when_available_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases_dir = root / "eval"
            project.mkdir()
            cases_dir.mkdir()
            (cases_dir / "golden-log-signal.json").write_text(
                json.dumps(
                    [
                        {
                            "name": "bad-log",
                            "logs": ["failed"],
                            "min_good_rate": 1.0,
                            "max_low_signal_rate": 0.0,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("fail", data["quality_gate"])
        self.assertEqual(1, data["summary"]["failed_gates"])
        self.assertEqual(["log_signal"], data["summary"]["failed_gate_names"])
        log_gate = next(gate for gate in data["gates"] if gate["name"] == "log_signal")
        self.assertEqual("fail", log_gate["status"])
        self.assertIn("eval-log-signal", log_gate["next_command_template"])

    def test_eval_quality_strict_fails_when_no_cases_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases_dir = root / "eval"
            project.mkdir()
            cases_dir.mkdir()

            result = self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--strict", "--json")
            data = json.loads(result.stdout)

        self.assertEqual("fail", data["quality_gate"])
        self.assertEqual("no_case_files", data["summary"]["failure_reason"])

    def test_eval_quality_fail_on_fail_returns_nonzero_with_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases_dir = root / "eval"
            project.mkdir()
            cases_dir.mkdir()
            (cases_dir / "golden-log-signal.json").write_text(
                json.dumps(
                    [
                        {
                            "name": "bad-log",
                            "logs": ["failed"],
                            "min_good_rate": 1.0,
                            "max_low_signal_rate": 0.0,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            command = [
                sys.executable,
                str(RUNTIME),
                "eval-quality",
                "--cases-dir",
                str(cases_dir),
                "--fail-on-fail",
                "--json",
                "--project",
                str(project),
                "--memory-home",
                str(self.memory_home(project)),
            ]

            result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, env=os.environ.copy())
            data = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        self.assertEqual("fail", data["quality_gate"])
        self.assertEqual(["log_signal"], data["summary"]["failed_gate_names"])

    def test_maintain_health_reports_latest_quality_gate_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases_dir = root / "eval"
            project.mkdir()
            cases_dir.mkdir()
            (cases_dir / "golden-log-signal.json").write_text(
                json.dumps(
                    [
                        {
                            "name": "bad-log",
                            "logs": ["failed"],
                            "min_good_rate": 1.0,
                            "max_low_signal_rate": 0.0,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--json")
            health = json.loads(self.run_memory(project, "maintain-health", "--json").stdout)

        self.assertEqual("fail", health["last_quality_gate"]["quality_gate"])
        self.assertEqual(["log_signal"], health["last_quality_gate"]["summary"]["failed_gate_names"])
        self.assertTrue(
            any("quality gate" in action.lower() for action in health["recommended_actions"])
        )

    def test_maintain_plan_reviews_latest_quality_gate_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases_dir = root / "eval"
            project.mkdir()
            cases_dir.mkdir()
            (cases_dir / "golden-log-signal.json").write_text(
                json.dumps(
                    [
                        {
                            "name": "bad-log",
                            "logs": ["failed"],
                            "min_good_rate": 1.0,
                            "max_low_signal_rate": 0.0,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--json")
            plan = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)

        actions = [action for action in plan["actions"] if action["action"] == "review_quality_gate_failure"]
        self.assertEqual(1, len(actions))
        self.assertEqual("quality_gate", actions[0]["governance_lane"])
        self.assertEqual(["log_signal"], actions[0]["failed_gate_names"])
        self.assertTrue(any("eval-log-signal" in item for item in actions[0]["next_command_templates"]))
        self.assertEqual(1, plan["governance_summary"]["quality_gate_failure_reviews"])


if __name__ == "__main__":
    unittest.main()
