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


class ActiveLearningQueueTests(unittest.TestCase):
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
            "task": "ArkTS route blank screen broad diagnosis",
            "summary": "Broad route diagnosis.",
            "lesson": "Inspect routes broadly.",
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "inspect broad route files",
            "verification_method": "old manual case",
            "source_cases": ["old_case:route"],
            "confidence": 0.7,
        }
        self.run_memory(project, "reflect", "--payload", json.dumps(payload))

    def seed_weak_graph_signal(self, project: Path) -> None:
        from tools.agent_memory_runtime.storage import connect, resolve_project

        runtime_project = resolve_project(str(project), str(self.memory_home(project)))
        with connect(runtime_project) as conn:
            conn.execute(
                """
                INSERT INTO code_log_statements(
                  project_id, file_path, line, function, level, logger, message_template, updated_at
                )
                VALUES (?, 'pages/Profile.ets', 8, 'loadProfile', 'error', 'ProfilePage',
                        'load profile failed', '2026-07-12T00:00:00Z')
                """,
                (runtime_project.project_id,),
            )
            conn.commit()

    def seed_query_miss(self, project: Path) -> None:
        from tools.agent_memory_runtime.storage import connect, resolve_project

        runtime_project = resolve_project(str(project), str(self.memory_home(project)))
        with connect(runtime_project) as conn:
            conn.execute(
                """
                INSERT INTO query_misses(
                  project_id, query, normalized_query, source, result_counts,
                  created_at, last_seen_at, miss_count, status
                )
                VALUES (?, 'zzzz-no-memory-anchor-123', 'zzzz-no-memory-anchor-123',
                        'context', '{}', '2026-07-12T00:00:00Z',
                        '2026-07-12T00:01:00Z', 2, 'open')
                """,
                (runtime_project.project_id,),
            )
            conn.commit()

    def seed_queue_signals(self, project: Path) -> None:
        self.run_memory(project, "init")
        self.seed_reflection(project)
        self.seed_weak_graph_signal(project)
        self.seed_query_miss(project)
        self.run_memory(
            project,
            "experience-usage",
            "--query",
            "ArkTS route blank screen 如何定位",
            "--type",
            "reflection",
            "--id",
            "1",
            "--outcome",
            "misleading",
            "--verified",
            "--json",
        )

    def test_maintain_health_reports_active_learning_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_queue_signals(project)

            result = self.run_memory(project, "maintain-health", "--json")
            data = json.loads(result.stdout)

        queue = data["active_learning_queue"]
        self.assertGreaterEqual(queue["queue_count"], 3)
        self.assertGreater(queue["top_priority_score"], 0)
        self.assertGreaterEqual(queue["lanes"]["experience_usage"], 1)
        self.assertGreaterEqual(queue["lanes"]["query_miss"], 1)
        self.assertGreaterEqual(queue["lanes"]["graph_signal"], 1)
        self.assertEqual("experience_usage", queue["top_items"][0]["lane"])

    def test_maintain_plan_emits_active_learning_queue_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_queue_signals(project)

            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        queue = data["active_learning_queue"]
        actions = [action for action in data["actions"] if action["action"] == "review_active_learning_queue"]
        self.assertGreaterEqual(data["governance_summary"]["active_learning_queue_items"], 3)
        self.assertEqual(len(queue["top_items"]), len(actions))
        self.assertTrue(all(action["command"] is None for action in actions))
        self.assertEqual(actions[0]["queue_item"]["lane"], queue["top_items"][0]["lane"])


if __name__ == "__main__":
    unittest.main()
