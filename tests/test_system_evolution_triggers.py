# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Synthetic trigger-contract regressions, not real tasks or model runs."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_system_evolution import synthetic_report
from tools.agent_memory_runtime.system_evolution_trigger_contract import trigger_choice


def synthetic_trigger() -> dict:
    return {
        "schema_version": "system-meta-trigger/v1",
        "task_ref": {"key": "synthetic-session.task-1", "origin": "client_local"},
        "task_state": "failed", "task_outcome": "unknown", "memory_use": "used",
        "memory_requested": False, "manual_request": False, "review_enabled": True,
        "user_cancelled": False, "budget_available": True, "activity": "task",
        "signals": [{"kind": "memory_error", "refs": ["synthetic-observation:memory-error"]}],
        "version_refs": {}, "query_refs": [],
    }


class SystemEvolutionTriggerTests(AgentMemoryTestBase):
    def command(self, root: Path, *args: str) -> dict:
        return json.loads(self.run_memory(root, *args, "--json").stdout)

    def failed(self, root: Path, *args: str) -> dict:
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            self.run_memory(root, *args, "--json")
        self.assertEqual(1, caught.exception.returncode)
        return json.loads(caught.exception.stdout)

    def trigger(self, root: Path, request: dict | None = None, claim: bool = False) -> dict:
        args = ["reflect-system-trigger", "--payload", json.dumps(request if request is not None else synthetic_trigger())]
        if claim:
            args.append("--claim")
        return self.command(root, *args)

    def tables(self, root: Path) -> set[str]:
        with closing(sqlite3.connect(self.project_memory_dir(root) / "memory.db")) as conn:
            return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def save_decision(self, root: Path, decision: dict) -> tuple[dict, dict]:
        report = synthetic_report()
        report.update(decision["report_binding"])
        saved = self.command(root, "reflect-system", "--review-key", decision["review_key"], "--payload", json.dumps(report))
        return saved, report

    def test_priority_stop_budget_manual_and_recursive_suppression(self) -> None:
        cases = [
            ({"manual_request": True, "user_cancelled": True}, (None, "user_stopped")),
            ({"manual_request": True, "review_enabled": False}, (None, "review_disabled")),
            ({"manual_request": True, "budget_available": False}, (None, "review_budget_unavailable")),
            ({"manual_request": True, "task_state": "in_progress"}, ("manual", "manual_request")),
            ({"manual_request": True, "activity": "system_review"}, ("manual", "manual_request")),
            ({"activity": "system_evolution"}, (None, "recursive_review_suppressed")),
            ({"activity": "system_review"}, (None, "recursive_review_suppressed")),
            ({"task_state": "in_progress"}, (None, "task_not_closed")),
            ({"task_state": "cancelled"}, (None, "task_not_closed")),
            ({"memory_use": "not_used"}, (None, "memory_not_observed_or_requested")),
            ({"task_ref": None}, (None, "task_identity_unavailable")),
            ({"signals": []}, (None, "no_concrete_signal")),
        ]
        for changes, expected in cases:
            with self.subTest(changes=changes):
                request = synthetic_trigger()
                request.update(changes)
                self.assertEqual(expected, trigger_choice(request))

    def test_readonly_decision_does_not_initialize_archive_or_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            decision = self.trigger(root)
            self.assertTrue(decision["should_review"])
            self.assertFalse(decision["claim_created"])
            self.assertFalse(decision["model_invoked"])
            self.assertFalse(self.memory_home(root).exists())
            refused = self.trigger(root, claim=True)
            self.assertFalse(refused["should_review"])
            self.assertEqual("archive_not_initialized", refused["reason"])
            self.assertFalse(self.memory_home(root).exists())
            self.run_memory(root, "init")
            before = self.tables(root)
            self.trigger(root)
            self.assertEqual(before, self.tables(root))

    def test_claim_is_separate_from_report_storage_and_can_be_inspected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_memory(root, "init")
            before = self.tables(root)
            decision = self.trigger(root, claim=True)
            self.assertTrue(decision["claim_created"])
            self.assertEqual("reserved", decision["claim"]["state"])
            self.assertFalse(decision["claim"]["model_execution_observed"])
            self.assertEqual({"system_meta_review_triggers"}, self.tables(root) - before)
            summary = self.command(root, "maintain-system")
            self.assertTrue(summary["available"])
            self.assertEqual(0, summary["counts"]["review_revisions"])
            self.assertEqual(1, len(summary["trigger_claims"]))
            detail = self.command(root, "maintain-system", "--trigger-id", str(decision["claim"]["id"]))
            self.assertEqual(synthetic_trigger(), detail["trigger_claim"]["request"])

    def test_concurrent_claims_allocate_only_one_slot_without_model_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_memory(root, "init")
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.trigger(root, claim=True), range(2)))
            self.assertEqual(1, sum(result["claim_created"] for result in results))
            skipped = next(result for result in results if not result["claim_created"])
            self.assertEqual("already_claimed", skipped["reason"])
            self.assertFalse(skipped["should_review"])
            self.assertTrue(all(not result["model_invoked"] for result in results))

    def test_save_links_claim_and_manual_revision_preserves_historical_retries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_memory(root, "init")
            decision = self.trigger(root, claim=True)
            first, report = self.save_decision(root, decision)
            self.assertEqual("already_reviewed", self.trigger(root, claim=True)["reason"])
            request = synthetic_trigger()
            request["manual_request"] = True
            revision = self.trigger(root, request, claim=True)
            self.assertTrue(revision["should_review"])
            self.assertFalse(revision["claim_created"])
            self.assertEqual(2, revision["next_review_revision"])
            self.assertEqual(decision["review_key"], revision["review_key"])
            second, _ = self.save_decision(root, revision)
            detail = self.command(root, "maintain-system", "--trigger-id", str(decision["claim"]["id"]))
            self.assertEqual("recorded", detail["trigger_claim"]["state"])
            self.assertEqual(second["review"]["id"], detail["trigger_claim"]["review_id"])
            repeated = self.command(root, "reflect-system", "--review-key", decision["review_key"], "--payload", json.dumps(report))
            self.assertFalse(repeated["inserted"])
            self.assertEqual(first["review"], repeated["review"])

    def test_claim_binding_cannot_be_bypassed_by_key_task_or_automatic_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_memory(root, "init")
            decision = self.trigger(root, claim=True)
            report = synthetic_report()
            report.update(decision["report_binding"])
            before = self.tables(root)
            bad = self.failed(root, "reflect-system", "--review-key", "different-key", "--payload", json.dumps(report))
            self.assertEqual("trigger_claim_conflict", bad["code"])
            wrong_task = json.loads(json.dumps(report))
            wrong_task["task_ref"] = {"key": "synthetic-other-task", "origin": "client_local"}
            bad = self.failed(root, "reflect-system", "--review-key", decision["review_key"], "--payload", json.dumps(wrong_task))
            self.assertEqual("trigger_claim_conflict", bad["code"])
            self.assertEqual(before, self.tables(root))
            self.save_decision(root, decision)
            report["review_revision"] = 2
            bad = self.failed(root, "reflect-system", "--review-key", decision["review_key"], "--payload", json.dumps(report))
            self.assertEqual("trigger_claim_conflict", bad["code"])

    def test_legacy_report_remains_idempotent_after_a_manual_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_memory(root, "init")
            decision = self.trigger(root)
            saved, report = self.save_decision(root, decision)
            request = synthetic_trigger()
            request["manual_request"] = True
            manual = self.trigger(root, request, claim=True)
            self.assertTrue(manual["claim_created"])
            self.assertEqual("recorded", manual["claim"]["state"])
            self.assertEqual(2, manual["next_review_revision"])
            repeated = self.command(root, "reflect-system", "--review-key", decision["review_key"], "--payload", json.dumps(report))
            self.assertFalse(repeated["inserted"])
            self.assertEqual(saved["review"], repeated["review"])

    def test_repeated_gap_needs_distinct_rounds_and_inputs_remain_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = synthetic_trigger()
            request["signals"] = [{"kind": "repeated_gap", "refs": ["synthetic-gap:observed"],
                                   "gap_key": "synthetic-gap", "round_refs": ["synthetic-round:1", "synthetic-round:2"]}]
            self.assertEqual("repeated_gap", self.trigger(root, request)["trigger"])
            request["signals"][0]["round_refs"] = ["synthetic-round:1", "synthetic-round:1"]
            result = self.failed(root, "reflect-system-trigger", "--payload", json.dumps(request))
            self.assertEqual("invalid_trigger", result["code"])
            request = synthetic_trigger()
            request["raw_logs"] = "SYNTHETIC_PRIVATE_TRIGGER_TEXT"
            result = self.failed(root, "reflect-system-trigger", "--payload", json.dumps(request))
            self.assertNotIn("SYNTHETIC_PRIVATE_TRIGGER_TEXT", json.dumps(result))
            self.assertFalse(self.memory_home(root).exists())

    def test_manual_unassociated_review_does_not_invent_a_claim_or_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = synthetic_trigger()
            request.update(task_ref=None, manual_request=True, task_state="cancelled", signals=[])
            result = self.trigger(root, request, claim=True)
            self.assertTrue(result["should_review"])
            self.assertIsNone(result["review_key"])
            self.assertIsNone(result["claim"])
            self.assertIsNone(result["report_binding"]["task_ref"])
            self.assertFalse(self.memory_home(root).exists())
