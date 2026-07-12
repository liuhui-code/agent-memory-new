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


class QualityClosedLoopTests(unittest.TestCase):
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

    def seed_reflection(self, project: Path) -> None:
        payload = {
            "experience_type": "procedure_experience",
            "task": "ArkTS route blank screen diagnosis",
            "summary": "Verified route target mismatch diagnosis.",
            "lesson": "Check router.pushUrl target against page registration first.",
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "compare router.pushUrl target and page registration",
            "verification_method": "verified route reproduction",
            "source_cases": ["incident_trace:route"],
            "confidence": 0.9,
        }
        self.run_memory(project, "reflect", "--payload", json.dumps(payload))

    def test_context_and_search_include_query_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflection(project)

            context = json.loads(
                self.run_memory(project, "context", "--query", "ArkTS route blank screen", "--json").stdout
            )
            search = json.loads(
                self.run_memory(project, "search", "--query", "ArkTS route blank screen", "--json").stdout
            )

        self.assertIn("query_audit", context)
        self.assertIn("query_audit", search)
        self.assertGreaterEqual(context["query_audit"]["result_counts"]["reflections"], 1)
        self.assertTrue(context["query_audit"]["top_explanations"]["reflections"])

    def test_experience_usage_summary_reports_effectiveness_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflection(project)
            self.run_memory(
                project,
                "experience-usage",
                "--query",
                "ArkTS route blank screen",
                "--type",
                "reflection",
                "--id",
                "1",
                "--outcome",
                "helpful",
                "--json",
            )
            self.run_memory(
                project,
                "experience-usage",
                "--query",
                "ArkTS route blank screen",
                "--type",
                "reflection",
                "--id",
                "1",
                "--outcome",
                "misleading",
                "--json",
            )

            health = json.loads(self.run_memory(project, "maintain-health", "--json").stdout)

        record = health["experience_usage"]["records"][0]
        self.assertEqual(2, record["total_count"])
        self.assertEqual(1, record["success_count"])
        self.assertEqual(1, record["failure_count"])
        self.assertIn(record["effectiveness_band"], {"mixed", "strong", "weak"})

    def test_eval_governance_checks_expected_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            project.mkdir()
            self.run_memory(project, "init")
            from tools.agent_memory_runtime.storage import connect, resolve_project

            runtime_project = resolve_project(str(project), str(self.memory_home(project)))
            with connect(runtime_project) as conn:
                conn.execute(
                    """
                    INSERT INTO semantic_facts(
                      project_id, fact, source, confidence, status, use_count, created_at, updated_at
                    )
                    VALUES (?, 'Low confidence unused fact', 'test', 0.2, 'active', 0,
                            '2026-07-12T00:00:00Z', '2026-07-12T00:00:00Z')
                    """,
                    (runtime_project.project_id,),
                )
                conn.commit()
            cases = root / "governance-cases.json"
            cases.write_text(
                json.dumps(
                    [
                        {
                            "name": "memory tier action",
                            "expected_actions": [
                                {"action": "review_memory_tier", "governance_lane": "memory_tiers"}
                            ],
                            "must_not_actions": [
                                {"action": "review_experience_conflict", "governance_lane": "experience_conflict"}
                            ],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_memory(project, "eval-governance", "--cases", str(cases), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("pass", data["quality_gate"])
        self.assertEqual(1.0, data["summary"]["expected_action_hit_rate"])
        self.assertEqual(1.0, data["summary"]["blocked_bad_action_rate"])

    def test_arkts_learn_extracts_state_symbol_and_edge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Profile.ets").write_text(
                "@Entry\n"
                "@Component\n"
                "struct Profile {\n"
                "  @State profileLoaded: boolean = false\n"
                "  build() { Text(String(this.profileLoaded)) }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-entry", "--entry", "pages/Profile.ets", "--json")
            symbols = json.loads(self.run_memory(project, "list", "--type", "code-symbol", "--json").stdout)
            edges = json.loads(self.run_memory(project, "list", "--type", "memory-edge", "--json").stdout)

        self.assertTrue(any(item["symbol"] == "profileLoaded" and item["symbol_type"] == "state" for item in symbols))
        self.assertTrue(any(edge["relation"] == "defines_state" for edge in edges))

    def test_log_signal_reports_observability_gaps(self) -> None:
        from tools.agent_memory_runtime.log_signal_quality import score_log_signal
        from tools.agent_memory_runtime.runtime_logs import normalize_runtime_log_line

        result = score_log_signal(normalize_runtime_log_line("failed", 1))

        self.assertIn("observability_gaps", result)
        self.assertIn("missing_reason", result["observability_gaps"])
        self.assertIn("missing_correlation", result["observability_gaps"])

    def test_maintain_plan_reports_log_observability_gap_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Profile.ets").write_text(
                "function loadProfile() {\n"
                "  console.error('failed')\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-entry", "--entry", "pages/Profile.ets", "--json")
            plan = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)

        actions = plan["actions"]
        self.assertTrue(any(action["action"] == "review_log_observability_gap" for action in actions))


if __name__ == "__main__":
    unittest.main()
