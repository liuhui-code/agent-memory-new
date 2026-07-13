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


class QualityGateHistoryTests(unittest.TestCase):
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

    def write_bad_log_case(self, cases_dir: Path) -> None:
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

    def test_eval_quality_history_reports_recurring_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases_dir = root / "eval"
            project.mkdir()
            cases_dir.mkdir()
            self.write_bad_log_case(cases_dir)

            self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--json")
            self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--json")
            result = self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--history", "--gate", "log_signal", "--json")
            data = json.loads(result.stdout)

        self.assertEqual(2, data["summary"]["run_count"])
        self.assertEqual(["log_signal"], data["summary"]["recurring_failed_gate_names"])
        self.assertEqual(2, data["summary"]["failed_gate_counts"]["log_signal"])
        self.assertEqual(["log_signal"], data["gate_filter"])

    def test_maintain_plan_reviews_recurring_quality_gate_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases_dir = root / "eval"
            project.mkdir()
            cases_dir.mkdir()
            self.write_bad_log_case(cases_dir)

            self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--json")
            self.run_memory(project, "eval-quality", "--cases-dir", str(cases_dir), "--json")
            plan = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)

        actions = [action for action in plan["actions"] if action["action"] == "review_recurring_quality_gate_failure"]
        self.assertEqual(1, len(actions))
        self.assertEqual("quality_gate", actions[0]["governance_lane"])
        self.assertEqual(["log_signal"], actions[0]["recurring_failed_gate_names"])
        self.assertTrue(any("eval-log-signal" in item for item in actions[0]["next_command_templates"]))
        self.assertEqual(1, plan["governance_summary"]["recurring_quality_gate_failure_reviews"])


if __name__ == "__main__":
    unittest.main()
