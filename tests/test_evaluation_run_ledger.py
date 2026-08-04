# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tools.agent_memory_runtime.benchmark_case_seal import case_pack_digest
from tools.agent_memory_runtime.evaluation_run_ledger import (
    evaluation_run_guard,
    reserve_evaluation_run,
)
from tools.agent_memory_runtime.storage import connect, ensure_initialized, resolve_project


class EvaluationRunLedgerTests(unittest.TestCase):
    def test_development_pack_is_repeatable_and_not_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.project(Path(temp_dir))
            pack = {"suite": "development", "evaluation_governance": {"enforced": True, "split": "development"}}

            with evaluation_run_guard(project, pack, "context_capability", "cases.json") as run:
                self.assertIsNone(run)
            with evaluation_run_guard(project, pack, "context_capability", "cases.json") as run:
                self.assertIsNone(run)

            self.assertEqual([], self.rows(project))

    def test_holdout_is_consumed_once_and_records_result_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.project(Path(temp_dir))
            pack = holdout_pack("once")

            with evaluation_run_guard(project, pack, "context_capability", "cases.json") as run:
                assert run is not None
                run["gate_status"] = "pass"
                run["result"] = {"system_context_gate": "pass"}

            row = self.rows(project)[0]
            self.assertEqual("completed", row["status"])
            self.assertEqual("pass", row["gate_status"])
            self.assertEqual(64, len(row["result_digest"]))
            with self.assertRaisesRegex(SystemExit, "already consumed or reserved"):
                with evaluation_run_guard(project, pack, "context_capability", "cases.json"):
                    self.fail("a consumed holdout body must not execute")

    def test_failed_holdout_remains_consumed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.project(Path(temp_dir))
            pack = holdout_pack("failed")

            with self.assertRaisesRegex(RuntimeError, "runner failed"):
                with evaluation_run_guard(project, pack, "context_capability", "cases.json"):
                    raise RuntimeError("runner failed")

            row = self.rows(project)[0]
            self.assertEqual("failed", row["status"])
            self.assertEqual("RuntimeError", row["error_class"])
            with self.assertRaises(SystemExit):
                reserve_evaluation_run(project, pack, "context_capability", "cases.json")

    def test_agent_run_requires_passing_context_for_same_seal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.project(Path(temp_dir))
            pack = holdout_pack("predecessor")

            with self.assertRaisesRegex(SystemExit, "requires a recorded Context run"):
                reserve_evaluation_run(project, pack, "agent_benchmark", "cases.json")
            with evaluation_run_guard(project, pack, "context_capability", "cases.json") as run:
                assert run is not None
                run["gate_status"] = "pass"
                run["result"] = {"system_context_gate": "pass"}
            with evaluation_run_guard(project, pack, "agent_benchmark", "cases.json") as run:
                assert run is not None
                run["gate_status"] = "pass"
                run["result"] = {"quality_gate": "pass"}

            self.assertEqual(
                ["context_capability", "agent_benchmark"],
                [row["run_kind"] for row in self.rows(project)],
            )

    def test_failed_context_blocks_agent_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.project(Path(temp_dir))
            pack = holdout_pack("blocked")

            with evaluation_run_guard(project, pack, "context_capability", "cases.json") as run:
                assert run is not None
                run["gate_status"] = "fail"
                run["result"] = {"system_context_gate": "fail"}
            with self.assertRaisesRegex(SystemExit, "completed passing Context gate"):
                reserve_evaluation_run(project, pack, "agent_benchmark", "cases.json")

    def test_concurrent_reservations_have_one_winner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.project(Path(temp_dir))
            pack = holdout_pack("concurrent")
            barrier = threading.Barrier(2)

            def reserve() -> str:
                barrier.wait()
                try:
                    reserve_evaluation_run(project, pack, "context_capability", "cases.json")
                    return "reserved"
                except SystemExit:
                    return "rejected"

            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(lambda _: reserve(), range(2)))

            self.assertEqual(["rejected", "reserved"], sorted(outcomes))
            self.assertEqual(1, len(self.rows(project)))

    @staticmethod
    def project(temp_dir: Path):
        source = temp_dir / "source"
        source.mkdir()
        project = resolve_project(str(source), str(temp_dir / "memory"))
        ensure_initialized(project)
        return project

    @staticmethod
    def rows(project) -> list[dict]:
        with connect(project) as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM evaluation_runs ORDER BY id")]


def holdout_pack(case_id: str) -> dict:
    pack = {
        "schema_version": "agent-benchmark-cases/v1",
        "suite": "holdout",
        "governance": {"require_seal": True},
        "evaluation_governance": {
            "status": "classified",
            "enforced": True,
            "split": "holdout",
        },
        "cases": [{"id": case_id}],
    }
    pack["seal"] = {
        "schema_version": "agent-benchmark-case-seal/v1",
        "sealed_at": "2026-08-02T00:00:00+00:00",
        "digest_algorithm": "sha256",
        "canonicalization": "json-sort-keys-compact-excluding-seal",
        "case_count": 1,
        "digest": case_pack_digest(pack),
    }
    return pack


if __name__ == "__main__":
    unittest.main()
