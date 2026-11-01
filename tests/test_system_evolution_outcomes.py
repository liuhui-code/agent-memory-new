# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Read-only effect feedback using actual isolated lifecycle records and declared tasks."""

import copy
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests import test_system_evolution_lifecycle as lifecycle
from tools.agent_memory_runtime.system_evolution_contract import SystemEvolutionError
from tools.agent_memory_runtime.system_evolution_outcome_contract import validate_observations
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.system_evolution_lifecycle_store import reserve_operation, finish_operation


def outcome_plan() -> dict:
    return {"schema_version": "system-change-outcome-plan/v1", "proposal_id": 1,
            "prepared_state_revision": 3, "round_key": "synthetic-round",
            "hypothesis": "The controlled layout remains usable after application.",
            "expected_result": "Observe later checks and retain negative/unknown task declarations.",
            "guardrails": ["Do not treat controlled checks or task declarations as production efficacy."],
            "window": {"key": "synthetic-window", "source_ref": "synthetic-development-fixture",
                       "target_presented": 3, "allowed_exclusion_reasons": ["out_of_scope"]}}


def observations(project_id: str, digest: str) -> dict:
    tasks = []
    for sequence, outcome in enumerate(("pass", "unknown", "unknown"), 1):
        excluded = sequence == 3
        tasks.append({"sequence": sequence, "task_ref": {"key": "synthetic-task-" + str(sequence), "origin": "client_local"},
                      "state": "excluded" if excluded else "included", "exclusion_reason": "out_of_scope" if excluded else None,
                      "outcome": outcome, "verification": "test" if sequence == 1 else "unavailable",
                      "evidence_refs": ["synthetic-check-reference"] if sequence == 1 else [],
                      "cost": {"tokens": 20 if sequence == 1 else None, "elapsed_ms": None}})
    return {"schema_version": "system-change-outcome-observations/v1", "project_id": project_id,
            "proposal_id": 1, "round_key": "synthetic-round", "plan_digest": digest,
            "application_key": "apply-layout", "tasks": tasks}


class SystemEvolutionOutcomeTests(AgentMemoryTestBase):
    git = lifecycle.SystemEvolutionLifecycleTests.git
    command = lifecycle.SystemEvolutionLifecycleTests.command
    failed = lifecycle.SystemEvolutionLifecycleTests.failed
    candidate = lifecycle.SystemEvolutionLifecycleTests.candidate
    base_fixture = lifecycle.SystemEvolutionLifecycleTests.base_fixture
    fixture = lifecycle.SystemEvolutionLifecycleTests.fixture
    accept = lifecycle.SystemEvolutionLifecycleTests.accept
    apply = lifecycle.SystemEvolutionLifecycleTests.apply
    state = lifecycle.SystemEvolutionLifecycleTests.state

    def run_memory(self, project: Path, *args: str, **kwargs):
        runtime = getattr(self, "installed_runtime", None)
        if runtime is None:
            return super().run_memory(project, *args, **kwargs)
        return subprocess.run([sys.executable, str(runtime), *args, "--project", str(project),
                               "--memory-home", str(self.memory_home(project))], text=True, capture_output=True, check=True)

    def applied_fixture(self, directory: str, *, failed_monitor: bool = False, installed: bool = False):
        self.install_current_copy = installed
        root, recovery, change, candidate = self.fixture(directory, monitor_fails=failed_monitor,
                                                        prepared_artifacts={"outcome-plan.json": outcome_plan()})
        self.accept(root, change)
        self.apply(root, recovery, change)
        call = ("maintain-system-follow-up", "--id", "1", "--expected-revision", "5", "--operation-key", "observed-monitor",
                "--status", "monitoring", "--note", "Actual controlled post-application check.", "--execute")
        (self.failed if failed_monitor else self.command)(root, *call)
        digest = hashlib.sha256((root / "outcome-plan.json").read_bytes()).hexdigest()
        (root / "observations.json").write_text(json.dumps(observations(self.project_id(root), digest)), encoding="utf-8")
        return root, recovery, change

    def context(self, root: Path, *, failure: bool = False, with_observations: bool = True, **kwargs):
        args = ["maintain-system-outcome", "--id", "1", "--application-key", kwargs.get("application_key", "apply-layout"),
                "--plan-file", kwargs.get("plan_file", "outcome-plan.json")]
        if with_observations:
            args.extend(["--observations-file", "observations.json"])
        return (self.failed if failure else self.command)(root, *args)

    def test_no_archive_is_created_by_reading_missing_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "empty"
            root.mkdir()
            result = self.context(root, with_observations=False)
            self.assertFalse(result["available"])
            self.assertFalse(self.memory_home(root).exists())

    def test_actual_application_results_and_declared_window_are_bound_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change = self.applied_fixture(directory)
            self.run_memory(root, "update", "--type", "semantic", "--fact", "Synthetic outcome query isolation fact.")
            before_query = self.command(root, "context", "--query", "outcome query isolation", "--compact")
            database = self.project_memory_dir(root) / "memory.db"
            before_bytes = database.read_bytes()
            with closing(sqlite3.connect(database)) as conn:
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            result = self.context(root)
            self.assertEqual("system-change-outcome-context/v1", result["schema_version"])
            self.assertEqual(change["artifact_manifest"]["base_version"], result["binding"]["parent_base_version"])
            self.assertEqual("declared_complete", result["observations"]["window_state"])
            self.assertEqual({"presented": 3, "included": 2, "excluded": 1, "pass": 1, "fail": 0, "partial": 0, "unknown": 1},
                             result["observations"]["counts"])
            self.assertEqual({"observed_total": 20, "missing_tasks": 1}, result["observations"]["declared_task_costs"]["tokens"])
            self.assertTrue(result["execution"]["images"]["matches_applied_version"])
            self.assertEqual(0, result["execution"]["operations"][0]["results"][0]["exit_code"])
            self.assertIn("unknown_task_outcomes", result["gaps"])
            for name in ("records_written", "evidence_verified", "efficacy_verified", "promotion_eligible", "proposal_state_changed"):
                self.assertFalse(result[name])
            self.assertEqual(before_bytes, database.read_bytes())
            with closing(sqlite3.connect(database)) as conn:
                self.assertEqual(tables, conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall())
            after_query = self.command(root, "context", "--query", "outcome query isolation", "--compact")
            self.assertEqual(before_query["query_handoff"], after_query["query_handoff"])
            value = json.loads((root / "observations.json").read_text())
            value["tasks"] = value["tasks"][:1]
            (root / "observations.json").write_text(json.dumps(value))
            self.assertEqual("partial", self.context(root)["observations"]["window_state"])

    def test_installed_copy_reports_actual_failed_monitor_and_missing_observations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change = self.applied_fixture(directory, failed_monitor=True, installed=True)
            result = self.context(root, with_observations=False)
            self.assertEqual("unavailable", result["observations"]["window_state"])
            operation = result["execution"]["operations"][0]
            self.assertEqual("failed", operation["state"])
            self.assertEqual(7, operation["results"][0]["exit_code"])
            self.assertIn("output_error", operation["results"][0])
            self.assertEqual("applied", self.state(root, change)["state"])

    def test_tampered_unbound_cross_application_and_malformed_documents_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change = self.applied_fixture(directory)
            original = (root / "outcome-plan.json").read_bytes()
            (root / "outcome-plan.json").write_bytes(original + b" ")
            self.assertEqual("outcome_plan_unbound", self.context(root, failure=True)["code"])
            (root / "outcome-plan.json").write_bytes(original)
            (root / "late-plan.json").write_bytes(original)
            self.assertEqual("outcome_plan_unbound", self.context(root, failure=True, plan_file="late-plan.json")["code"])
            self.assertEqual("outcome_binding_mismatch", self.context(root, failure=True, application_key="observed-monitor")["code"])
            value = json.loads((root / "observations.json").read_text())
            value["project_id"] = "different-project"
            (root / "observations.json").write_text(json.dumps(value))
            self.assertEqual("outcome_binding_mismatch", self.context(root, failure=True)["code"])
            (root / "observations.json").write_text('{"schema_version":1,"schema_version":2}')
            self.assertIn("code", self.context(root, failure=True))
            (root / "observations.json").write_bytes(b"x" * 32769)
            self.assertIn("code", self.context(root, failure=True))

    def test_rollback_and_drift_remain_visible_without_rewriting_the_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change = self.applied_fixture(directory)
            (root / "value.txt").write_text("Controlled drift.\n")
            self.assertFalse(self.context(root)["execution"]["images"]["matches_applied_version"])
            (root / "value.txt").write_text("after\n")
            self.command(root, "maintain-system-rollback", "--id", "1", "--expected-revision", "6",
                         "--operation-key", "rollback-feedback", "--application-key", "apply-layout", "--execute")
            result = self.context(root)
            self.assertEqual("rolled_back", result["proposal"]["state"])
            self.assertTrue(result["execution"]["images"]["matches_original_version"])
            self.assertFalse(result["execution"]["images"]["matches_applied_version"])
            self.assertEqual("rollback", result["execution"]["operations"][-1]["kind"])

    def test_unknowns_exclusions_identity_and_payload_bounds_are_not_silently_dropped(self) -> None:
        plan = outcome_plan()
        sample = observations("project", "digest")
        mutations = []
        for path, value in [(('tasks', 1, 'sequence'), 3), (('tasks', 1, 'task_ref'), sample['tasks'][0]['task_ref']),
                            (('tasks', 0, 'verification'), "unavailable"), (('tasks', 0, 'cost', 'tokens'), True),
                            (('tasks', 2, 'exclusion_reason'), "undeclared"), (('tasks', 0, 'outcome'), {}),
                            (('tasks', 0, 'task_ref', 'origin'), []), (('tasks', 0, 'raw_query'), "not permitted")]:
            changed = copy.deepcopy(sample)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            mutations.append(changed)
        mutations.append({**sample, "tasks": sample["tasks"] * 7})
        for changed in mutations:
            with self.subTest(sample=changed), self.assertRaises(SystemEvolutionError):
                validate_observations(changed, plan, "project", "digest", "apply-layout")

    def test_unresolved_and_truncated_history_are_explicit_not_process_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change = self.applied_fixture(directory)
            project = resolve_project(str(root), str(self.memory_home(root)))
            current = self.state(root, change)
            # Controlled storage metadata only; these rows are not executions or real process receipts.
            for index in range(20):
                operation = reserve_operation(project, current, "metadata-" + str(index), "monitoring",
                                              {"call": {"expected_revision": 6}}, {"binding": {"application_key": "apply-layout"}})
                finish_operation(project, operation, operation["receipt"], state="failed")
            reserve_operation(project, current, "unresolved-metadata", "monitoring",
                              {"call": {"expected_revision": 6}}, {"active_check_key": "unknown-child"})
            result = self.context(root)
            self.assertTrue(result["execution"]["operations_truncated"])
            self.assertTrue(result["execution"]["unresolved_operation"])
            self.assertEqual(20, len(result["execution"]["operations"]))
            self.assertIn("unresolved_or_truncated_operation_history", result["gaps"])
            self.assertEqual("monitoring", self.state(root, change)["state"])
