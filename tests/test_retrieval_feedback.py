# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional

from tools.agent_memory_runtime.storage_schema import create_schema


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"


class RetrievalFeedbackTests(unittest.TestCase):
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

    def seed_reflections(self, project: Path) -> None:
        weak_payload = {
            "experience_type": "procedure_experience",
            "task": "ArkTS route blank screen",
            "summary": "Broad route advice.",
            "lesson": "Try broad route checks.",
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "try broad route checks",
            "verification_method": "not verified on current source",
            "source_cases": ["old_case:1"],
            "reuse_feedback": "misleading",
            "confidence": 0.4,
            "misleading_score": 0.4,
        }
        strong_payload = {
            "experience_type": "procedure_experience",
            "task": "ArkTS route blank screen diagnosis",
            "summary": "Verified route target mismatch diagnosis.",
            "lesson": "For ArkTS route blank screen, inspect router.pushUrl target and page registration first.",
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "inspect router.pushUrl target",
            "verification_method": "ran route navigation test",
            "source_cases": ["incident_trace:7"],
            "reuse_feedback": "reused successfully",
            "confidence": 0.95,
        }
        self.run_memory(project, "reflect", "--payload", json.dumps(weak_payload))
        self.run_memory(project, "reflect", "--payload", json.dumps(strong_payload))

    def test_retrieval_feedback_command_writes_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)

            result = self.run_memory(
                project,
                "retrieval-feedback",
                "--query",
                "ArkTS route blank screen 如何定位",
                "--type",
                "reflection",
                "--id",
                "1",
                "--reason",
                "weak_related",
                "--replacement-type",
                "reflection",
                "--replacement-id",
                "2",
                "--json",
            )
            data = json.loads(result.stdout)

        self.assertEqual("reflection", data["record_type"])
        self.assertEqual(1, data["record_id"])
        self.assertEqual("weak_related", data["reason"])

    def test_verified_feedback_penalizes_reflection_for_similar_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)
            self.run_memory(
                project,
                "retrieval-feedback",
                "--query",
                "ArkTS route blank screen 如何定位",
                "--type",
                "reflection",
                "--id",
                "1",
                "--reason",
                "weak_related",
                "--verified",
                "--json",
            )

            result = self.run_memory(project, "context", "--query", "ArkTS route blank screen 如何定位", "--json")
            data = json.loads(result.stdout)

        weak = next(item for item in data["reflections"] if item["id"] == 1)
        strong = next(item for item in data["reflections"] if item["id"] == 2)
        self.assertGreater(weak["feedback_penalty"], 0)
        self.assertLess(weak["rerank_score"], strong["rerank_score"])

    def test_maintain_plan_reviews_open_retrieval_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)
            self.run_memory(
                project,
                "retrieval-feedback",
                "--query",
                "ArkTS route blank screen 如何定位",
                "--type",
                "reflection",
                "--id",
                "1",
                "--reason",
                "misleading",
                "--verified",
                "--json",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        actions = [action for action in data["actions"] if action["action"] == "review_retrieval_feedback"]
        self.assertEqual(1, len(actions))
        self.assertEqual(1, data["governance_summary"]["retrieval_feedback_reviews"])
        self.assertEqual("misleading", actions[0]["reason_code"])

    def test_single_unverified_feedback_is_pending_and_does_not_change_rank(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)
            self.run_memory(
                project, "retrieval-feedback", "--query", "ArkTS route blank screen",
                "--type", "reflection", "--id", "1", "--reason", "misleading",
                "--task-id", "task-one", "--json",
            )

            context = json.loads(
                self.run_memory(project, "context", "--query", "ArkTS route blank screen", "--json").stdout
            )
            maintain = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)

        weak = next(item for item in context["reflections"] if item["id"] == 1)
        self.assertEqual(0.0, weak["feedback_penalty"])
        self.assertEqual(1, maintain["retrieval_feedback_summary"]["pending_signal_count"])
        self.assertEqual(0, maintain["governance_summary"]["retrieval_feedback_reviews"])

    def test_two_independent_tasks_stabilize_feedback_and_task_retry_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)
            args = (
                "retrieval-feedback", "--query", "ArkTS route blank screen",
                "--type", "reflection", "--id", "1", "--reason", "misleading",
            )
            first = json.loads(self.run_memory(project, *args, "--task-id", "task-one", "--json").stdout)
            retry = json.loads(self.run_memory(project, *args, "--task-id", "task-one", "--json").stdout)
            self.run_memory(project, *args, "--task-id", "task-two", "--json")
            context = json.loads(
                self.run_memory(project, "context", "--query", "ArkTS route blank screen", "--json").stdout
            )

        weak = next(item for item in context["reflections"] if item["id"] == 1)
        self.assertEqual(first["id"], retry["id"])
        self.assertGreater(weak["feedback_penalty"], 0)

    def test_resolved_feedback_stops_affecting_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)
            feedback = json.loads(self.run_memory(
                project, "retrieval-feedback", "--query", "ArkTS route blank screen",
                "--type", "reflection", "--id", "1", "--reason", "misleading",
                "--verified", "--json",
            ).stdout)
            self.run_memory(
                project, "retrieval-feedback", "--feedback-id", str(feedback["id"]),
                "--status", "resolved", "--note", "not reproducible", "--json",
            )
            context = json.loads(
                self.run_memory(project, "context", "--query", "ArkTS route blank screen", "--json").stdout
            )

        weak = next(item for item in context["reflections"] if item["id"] == 1)
        self.assertEqual(0.0, weak["feedback_penalty"])

    def test_feedback_rejects_missing_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            result = subprocess.run(
                [
                    sys.executable, str(RUNTIME), "retrieval-feedback", "--project", str(project),
                    "--memory-home", str(self.memory_home(project)), "--query", "missing",
                    "--type", "reflection", "--id", "999", "--reason", "misleading", "--json",
                ],
                cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=os.environ.copy(),
            )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("reflection record not found", result.stderr)

    def test_candidate_feedback_is_not_lost_behind_unrelated_global_tail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_reflections(project)
            memory_home = self.memory_home(project)
            self.run_memory(
                project, "retrieval-feedback", "--query", "ArkTS route blank screen",
                "--type", "reflection", "--id", "1", "--reason", "misleading",
                "--verified", "--json",
            )
            project_id = hashlib.sha256(str(project.resolve()).encode("utf-8")).hexdigest()[:16]
            db_path = memory_home / "projects" / project_id / "memory.db"
            with sqlite3.connect(db_path) as conn:
                conn.executemany(
                    """
                    INSERT INTO retrieval_feedback(
                      project_id, query, normalized_query, record_type, record_id,
                      reason, status, created_at
                    ) VALUES (?, ?, ?, 'reflection', 2, 'weak_related', 'open', ?)
                    """,
                    [
                        (project_id, f"unrelated noise {index}", f"unrelated noise {index}", f"2026-07-16T00:{index % 60:02d}:00Z")
                        for index in range(250)
                    ],
                )
                conn.commit()

            context = json.loads(
                self.run_memory(project, "context", "--query", "ArkTS route blank screen", "--json").stdout
            )

        weak = next(item for item in context["reflections"] if item["id"] == 1)
        self.assertGreater(weak["feedback_penalty"], 0)

    def test_existing_feedback_tables_migrate_in_place(self) -> None:
        with sqlite3.connect(":memory:") as conn:
            conn.row_factory = sqlite3.Row
            conn.executescript(
                """
                CREATE TABLE retrieval_feedback (
                  id INTEGER PRIMARY KEY, project_id TEXT, query TEXT,
                  normalized_query TEXT, record_type TEXT, record_id INTEGER,
                  reason TEXT, replacement_type TEXT, replacement_id INTEGER,
                  note TEXT, status TEXT, created_at TEXT, reviewed_at TEXT
                );
                CREATE TABLE experience_usage_events (
                  id INTEGER PRIMARY KEY, project_id TEXT, query TEXT,
                  normalized_query TEXT, record_type TEXT, record_id INTEGER,
                  outcome TEXT, note TEXT, evidence TEXT, created_at TEXT
                );
                """
            )
            create_schema(conn)
            feedback_columns = {row["name"] for row in conn.execute("PRAGMA table_info(retrieval_feedback)")}
            usage_columns = {row["name"] for row in conn.execute("PRAGMA table_info(experience_usage_events)")}

        self.assertTrue({"task_id", "query_id", "event_key", "verified", "resolution"} <= feedback_columns)
        self.assertTrue({"task_id", "query_id", "event_key", "verified"} <= usage_columns)
