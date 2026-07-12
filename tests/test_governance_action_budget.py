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


class GovernanceActionBudgetTests(unittest.TestCase):
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

    def seed_actions(self, project: Path) -> None:
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
            conn.execute(
                """
                INSERT INTO reflections(
                  project_id, task, lesson, status, confidence, use_count, created_at
                )
                VALUES (?, 'Stale broad route advice', 'Inspect every route file.', 'stale',
                        0.5, 0, '2026-07-12T00:00:00Z')
                """,
                (runtime_project.project_id,),
            )
            conn.execute(
                """
                INSERT INTO query_misses(
                  project_id, query, normalized_query, source, result_counts,
                  created_at, last_seen_at, miss_count, status
                )
                VALUES (?, 'zzzz-no-memory-anchor-456', 'zzzz-no-memory-anchor-456',
                        'context', '{}', '2026-07-12T00:00:00Z',
                        '2026-07-12T00:01:00Z', 3, 'open')
                """,
                (runtime_project.project_id,),
            )
            conn.commit()

    def test_maintain_plan_reports_action_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            self.seed_actions(project)

            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        budget = data["action_budget"]
        self.assertGreaterEqual(budget["total_actions"], 3)
        self.assertGreaterEqual(budget["requires_confirmation"], 2)
        self.assertGreaterEqual(budget["counts_by_lane"]["memory_tiers"], 2)
        self.assertGreaterEqual(budget["counts_by_lane"]["log_diagnosis"], 1)
        self.assertTrue(budget["top_actions"])
        self.assertTrue(all("priority_score" in action for action in data["actions"]))
        self.assertTrue(all("priority_reasons" in action for action in data["actions"]))
        self.assertGreaterEqual(
            budget["top_actions"][0]["priority_score"],
            budget["top_actions"][-1]["priority_score"],
        )
        self.assertEqual(budget, data["governance_summary"]["action_budget"])

    def test_maintain_plan_compact_returns_budget_first_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            self.seed_actions(project)

            result = self.run_memory(project, "maintain-plan", "--compact", "--json")
            data = json.loads(result.stdout)

        self.assertTrue(data["compact"])
        self.assertIn("action_budget", data)
        self.assertIn("health_overview", data)
        self.assertEqual(data["actions"], data["action_budget"]["top_actions"])
        self.assertLessEqual(len(data["actions"]), data["action_budget"]["top_limit"])
        self.assertIn("memory_tier_counts", data["health_overview"])
        self.assertIn("active_learning_queue_count", data["health_overview"])
        self.assertNotIn("low_quality_records", data)
        self.assertNotIn("high_value_records", data)

    def test_maintain_plan_action_limit_controls_budget_batch_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            self.seed_actions(project)

            result = self.run_memory(project, "maintain-plan", "--compact", "--action-limit", "1", "--json")
            data = json.loads(result.stdout)

        self.assertEqual(1, data["action_budget"]["top_limit"])
        self.assertEqual(1, len(data["action_budget"]["top_actions"]))
        self.assertEqual(1, len(data["actions"]))


if __name__ == "__main__":
    unittest.main()
