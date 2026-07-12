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


class MemoryTierTests(unittest.TestCase):
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

    def seed_tier_records(self, project: Path) -> None:
        from tools.agent_memory_runtime.storage import connect, resolve_project

        runtime_project = resolve_project(str(project), str(self.memory_home(project)))
        with connect(runtime_project) as conn:
            conn.execute(
                """
                INSERT INTO semantic_facts(
                  project_id, fact, source, confidence, status, use_count, created_at, updated_at
                )
                VALUES (?, 'Low confidence unused fact', 'test', 0.3, 'active', 0,
                        '2026-07-12T00:00:00Z', '2026-07-12T00:00:00Z')
                """,
                (runtime_project.project_id,),
            )
            conn.execute(
                """
                INSERT INTO reflections(
                  project_id, task, lesson, status, confidence, use_count, last_used_at, created_at
                )
                VALUES (?, 'Hot route diagnosis', 'Use exact route anchors first.', 'active',
                        0.9, 3, '2026-07-12T00:02:00Z', '2026-07-12T00:00:00Z')
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
            conn.commit()

    def test_maintain_health_reports_memory_tiers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            self.seed_tier_records(project)

            result = self.run_memory(project, "maintain-health", "--json")
            data = json.loads(result.stdout)

        tiers = data["memory_tiers"]
        self.assertGreaterEqual(tiers["counts"]["hot"], 1)
        self.assertGreaterEqual(tiers["counts"]["cold"], 1)
        self.assertGreaterEqual(tiers["counts"]["archive_candidate"], 1)
        self.assertTrue(tiers["review_targets"])

    def test_maintain_plan_reviews_memory_tiers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            self.seed_tier_records(project)

            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        actions = [action for action in data["actions"] if action["action"] == "review_memory_tier"]
        self.assertGreaterEqual(len(actions), 2)
        self.assertGreaterEqual(data["governance_summary"]["memory_tier_reviews"], 2)
        self.assertTrue(any(action["tier"] == "archive_candidate" for action in actions))
        self.assertTrue(any(action["tier"] == "cold" for action in actions))


if __name__ == "__main__":
    unittest.main()
