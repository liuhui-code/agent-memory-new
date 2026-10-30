# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Synthetic check-run regression cases for isolated execution.

The commands below run in temporary test fixtures; they are not evidence
of real user tasks, approvals, product correctness or measured Memory benefit.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_system_evolution import synthetic_report


COUNTING_CHECK = (
    "from pathlib import Path\n"
    "counter = Path('synthetic-counter.txt')\n"
    "counter.write_text(str(int(counter.read_text()) + 1) if counter.exists() else '1')\n"
    "print('SYNTHETIC_PRIVATE_CHECK_OUTPUT')\n"
)


class SystemEvolutionCheckTests(AgentMemoryTestBase):
    def command(self, root: Path, *args: str) -> dict:
        return json.loads(self.run_memory(root, *args, "--json").stdout)

    def failed_command(self, root: Path, *args: str) -> dict:
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            self.run_memory(root, *args, "--json")
        self.assertEqual(1, caught.exception.returncode)
        return json.loads(caught.exception.stdout)

    def prepare(self, root: Path, script: str = COUNTING_CHECK, timeout: int = 5) -> dict:
        self.run_memory(root, "init")
        report = synthetic_report()
        report["change_proposals"][0]["acceptance_criteria"] = [
            "Observe one controlled process exit, without a product correctness claim.",
        ]
        saved = self.command(root, "reflect-system", "--review-key", "synthetic-review", "--payload", json.dumps(report))
        (root / "candidate.patch").write_text("Synthetic artifact; not an applied product patch.\n", encoding="utf-8")
        prepared = self.command(root, "maintain-system-status", "--id", str(saved["proposal_id"]),
                                "--expected-revision", "1", "--status", "prepared", "--note", "Synthetic preparation.",
                                "--development-root", str(root), "--artifact-file", "candidate.patch", "--base-version", "synthetic-base")
        source = root / "synthetic_check.py"
        source.write_text(script, encoding="utf-8")
        return {
            "schema_version": "system-change-check-plan/v1", "proposal_id": saved["proposal_id"],
            "prepared_state_revision": prepared["change"]["state_revision"],
            "artifact_digest": prepared["change"]["artifact_digest"],
            "source_files": [{"path": source.name, "digest": hashlib.sha256(source.read_bytes()).hexdigest()}],
            "checks": [{"key": "synthetic-check", "argv": [sys.executable, source.name],
                        "assertion_indices": [0], "timeout_seconds": timeout}],
        }

    def run_plan(self, root: Path, plan: dict, *, execute: bool = False,
                 key: str = "synthetic-run", failure: bool = False) -> dict:
        plan_file = root / "synthetic-plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")
        args = ["maintain-system-check", "--id", str(plan["proposal_id"]), "--expected-revision",
                str(plan["prepared_state_revision"]), "--run-key", key, "--plan-file", str(plan_file)]
        if execute:
            args.append("--execute")
        return (self.failed_command if failure else self.command)(root, *args)

    def tables(self, root: Path) -> set[str]:
        with closing(sqlite3.connect(self.project_memory_dir(root) / "memory.db")) as conn:
            return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def test_preview_does_not_run_or_initialize_check_storage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.prepare(root)
            before = self.tables(root)
            result = self.run_plan(root, plan)
            self.assertEqual("system-change-check-preview/v1", result["schema_version"])
            self.assertFalse(result["checks_executed"])
            self.assertTrue(result["binding"]["matches"])
            self.assertEqual(before, self.tables(root))
            self.assertNotIn("system_change_check_runs", before)
            self.assertFalse((root / "synthetic-counter.txt").exists())

    def test_actual_observation_is_idempotent_and_does_not_promote(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.prepare(root)
            result = self.run_plan(root, plan, execute=True)
            receipt = result["run"]["receipt"]
            self.assertEqual("all_exit_zero", receipt["outcome"])
            self.assertEqual(0, receipt["results"][0]["exit_code"])
            self.assertTrue(receipt["checks_executed"])
            self.assertFalse(result["evidence_verified"])
            self.assertFalse(result["promotion_eligible"])
            self.assertFalse(result["application_performed"])
            self.assertNotIn("SYNTHETIC_PRIVATE_CHECK_OUTPUT", json.dumps(result))
            self.assertNotIn("argv", result["run"]["plan_summary"]["checks"][0])
            again = self.run_plan(root, plan, execute=True)
            self.assertTrue(again["reused"])
            self.assertEqual(result["run"]["id"], again["run"]["id"])
            self.assertEqual("1", (root / "synthetic-counter.txt").read_text())
            detail = self.command(root, "maintain-system", "--change-id", str(plan["proposal_id"]))
            self.assertEqual("prepared", detail["change"]["state"])
            self.assertEqual(2, detail["change"]["state_revision"])
            self.assertEqual("all_exit_zero", detail["check_runs"][0]["outcome"])
            stored = self.command(root, "maintain-system", "--run-key", "synthetic-run")
            self.assertEqual(result["run"]["receipt"], stored["check_run"]["receipt"])

    def test_source_and_artifact_drift_prevent_execution(self) -> None:
        for changed_file in ("synthetic_check.py", "candidate.patch"):
            with self.subTest(changed_file=changed_file), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                plan = self.prepare(root)
                (root / changed_file).write_text("Changed controlled bytes.\n", encoding="utf-8")
                result = self.run_plan(root, plan, execute=True, failure=True)
                self.assertEqual("check_binding_mismatch", result["code"])
                self.assertNotIn("system_change_check_runs", self.tables(root))
                self.assertFalse((root / "synthetic-counter.txt").exists())

    def test_nonzero_exit_is_observed_and_not_relabelled_as_passed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.prepare(root, "raise SystemExit(7)\n")
            result = self.run_plan(root, plan, execute=True, failure=True)
            self.assertEqual("exit_nonzero", result["run"]["receipt"]["outcome"])
            self.assertEqual(7, result["run"]["receipt"]["results"][0]["exit_code"])
            self.assertEqual("completed", result["run"]["state"])
            repeated = self.run_plan(root, plan, execute=True, failure=True)
            self.assertTrue(repeated["reused"])

    def test_drift_during_check_stops_remaining_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.prepare(root, "from pathlib import Path\nPath('candidate.patch').write_text('changed during check')\n")
            plan["checks"].append({"key": "must-not-run", "argv": [sys.executable, "-c", COUNTING_CHECK],
                                   "assertion_indices": [0], "timeout_seconds": 5})
            result = self.run_plan(root, plan, execute=True, failure=True)
            receipt = result["run"]["receipt"]
            self.assertEqual("binding_changed", receipt["outcome"])
            self.assertEqual(["must-not-run"], receipt["unexecuted_check_keys"])
            self.assertEqual(1, len(receipt["results"]))
            self.assertFalse((root / "synthetic-counter.txt").exists())

    def test_timeout_is_terminal_without_automatic_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.prepare(root, "import time\ntime.sleep(20)\n", timeout=1)
            result = self.run_plan(root, plan, execute=True, failure=True)
            receipt = result["run"]["receipt"]
            self.assertEqual("timed_out", receipt["outcome"])
            self.assertIsNotNone(receipt["results"][0]["exit_code"])
            self.assertEqual("completed", result["run"]["state"])
            self.assertTrue(self.run_plan(root, plan, execute=True, failure=True)["reused"])

    def test_changed_request_cannot_reuse_a_run_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.prepare(root)
            self.run_plan(root, plan, execute=True)
            plan["checks"][0]["key"] = "different-synthetic-check"
            result = self.run_plan(root, plan, execute=True, failure=True)
            self.assertEqual("run_key_conflict", result["code"])
            self.assertEqual("1", (root / "synthetic-counter.txt").read_text())

    def test_invalid_mapping_and_unknown_fields_do_not_execute(self) -> None:
        for field in ("mapping", "unknown"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                plan = self.prepare(root)
                if field == "mapping":
                    plan["checks"][0]["assertion_indices"] = []
                else:
                    plan["raw_logs"] = "SYNTHETIC_PRIVATE_CHECK_OUTPUT"
                result = self.run_plan(root, plan, execute=True, failure=True)
                self.assertEqual("invalid_check_plan", result["code"])
                self.assertNotIn("SYNTHETIC_PRIVATE_CHECK_OUTPUT", json.dumps(result))
                self.assertNotIn("system_change_check_runs", self.tables(root))

    def test_unresolved_reservation_blocks_retry_and_proposal_updates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.prepare(root)
            self.run_plan(root, plan, execute=True)
            # Controlled storage fixture models an unresolved reservation, not a live process.
            with closing(sqlite3.connect(self.project_memory_dir(root) / "memory.db")) as conn, conn:
                conn.execute("UPDATE system_change_check_runs SET state='running', completed_at=NULL, receipt_json=?",
                             (json.dumps({"outcome": "unknown", "checks_executed": None}),))
            blocked = self.run_plan(root, plan, execute=True, failure=True)
            self.assertEqual("check_run_in_progress", blocked["code"])
            status = self.failed_command(root, "maintain-system-status", "--id", str(plan["proposal_id"]),
                                         "--expected-revision", "2", "--status", "rejected", "--note", "Synthetic blocked update.")
            self.assertEqual("check_run_in_progress", status["code"])
            self.assertEqual("1", (root / "synthetic-counter.txt").read_text())
