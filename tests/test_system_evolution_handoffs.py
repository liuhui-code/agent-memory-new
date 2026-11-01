# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Controlled R3 handoffs with actual SQLite/lifecycle effects, no model efficacy claim."""

from __future__ import annotations

import copy
import io
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests import test_system_evolution_outcomes as outcomes
from tests import test_system_evolution_rounds as rounds
from tests.test_system_evolution_triggers import synthetic_trigger
from tools.agent_memory_runtime import system_evolution_handoffs as handoffs
from tools.agent_memory_runtime import system_evolution_migrations as migrations
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.system_evolution_contract import SystemEvolutionError
from tools.agent_memory_runtime.system_evolution_handoff_schema import TABLE, create_handoffs_schema
from tools.agent_memory_runtime.system_evolution_lifecycle_store import reserve_operation
from tools.agent_memory_runtime.system_evolution_outcome_contract import validate_outcome_plan


def host_plan() -> dict:
    plan = outcomes.outcome_plan()
    plan.update(schema_version="system-change-outcome-plan/v2", host_review={
        "enabled": True, "authorization_ref": "synthetic-fixture-authorized-window-review",
        "max_review_attempts": 1, "automatic_retries": 0, "max_report_chars": 4000})
    return plan


def claim_request() -> dict:
    return {"schema_version": "system-evolution-handoff-request/v1", "action": "claim",
            "round_key": "synthetic-round", "expected_revision": 1, "observations_file": "observations.json",
            "task_ref": {"origin": "client_local", "key": "synthetic-host-window-task"},
            "task_state": "completed", "activity": "round_follow_up", "review_enabled": True,
            "user_cancelled": False, "budget_available": True, "version_refs": {}}


def inspection() -> dict:
    return {"schema_version": "system-evolution-handoff-request/v1", "action": "inspect", "round_key": "synthetic-round"}


def completed(claim: dict) -> dict:
    return {**inspection(), "action": "complete", "claim_digest": claim["receipt_digest"],
            "assessment": {**claim["receipt"]["assessment_binding"], "finding": "inconclusive",
                           "summary": "Controlled declarations contain unknown outcomes and missing costs; efficacy unproven.",
                           "evidence_refs": ["synthetic-window-review"], "additional_cost": {"tokens": None, "elapsed_ms": None}}}


def failed(claim: dict) -> dict:
    return {**inspection(), "action": "fail", "claim_digest": claim["receipt_digest"], "reason": "unknown",
            "note": "Controlled host did not complete; no process-death assertion.", "evidence_refs": [],
            "additional_cost": {"tokens": None, "elapsed_ms": None}}


class SystemEvolutionHandoffTests(AgentMemoryTestBase):
    def run_memory(self, project: Path, *args: str, **kwargs):
        if not getattr(self, "installed_runtime", None):
            return super().run_memory(project, *args, **kwargs)
        return subprocess.run([sys.executable, str(self.installed_runtime), *args, "--project", str(project),
                               "--memory-home", str(self.memory_home(project))], text=True, capture_output=True, check=True)

    def command(self, root, *args):
        return json.loads(self.run_memory(root, *args, "--json").stdout)

    def fixture(self, directory, *, plan=None, migrate=True, installed=False):
        selected = host_plan() if plan is None else plan
        owner = rounds.SystemEvolutionRoundTests()
        with patch.object(outcomes, "outcome_plan", return_value=selected):
            root, recovery, change, applied = owner.fixture(directory, installed=installed)
        self.installed_runtime = getattr(owner, "installed_runtime", None)
        if migrate:
            self.command(root, "maintain-system-migrate", "--target-version", "system-handoffs-v1",
                         "--backup-file", str(Path(directory) / "before-handoffs.db"), "--execute")
        owner.record(root, rounds.opening())
        return root, owner, change, applied

    def handoff(self, root, request=None, *, execute=True, error=None):
        path = root / "handoff-request.json"
        path.write_text(json.dumps(claim_request() if request is None else request), encoding="utf-8")
        args = ("maintain-system-round-handoff", "--payload-file", str(path), *(["--execute"] if execute else []))
        if error is None:
            return self.command(root, *args)
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            self.command(root, *args)
        value = json.loads(caught.exception.stdout)
        self.assertEqual(error, value["code"])
        return value

    def test_explicit_migration_and_missing_archive_remain_side_effect_free(self):
        with tempfile.TemporaryDirectory() as directory:
            empty = Path(directory) / "empty"
            empty.mkdir()
            self.assertEqual("archive_not_initialized", self.handoff(empty, inspection())["reason"])
            self.assertFalse(self.memory_home(empty).exists())
            root, owner, change, applied = self.fixture(directory, migrate=False)
            self.assertEqual("handoff_storage_not_installed", self.handoff(root)["reason"])
            backup = Path(directory) / "before-handoffs.db"
            args = ("maintain-system-migrate", "--target-version", "system-handoffs-v1", "--backup-file", str(backup))
            self.assertFalse(self.command(root, *args)["migration_performed"])
            self.assertFalse(backup.exists())
            self.assertTrue(self.command(root, *args, "--execute")["migration_performed"])
            with closing(sqlite3.connect(backup)) as conn:
                self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name=?", (TABLE,)).fetchone())
                self.assertEqual("ok", conn.execute("PRAGMA integrity_check").fetchone()[0])
            self.assertTrue(self.command(root, *args, "--execute")["reused"])

    def test_installed_handoff_records_one_assessment_and_historical_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            root, owner, change, applied = self.fixture(directory, installed=True)
            self.run_memory(root, "update", "--type", "semantic", "--fact", "Synthetic window handoff query isolation.")
            before = self.command(root, "context", "--query", "window handoff query isolation", "--compact")
            preview = self.handoff(root, execute=False)
            self.assertEqual("ready", preview["decision"])
            self.assertFalse(preview["should_review"])
            self.assertFalse(self.handoff(root, inspection())["handoff"])
            granted = self.handoff(root)
            self.assertTrue(granted["should_review"])
            claim = granted["handoff"]["claim"]
            self.assertFalse(self.handoff(root)["should_review"])
            result = completed(claim)
            self.assertFalse(self.handoff(root, result, execute=False)["records_written"])
            self.assertEqual(1, owner.read(root)["event"]["revision"])
            saved = self.handoff(root, result)
            self.assertEqual("recorded", saved["decision"])
            self.assertFalse(saved["efficacy_verified"])
            self.assertFalse(saved["model_execution_observed"])
            self.assertFalse(saved["application_performed"])
            self.assertEqual(2, owner.read(root)["event"]["revision"])
            self.assertEqual("assessed", owner.read(root)["event"]["receipt"]["state"])
            self.assertEqual("monitoring", applied.state(root, change)["state"])
            (root / "observations.json").unlink()
            (root / "outcome-plan.json").unlink()
            self.assertTrue(self.handoff(root, result)["reused"])
            self.assertEqual(saved["handoff"], self.handoff(root, inspection())["handoff"])
            altered = copy.deepcopy(result)
            altered["assessment"]["summary"] = "Changed historical opinion."
            self.handoff(root, altered, error="handoff_finish_conflict")
            with closing(sqlite3.connect(self.project_memory_dir(root) / "memory.db")) as conn:
                for statement in (f"UPDATE {TABLE} SET task_key='changed'", f"DELETE FROM {TABLE}"):
                    with self.assertRaises(sqlite3.IntegrityError):
                        conn.execute(statement)
                    conn.rollback()
            after = self.command(root, "context", "--query", "window handoff query isolation", "--compact")
            self.assertEqual(before["query_handoff"], after["query_handoff"])

    def test_boundary_flags_partial_and_unknown_windows_do_not_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root, owner, change, applied = self.fixture(directory)
            cases = [({"user_cancelled": True}, "user_stopped"), ({"review_enabled": False}, "review_disabled"),
                     ({"budget_available": False}, "host_budget_unavailable"), ({"activity": "system_review"}, "recursive_review_suppressed"),
                     ({"activity": "system_evolution"}, "recursive_review_suppressed"), ({"task_state": "in_progress"}, "task_not_closed")]
            for changes, reason in cases:
                self.assertEqual(reason, self.handoff(root, {**claim_request(), **changes})["reason"])
            path = root / "observations.json"
            original = json.loads(path.read_text())
            partial = {**original, "tasks": original["tasks"][:2]}
            path.write_text(json.dumps(partial))
            self.assertEqual("observation_window_incomplete", self.handoff(root)["reason"])
            original["tasks"][0].update(outcome="unknown", verification="unavailable", evidence_refs=[])
            path.write_text(json.dumps(original))
            self.assertEqual("known_result_declaration_unavailable", self.handoff(root)["reason"])
            self.assertFalse(self.handoff(root, inspection())["handoff"])

    def test_old_or_disabled_plans_and_prebound_report_limit(self):
        plans = [(outcomes.outcome_plan(), "prebound_host_review_not_enabled"),
                 (host_plan(), "prebound_host_review_not_enabled"), (host_plan(), "handoff_report_budget_exhausted"),
                 (host_plan(), "host_report_budget_unavailable")]
        plans[1][0]["host_review"]["enabled"] = False
        plans[2][0]["host_review"]["max_report_chars"] = 1100
        plans[3][0]["host_review"]["max_report_chars"] = 1
        for plan, reason in plans:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                root, owner, change, applied = self.fixture(directory, plan=plan)
                value = self.handoff(root)
                if value["should_review"]:
                    claim = value["handoff"]["claim"]
                    report = completed(claim)
                    report["assessment"]["evidence_refs"] = ["synthetic-ref-" + str(i) + ":" + "x" * 200 for i in range(8)]
                    self.handoff(root, report, error=reason)
                    self.assertEqual("failed", self.handoff(root, failed(claim))["decision"])
                else:
                    self.assertEqual(reason, value["reason"])
        for name, bad in (("max_review_attempts", 2), ("automatic_retries", 1), ("enabled", 1)):
            plan = host_plan()
            plan["host_review"][name] = bad
            with self.assertRaises(SystemEvolutionError):
                validate_outcome_plan(plan, 1, 3)

    def test_actual_concurrent_claims_and_shared_v1_task_budget(self):
        for v1_first in (False, True):
            with self.subTest(v1_first=v1_first), tempfile.TemporaryDirectory() as directory:
                root, owner, change, applied = self.fixture(directory)
                trigger = synthetic_trigger()
                trigger["task_ref"] = claim_request()["task_ref"]
                args = ("reflect-system-trigger", "--payload", json.dumps(trigger), "--claim")
                if v1_first:
                    self.assertTrue(self.command(root, *args)["claim_created"])
                    self.assertEqual("task_review_already_consumed", self.handoff(root)["reason"])
                else:
                    project = resolve_project(str(root), str(self.memory_home(root)))
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        values = list(pool.map(lambda _: handoffs.handoff_round(project, claim_request(), True), range(2)))
                    self.assertCountEqual([True, False], [value["should_review"] for value in values])
                    self.assertEqual("round_handoff_already_claimed", self.command(root, *args)["reason"])

    def test_drift_and_stale_round_refuse_finish_and_failure_retains_consumption(self):
        with tempfile.TemporaryDirectory() as directory:
            root, owner, change, applied = self.fixture(directory)
            claim = self.handoff(root)["handoff"]["claim"]
            path = root / "observations.json"
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            self.handoff(root, completed(claim), error="handoff_input_drift")
            self.assertEqual(1, owner.read(root)["event"]["revision"])
            path.write_bytes(original)
            wrong = completed(claim)
            wrong["assessment"]["record_key"] = "different-key"
            self.handoff(root, wrong, error="handoff_binding_mismatch")
            owner.record(root, rounds.assessment(root))
            self.handoff(root, completed(claim), error="round_revision_conflict")
            self.assertEqual("failed", self.handoff(root, failed(claim))["decision"])
            self.assertFalse(self.handoff(root, {**claim_request(), "expected_revision": 2})["should_review"])
            self.handoff(root, completed(claim), error="handoff_finish_conflict")

    def test_unknown_work_blocks_finish_without_clearing_actual_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            root, owner, change, applied = self.fixture(directory)
            claim = self.handoff(root)["handoff"]["claim"]
            project = resolve_project(str(root), str(self.memory_home(root)))
            current = applied.state(root, change)
            # Controlled unknown metadata, not an assertion that a child process exists.
            reserve_operation(project, current, "unknown-handoff-work", "monitoring",
                              {"call": {"expected_revision": current["state_revision"]}}, {"active_check_key": "unknown"})
            self.handoff(root, completed(claim), error="schema_work_in_progress")
            self.assertEqual("failed", self.handoff(root, failed(claim))["decision"])
            operation = self.command(root, "maintain-system", "--operation-key", "unknown-handoff-work")["operation"]
            self.assertEqual("running", operation["state"])

    def test_completion_and_round_write_roll_back_together_after_actual_insert(self):
        with tempfile.TemporaryDirectory() as directory:
            root, owner, change, applied = self.fixture(directory)
            claim = self.handoff(root)["handoff"]["claim"]
            project = resolve_project(str(root), str(self.memory_home(root)))
            with patch.object(handoffs, "append_event", side_effect=RuntimeError("Controlled failure after assessment insert")):
                with self.assertRaisesRegex(RuntimeError, "after assessment"):
                    handoffs.handoff_round(project, completed(claim), True)
            self.assertEqual(1, owner.read(root)["event"]["revision"])
            self.assertNotIn("finish", self.handoff(root, inspection())["handoff"])
            self.assertEqual("recorded", self.handoff(root, completed(claim))["decision"])

    def test_assessment_budget_and_stopped_round_do_not_launch_a_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root, owner, change, applied = self.fixture(directory)
            owner.record(root, rounds.assessment(root))
            self.assertEqual("no_new_observations", self.handoff(root, {**claim_request(), "expected_revision": 2})["reason"])
            owner.record(root, rounds.assessment(root, 2))
            value = json.loads((root / "observations.json").read_text())
            value["tasks"][0]["cost"]["tokens"] = 30
            (root / "observations.json").write_text(json.dumps(value))
            self.assertEqual("assessment_budget_exhausted", self.handoff(root, {**claim_request(), "expected_revision": 3})["reason"])
            owner.record(root, rounds.decision(3, "stop"))
            self.assertEqual("round_already_decided", self.handoff(root, {**claim_request(), "expected_revision": 4})["reason"])

    def test_failed_component_install_and_unsupported_schema_preserve_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root, owner, change, applied = self.fixture(directory, migrate=False)
            project = resolve_project(str(root), str(self.memory_home(root)))
            backup = Path(directory) / "failed-handoffs.db"
            def interrupted(conn):
                create_handoffs_schema(conn)
                raise RuntimeError("Controlled handoff DDL interruption")
            with patch.object(migrations, "create_handoffs_schema", side_effect=interrupted):
                with self.assertRaisesRegex(RuntimeError, "DDL interruption"):
                    migrations.migrate_governance(project, "system-handoffs-v1", str(backup), True)
            for db in (backup, project.db_path):
                with closing(sqlite3.connect(db)) as conn:
                    self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name=?", (TABLE,)).fetchone())
                    self.assertEqual("ok", conn.execute("PRAGMA integrity_check").fetchone()[0])
            self.command(root, "maintain-system-migrate", "--target-version", "system-handoffs-v1",
                         "--backup-file", str(Path(directory) / "success-handoffs.db"), "--execute")
            self.handoff(root)
            with closing(sqlite3.connect(project.db_path)) as conn:
                conn.execute("UPDATE runtime_schema_versions SET version='unknown' WHERE component='system_evolution_handoffs'")
                conn.commit()
            self.handoff(root, inspection(), error="handoff_schema_unsupported")
            with closing(sqlite3.connect(project.db_path)) as conn:
                self.assertEqual(1, conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0])
                conn.execute("UPDATE runtime_schema_versions SET version='system-handoffs-v1' WHERE component='system_evolution_handoffs'")
                conn.execute("DROP TRIGGER system_handoffs_no_delete")
                conn.commit()
            self.handoff(root, inspection(), error="handoff_schema_unsupported")

    def test_actual_old_runtime_ordinary_writes_preserve_handoff_events(self):
        with tempfile.TemporaryDirectory() as directory:
            root, owner, change, applied = self.fixture(directory)
            claim = self.handoff(root)["handoff"]["claim"]
            before = self.handoff(root, completed(claim))["handoff"]
            old = Path(directory) / "old"
            old.mkdir()
            repository = Path(__file__).resolve().parents[1]
            env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_LAZY_FETCH="1")
            raw = subprocess.check_output(["git", "-c", "protocol.allow=never", "archive", "--format=tar",
                                           "4d5e068e68a107437aee2df7edd39acb595d311f", "tools"], cwd=repository, env=env)
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                for member in archive.getmembers():
                    target = old / member.name
                    target.resolve().relative_to(old.resolve())
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        self.assertTrue(member.isfile())
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with archive.extractfile(member) as source:
                            target.write_bytes(source.read())
            command = [sys.executable, str(old / "tools/agent_memory.py")]
            subprocess.run([*command, "update", "--project", str(root), "--memory-home", str(self.memory_home(root)),
                            "--type", "semantic", "--fact", "Synthetic old writer preserves R3 handoff history."],
                           check=True, capture_output=True)
            query = ["context", "--project", str(root), "--memory-home", str(self.memory_home(root)),
                     "--query", "old writer preserves R3 handoff history", "--compact", "--json"]
            legacy = json.loads(subprocess.run([*command, *query], text=True, check=True, capture_output=True).stdout)
            current = self.command(root, "context", "--query", "old writer preserves R3 handoff history", "--compact")
            self.assertEqual(legacy["query_handoff"], current["query_handoff"])
            self.assertEqual(before, self.handoff(root, inspection())["handoff"])
