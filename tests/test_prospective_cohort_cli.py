# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_prospective_cohort_contract import protocol
from tests.test_prospective_cohort_metrics import benchmark_result


class ProspectiveCohortCliTests(AgentMemoryTestBase):
    def test_consecutive_cohort_closes_with_sanitized_natural_and_opportunity_segments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            self.init_git_project(root)
            protocol_path = self.write_json(root / "cohort.json", protocol())
            task_path = self.write_json(
                root / "task.json", {"description": "Find private marker SECRET_QUERY_42"}
            )
            self.run_memory(root, "init")
            self.run_memory(
                root, "update", "--type", "semantic", "--fact", "Timeout owner is RequestService"
            )

            created = self.json_command(
                root, "eval-cohort-create", "--protocol", str(protocol_path), "--json"
            )
            self.assertEqual("registered", created["status"])
            enrolled = self.json_command(
                root,
                "eval-cohort-enroll",
                "--cohort-id", "cohort-v1",
                "--task-id", "task-1",
                "--task-file", str(task_path),
                "--eligibility", "eligible",
                "--opportunity", "present",
                "--evidence-ref", "semantic:1",
                "--json",
            )
            self.assertEqual(1, enrolled["sequence_no"])
            self.assertEqual(64, len(enrolled["memory_manifest_digest"]))
            self.assertNotIn("SECRET_QUERY_42", json.dumps(enrolled))

            with self.assertRaises(subprocess.CalledProcessError):
                self.json_command(
                    root,
                    "eval-cohort-enroll",
                    "--cohort-id", "cohort-v1",
                    "--task-id", "task-overlap",
                    "--task-file", str(task_path),
                    "--eligibility", "eligible",
                    "--opportunity", "unknown",
                    "--json",
                )

            self.run_memory(
                root, "context", "--query", "SECRET_QUERY_42", "--compact", "--json"
            )
            completed = self.json_command(
                root,
                "eval-cohort-complete",
                "--cohort-id", "cohort-v1",
                "--task-id", "task-1",
                "--outcome", "pass",
                "--verification", "source_review",
                "--json",
            )
            self.assertEqual(1, completed["usage_metrics"]["query_count"])
            self.assertNotIn("SECRET_QUERY_42", json.dumps(completed))

            excluded = self.json_command(
                root,
                "eval-cohort-enroll",
                "--cohort-id", "cohort-v1",
                "--task-id", "task-2",
                "--task-file", str(task_path),
                "--eligibility", "excluded",
                "--opportunity", "unknown",
                "--exclusion-reason", "duplicate_task",
                "--json",
            )
            self.assertEqual(2, excluded["sequence_no"])
            finalized = self.json_command(
                root, "eval-cohort-finalize", "--cohort-id", "cohort-v1", "--json"
            )

            self.assertEqual("completed", finalized["status"])
            self.assertEqual("pass", finalized["data_quality"]["status"])
            self.assertEqual(2, finalized["data_quality"]["presented_count"])
            self.assertEqual(1, finalized["segments"]["natural"]["eligible_count"])
            self.assertEqual(1, finalized["segments"]["memory_opportunity"]["eligible_count"])
            self.assertEqual("observational", finalized["evidence_mode"])
            self.assertEqual("self_attested", finalized["external_consecutiveness"])
            self.assert_database_is_sanitized(root)

    def test_invalid_opportunity_reference_and_early_finalize_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            self.init_git_project(root)
            protocol_path = self.write_json(root / "cohort.json", protocol())
            task_path = self.write_json(root / "task.json", {"description": "Task"})
            self.run_memory(root, "init")
            self.json_command(
                root, "eval-cohort-create", "--protocol", str(protocol_path), "--json"
            )

            with self.assertRaises(subprocess.CalledProcessError):
                self.json_command(
                    root,
                    "eval-cohort-enroll",
                    "--cohort-id", "cohort-v1",
                    "--task-id", "task-1",
                    "--task-file", str(task_path),
                    "--eligibility", "eligible",
                    "--opportunity", "present",
                    "--evidence-ref", "reflection:999",
                    "--json",
                )

    def test_completed_usage_sample_allows_next_eligible_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            self.init_git_project(root)
            protocol_path = self.write_json(root / "cohort.json", protocol())
            task_path = self.write_json(root / "task.json", {"description": "Task"})
            self.run_memory(root, "init")
            self.json_command(root, "eval-cohort-create", "--protocol", str(protocol_path), "--json")
            for task_id in ("task-1", "task-2"):
                self.json_command(
                    root,
                    "eval-cohort-enroll",
                    "--cohort-id", "cohort-v1",
                    "--task-id", task_id,
                    "--task-file", str(task_path),
                    "--eligibility", "eligible",
                    "--opportunity", "unknown",
                    "--json",
                )
                self.json_command(
                    root,
                    "eval-cohort-complete",
                    "--cohort-id", "cohort-v1",
                    "--task-id", task_id,
                    "--outcome", "pass",
                    "--verification", "test",
                    "--json",
                )

            report = self.json_command(
                root, "eval-cohort-finalize", "--cohort-id", "cohort-v1", "--json"
            )
            self.assertEqual(2, report["segments"]["natural"]["completed_count"])
            with self.assertRaises(subprocess.CalledProcessError):
                self.json_command(
                    root, "eval-cohort-finalize", "--cohort-id", "cohort-v1", "--json"
                )

    def test_hash_chain_tampering_blocks_finalize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            self.init_git_project(root)
            value = protocol()
            value["target_presented_tasks"] = 1
            protocol_path = self.write_json(root / "cohort.json", value)
            task_path = self.write_json(root / "task.json", {"description": "Task"})
            self.run_memory(root, "init")
            self.json_command(root, "eval-cohort-create", "--protocol", str(protocol_path), "--json")
            self.json_command(
                root,
                "eval-cohort-enroll",
                "--cohort-id", "cohort-v1",
                "--task-id", "task-1",
                "--task-file", str(task_path),
                "--eligibility", "excluded",
                "--opportunity", "unknown",
                "--exclusion-reason", "not_diagnosis",
                "--json",
            )
            with sqlite3.connect(self.database(root)) as conn:
                conn.execute(
                    "UPDATE prospective_cohort_tasks SET task_digest = ? WHERE task_id = ?",
                    ("0" * 64, "task-1"),
                )

            with self.assertRaises(subprocess.CalledProcessError):
                self.json_command(
                    root, "eval-cohort-finalize", "--cohort-id", "cohort-v1", "--json"
                )

    def test_mismatched_usage_trace_rolls_back_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            self.init_git_project(root)
            value = protocol()
            value["target_presented_tasks"] = 1
            protocol_path = self.write_json(root / "cohort.json", value)
            task_path = self.write_json(root / "task.json", {"description": "Task"})
            self.run_memory(root, "init")
            self.json_command(root, "eval-cohort-create", "--protocol", str(protocol_path), "--json")
            self.json_command(
                root,
                "eval-cohort-enroll",
                "--cohort-id", "cohort-v1",
                "--task-id", "task-1",
                "--task-file", str(task_path),
                "--eligibility", "eligible",
                "--opportunity", "unknown",
                "--json",
            )
            trace_path = self.project_memory_dir(root) / "runtime" / "last_task_trace.json"
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            trace["sample_id"] = "another-task"
            trace_path.write_text(json.dumps(trace), encoding="utf-8")

            with self.assertRaises(subprocess.CalledProcessError):
                self.json_command(
                    root,
                    "eval-cohort-complete",
                    "--cohort-id", "cohort-v1",
                    "--task-id", "task-1",
                    "--outcome", "pass",
                    "--verification", "test",
                    "--json",
                )
            with sqlite3.connect(self.database(root)) as conn:
                status = conn.execute(
                    "SELECT status FROM prospective_cohort_tasks WHERE task_id = 'task-1'"
                ).fetchone()[0]
            self.assertEqual("active", status)

    def test_clean_task_binds_one_case_selective_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            self.init_git_project(root)
            value = protocol()
            value["target_presented_tasks"] = 1
            protocol_path = self.write_json(base / "cohort.json", value)
            task_path = self.write_json(base / "task.json", {"description": "Task"})
            result_path = self.write_json(base / "result.json", benchmark_result())
            self.run_memory(root, "init")
            self.json_command(root, "eval-cohort-create", "--protocol", str(protocol_path), "--json")
            enrolled = self.json_command(
                root,
                "eval-cohort-enroll",
                "--cohort-id", "cohort-v1",
                "--task-id", "case-1",
                "--task-file", str(task_path),
                "--eligibility", "eligible",
                "--opportunity", "unknown",
                "--json",
            )
            self.assertTrue(enrolled["replay_eligible"])
            completed = self.json_command(
                root,
                "eval-cohort-complete",
                "--cohort-id", "cohort-v1",
                "--task-id", "case-1",
                "--outcome", "pass",
                "--verification", "test",
                "--benchmark-result", str(result_path),
                "--case-id", "case-1",
                "--json",
            )
            self.assertEqual("pass", completed["benchmark_metrics"]["quality_gate"])
            report = self.json_command(
                root, "eval-cohort-finalize", "--cohort-id", "cohort-v1", "--json"
            )
            self.assertEqual("paired_selective_query", report["evidence_mode"])

    def json_command(self, root: Path, *args: str) -> dict:
        return json.loads(self.run_memory(root, *args).stdout)

    def assert_database_is_sanitized(self, root: Path) -> None:
        with sqlite3.connect(self.database(root)) as conn:
            task = conn.execute(
                "SELECT * FROM prospective_cohort_tasks WHERE task_id = 'task-1'"
            ).fetchone()
        self.assertIsNotNone(task)
        self.assertNotIn("SECRET_QUERY_42", json.dumps(task))

    def database(self, root: Path) -> Path:
        return self.project_memory_dir(root) / "memory.db"

    @staticmethod
    def write_json(path: Path, value: dict) -> Path:
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    @staticmethod
    def init_git_project(root: Path) -> None:
        root.mkdir()
        (root / "main.ets").write_text("export const value = 1\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        subprocess.run(["git", "add", "main.ets"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)


if __name__ == "__main__":
    unittest.main()
