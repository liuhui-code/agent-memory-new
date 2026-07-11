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


class GraphQualityTests(unittest.TestCase):
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

    def seed_graph_quality_fixture(self, project: Path) -> None:
        from tools.agent_memory_runtime.storage import connect, resolve_project

        runtime_project = resolve_project(str(project), str(self.memory_home(project)))
        with connect(runtime_project) as conn:
            conn.execute(
                """
                INSERT INTO code_files(project_id, file_path, summary, language, updated_at)
                VALUES (?, 'pages/Home.ets', 'Home page', 'ArkTS', '2026-07-11T00:00:00Z')
                """,
                (runtime_project.project_id,),
            )
            symbol = conn.execute(
                """
                INSERT INTO code_symbols(project_id, file_path, symbol, symbol_type, summary, updated_at)
                VALUES (?, 'pages/Home.ets', 'openProfile', 'function', 'opens profile', '2026-07-11T00:00:00Z')
                """,
                (runtime_project.project_id,),
            )
            conn.execute(
                """
                INSERT INTO code_log_statements(
                  project_id, file_path, line, function, level, logger, message_template, updated_at
                )
                VALUES (?, 'pages/Home.ets', 12, 'openProfile', 'error', 'console',
                        'router.pushUrl failed', '2026-07-11T00:00:00Z')
                """,
                (runtime_project.project_id,),
            )
            conn.execute(
                """
                INSERT INTO memory_edges(
                  project_id, source_type, source_id, relation, target_type, target_id,
                  evidence, confidence, created_at
                )
                VALUES (?, 'code_file', 1, 'contains', 'code_symbol', ?, 'file contains symbol',
                        0.95, '2026-07-11T00:00:00Z')
                """,
                (runtime_project.project_id, int(symbol.lastrowid)),
            )
            conn.execute(
                """
                INSERT INTO memory_edges(
                  project_id, source_type, source_id, relation, target_type, target_id,
                  evidence, confidence, created_at
                )
                VALUES (?, 'code_symbol', ?, 'emits_log', 'code_log_statement', 9999,
                        'stale log edge', 0.2, '2026-07-11T00:00:00Z')
                """,
                (runtime_project.project_id, int(symbol.lastrowid)),
            )
            conn.commit()

    def test_maintain_health_reports_graph_quality(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            self.seed_graph_quality_fixture(project)

            result = self.run_memory(project, "maintain-health", "--json")
            data = json.loads(result.stdout)

        graph = data["graph_quality"]
        self.assertEqual(1, graph["orphan_code_logs"])
        self.assertEqual(1, graph["stale_edges"])
        self.assertEqual(1, graph["low_confidence_edges"])
        self.assertEqual("poor", graph["health_status"])

    def test_maintain_plan_reviews_graph_quality(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            self.seed_graph_quality_fixture(project)

            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        actions = [action for action in data["actions"] if action["action"] == "review_graph_quality"]
        self.assertEqual(1, len(actions))
        self.assertEqual("graph_quality", actions[0]["type"])
        self.assertEqual(1, data["governance_summary"]["graph_quality_reviews"])

    def test_maintain_health_reports_graph_signal_quality_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            self.seed_graph_quality_fixture(project)

            result = self.run_memory(project, "maintain-health", "--json")
            data = json.loads(result.stdout)

        signal = data["graph_signal_quality"]
        self.assertGreaterEqual(signal["weak_anchor_count"], 1)
        self.assertGreaterEqual(signal["missing_business_semantics"], 1)
        self.assertGreaterEqual(signal["missing_log_signal_fields"], 1)
        self.assertTrue(signal["top_repair_targets"])
        self.assertEqual("code_log_statement", signal["top_repair_targets"][0]["target_type"])
        self.assertIn("suggested_fields", signal["top_repair_targets"][0])

    def test_maintain_plan_reviews_graph_signal_quality(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            self.seed_graph_quality_fixture(project)

            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        actions = [action for action in data["actions"] if action["action"] == "review_graph_signal_quality"]
        self.assertEqual(1, len(actions))
        self.assertEqual("graph_signal_quality", actions[0]["type"])
        self.assertTrue(actions[0]["graph_signal_quality"]["top_repair_targets"])
        self.assertEqual(1, data["governance_summary"]["graph_signal_quality_reviews"])
