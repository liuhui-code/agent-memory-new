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
        calibration = next(gate for gate in data["gates"] if gate["name"] == "calibration")
        self.assertEqual("skipped", calibration["status"])

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
        log_gate = next(gate for gate in data["gates"] if gate["name"] == "log_signal")
        self.assertEqual("fail", log_gate["status"])

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


if __name__ == "__main__":
    unittest.main()
