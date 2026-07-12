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


class GraphSignalEvalTests(unittest.TestCase):
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

    def test_eval_graph_signal_passes_expected_weak_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases = root / "golden-graph-signal.json"
            project.mkdir()
            pages = project / "pages"
            pages.mkdir()
            (pages / "Profile.ets").write_text(
                "export function loadProfile() {\n"
                "  console.error('profile failed');\n"
                "}\n",
                encoding="utf-8",
            )
            cases.write_text(
                json.dumps(
                    [
                        {
                            "name": "weak-profile-log-target",
                            "min_coverage_score": 0.0,
                            "allowed_coverage_statuses": ["watch", "poor"],
                            "max_repair_targets": 5,
                            "required_repair_targets": [
                                {"target_type": "code_log_statement", "text": "profile failed"}
                            ],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")
            result = self.run_memory(project, "eval-graph-signal", "--cases", str(cases), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("pass", data["quality_gate"])
        self.assertEqual(1, data["summary"]["passed_cases"])
        self.assertIn("coverage_scorecard", data["graph_signal_quality"])
        self.assertEqual([], data["cases"][0]["missing_required_repair_targets"])

    def test_eval_graph_signal_fails_missing_required_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            cases = root / "golden-graph-signal.json"
            project.mkdir()
            cases.write_text(
                json.dumps(
                    [
                        {
                            "name": "missing-target",
                            "min_coverage_score": 0.0,
                            "required_repair_targets": [
                                {"target_type": "code_log_statement", "text": "profile failed"}
                            ],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_memory(project, "eval-graph-signal", "--cases", str(cases), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("fail", data["quality_gate"])
        self.assertEqual(1, data["summary"]["failed_cases"])
        self.assertEqual(1, len(data["cases"][0]["missing_required_repair_targets"]))


if __name__ == "__main__":
    unittest.main()
