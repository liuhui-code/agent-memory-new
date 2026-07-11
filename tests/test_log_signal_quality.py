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


class LogSignalQualityTests(unittest.TestCase):
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

    def test_rich_runtime_event_scores_good(self) -> None:
        from tools.agent_memory_runtime.log_signal_quality import score_log_signal
        from tools.agent_memory_runtime.runtime_logs import normalize_runtime_log_line

        event = normalize_runtime_log_line(
            "07-11 12:00:00.100 com.demo.app E Router: [Route] stage=failed route=pages/Profile request_id=req-1 session_id=sess-1 reason=target_missing code=404 result=failed",
            1,
        )
        result = score_log_signal(event)

        self.assertEqual("good", result["log_signal_band"])
        self.assertGreaterEqual(result["log_signal_score"], 0.75)
        self.assertIn("route_or_resource", result["present_signals"])
        self.assertNotIn("request_or_session_id", result["missing_signals"])

    def test_generic_failed_log_scores_poor(self) -> None:
        from tools.agent_memory_runtime.log_signal_quality import score_log_signal
        from tools.agent_memory_runtime.runtime_logs import normalize_runtime_log_line

        result = score_log_signal(normalize_runtime_log_line("failed", 1))

        self.assertEqual("poor", result["log_signal_band"])
        self.assertLess(result["log_signal_score"], 0.55)
        self.assertIn("reason", result["missing_signals"])
        self.assertIn("request_id", result["suggested_log_fields"])

    def test_route_error_without_target_reports_missing_route_and_reason(self) -> None:
        from tools.agent_memory_runtime.log_signal_quality import score_log_signal
        from tools.agent_memory_runtime.runtime_logs import normalize_runtime_log_line

        event = normalize_runtime_log_line(
            "07-11 12:00:00.100 com.demo.app E Router: [Route] stage=failed result=failed",
            1,
        )
        result = score_log_signal(event)

        self.assertIn("route_or_resource", result["missing_signals"])
        self.assertIn("reason", result["missing_signals"])
        self.assertIn("route", result["suggested_log_fields"])
        self.assertIn("reason", result["suggested_log_fields"])

    def test_analyze_runtime_log_adds_signal_summary_and_low_signal_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Profile.ets").write_text(
                "import hilog from '@ohos.hilog';\n"
                "struct ProfilePage {\n"
                "  aboutToAppear() {\n"
                "    hilog.error(0x0000, 'ProfilePage', 'load profile failed');\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", "pages")
            runtime_log = project / "runtime.log"
            runtime_log.write_text(
                "failed\n"
                "07-11 12:00:00.100 EntryAbility E ProfilePage: load profile failed code=401 request_id=req-1 session_id=sess-1 reason=session_invalid\n",
                encoding="utf-8",
            )

            result = self.run_memory(
                project,
                "analyze-runtime-log",
                "--query",
                "Profile load failed log",
                "--log-file",
                str(runtime_log),
                "--json",
            )
            data = json.loads(result.stdout)

        self.assertIn("log_signal_summary", data)
        self.assertIn("low_signal_events", data)
        self.assertGreaterEqual(data["log_signal_summary"]["event_count"], 2)
        self.assertTrue(any(event["log_signal_band"] == "poor" for event in data["low_signal_events"]))
        self.assertTrue(any("log_signal_score" in event for event in data["matched_events"]))

    def test_context_code_log_matches_include_signal_quality(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Profile.ets").write_text(
                "import hilog from '@ohos.hilog';\n"
                "struct ProfilePage {\n"
                "  aboutToAppear() {\n"
                "    hilog.error(0x0000, 'ProfilePage', 'load profile failed');\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", "pages")
            result = self.run_memory(project, "context", "--query", "load profile failed", "--json")
            data = json.loads(result.stdout)

        self.assertTrue(data["code_log_matches"])
        log_match = data["code_log_matches"][0]
        self.assertIn("log_signal_score", log_match)
        self.assertIn("log_signal_band", log_match)
        self.assertIn("missing_signals", log_match)


if __name__ == "__main__":
    unittest.main()
