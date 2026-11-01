# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Isolated immutable round ledger and migration; not a real efficacy study."""

import hashlib
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
from tests.test_system_evolution import synthetic_report
from tools.agent_memory_runtime import system_evolution_migrations as migrations
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.system_evolution_contract import SystemEvolutionError
from tools.agent_memory_runtime.system_evolution_lifecycle_store import reserve_operation
from tools.agent_memory_runtime.system_evolution_rounds import record_round
from tools.agent_memory_runtime.system_evolution_rounds_schema import TABLE, create_rounds_schema


def opening() -> dict:
    return {"schema_version": "system-evolution-round-record/v1", "kind": "open", "record_key": "open-round",
            "study_key": "synthetic-study", "round_key": "synthetic-round", "expected_revision": 0,
            "parent_round_key": None, "proposal_id": 1, "application_key": "apply-layout",
            "plan_file": "outcome-plan.json", "budget": {"max_rounds": 2, "max_assessments": 2}}


def assessment(root: Path, revision: int = 1) -> dict:
    return {"schema_version": "system-evolution-round-record/v1", "kind": "assessment", "record_key": "assess-" + str(revision),
            "study_key": "synthetic-study", "round_key": "synthetic-round", "expected_revision": revision,
            "observations_file": "observations.json", "observations_digest": hashlib.sha256((root / "observations.json").read_bytes()).hexdigest(),
            "finding": "inconclusive", "summary": "Controlled partial/unknown declarations; no efficacy claim.",
            "evidence_refs": ["synthetic-record-reference"], "additional_cost": {"tokens": None, "elapsed_ms": None}}


def decision(revision: int, choice: str = "inconclusive") -> dict:
    return {"schema_version": "system-evolution-round-record/v1", "kind": "decision", "record_key": "decision-" + choice,
            "study_key": "synthetic-study", "round_key": "synthetic-round", "expected_revision": revision,
            "assessment_revision": None if choice == "stop" else revision, "decision": choice,
            "note": "Current Agent recommendation only; no deployment or objective efficacy assertion.", "evidence_refs": []}


class SystemEvolutionRoundTests(AgentMemoryTestBase):
    def run_memory(self, project: Path, *args: str, **kwargs):
        if not getattr(self, "installed_runtime", None):
            return super().run_memory(project, *args, **kwargs)
        return subprocess.run([sys.executable, str(self.installed_runtime), *args, "--project", str(project),
                               "--memory-home", str(self.memory_home(project))], text=True, capture_output=True, check=True)

    def command(self, root, *args):
        return json.loads(self.run_memory(root, *args, "--json").stdout)

    def failed(self, root, *args):
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            self.command(root, *args)
        self.assertEqual(1, caught.exception.returncode)
        return json.loads(caught.exception.stdout)

    def fixture(self, directory: str, *, migrate: bool = True, installed: bool = False):
        owner = outcomes.SystemEvolutionOutcomeTests()
        root, recovery, change = owner.applied_fixture(directory, installed=installed)
        self.installed_runtime = getattr(owner, "installed_runtime", None)
        if migrate:
            self.command(root, "maintain-system-migrate", "--target-version", "system-rounds-v1",
                         "--backup-file", str(Path(directory) / "before-rounds.db"), "--execute")
        return root, recovery, change, owner

    def record(self, root, value, *, execute=True, failure=False):
        path = root / "round-record.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return (self.failed if failure else self.command)(root, "maintain-system-round-record", "--payload-file", str(path),
                                                        *(["--execute"] if execute else []))

    def read(self, root, *args):
        return self.command(root, "maintain-system-round", "--round-key", "synthetic-round", *args)

    def test_explicit_backup_migration_preview_and_uninitialized_read(self):
        with tempfile.TemporaryDirectory() as directory:
            empty = Path(directory) / "empty"
            empty.mkdir()
            self.assertFalse(self.command(empty, "maintain-system-round")["available"])
            self.assertFalse(self.memory_home(empty).exists())
            root, recovery, change, owner = self.fixture(directory, migrate=False)
            self.assertFalse(self.command(root, "maintain-system-round")["available"])
            self.assertEqual("schema_upgrade_required", self.record(root, opening(), failure=True)["code"])
            backup = Path(directory) / "before-rounds.db"
            args = ("maintain-system-migrate", "--target-version", "system-rounds-v1", "--backup-file", str(backup))
            self.assertFalse(self.command(root, *args)["migration_performed"])
            self.assertFalse(backup.exists())
            self.assertTrue(self.command(root, *args, "--execute")["migration_performed"])
            with closing(sqlite3.connect(backup)) as conn:
                self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name=?", (TABLE,)).fetchone())
                self.assertEqual("ok", conn.execute("PRAGMA integrity_check").fetchone()[0])
            self.assertTrue(self.command(root, *args, "--execute")["reused"])

    def test_immutable_snapshots_revisions_budgets_and_restart_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, owner = self.fixture(directory)
            self.run_memory(root, "update", "--type", "semantic", "--fact", "Synthetic round ledger query isolation fact.")
            before = self.command(root, "context", "--query", "round ledger query isolation", "--compact")
            self.assertFalse(self.record(root, opening(), execute=False)["records_written"])
            first = self.record(root, opening())
            self.assertTrue(first["records_written"])
            self.assertTrue(self.record(root, opening())["reused"])
            first_assessment = assessment(root)
            old = self.record(root, first_assessment)["event"]
            value = json.loads((root / "observations.json").read_text())
            value["tasks"][1].update(outcome="pass", verification="test", evidence_refs=["synthetic-second-check"],
                                     cost={"tokens": 10, "elapsed_ms": 100})
            value["tasks"][0]["cost"]["elapsed_ms"] = 200
            (root / "observations.json").write_text(json.dumps(value))
            second = assessment(root, 2)
            second["finding"] = "supported"
            self.record(root, second)
            exhausted = assessment(root, 3)
            self.assertEqual("round_budget_exhausted", self.record(root, exhausted, failure=True)["code"])
            adopted = self.record(root, decision(3, "adopt_candidate"))
            self.assertFalse(adopted["efficacy_verified"])
            self.assertFalse(adopted["application_performed"])
            self.assertEqual("monitoring", owner.state(root, change)["state"])
            (root / "outcome-plan.json").unlink()
            (root / "observations.json").unlink()
            self.assertTrue(self.record(root, first_assessment)["reused"])
            historical = self.read(root, "--revision", "2")["event"]
            self.assertEqual(old, historical)
            self.assertEqual(1, historical["receipt"]["context"]["observations"]["counts"]["unknown"])
            self.assertEqual("decided", self.read(root)["event"]["receipt"]["state"])
            self.assertTrue(self.read(root, "--limit", "1")["history_truncated"])
            changed = {**first_assessment, "summary": "A different immutable opinion."}
            self.assertEqual("round_key_conflict", self.record(root, changed, failure=True)["code"])
            with closing(sqlite3.connect(self.project_memory_dir(root) / "memory.db")) as conn:
                for sql in (f"UPDATE {TABLE} SET revision=9", f"DELETE FROM {TABLE}"):
                    with self.assertRaises(sqlite3.IntegrityError):
                        conn.execute(sql)
                    conn.rollback()
            after = self.command(root, "context", "--query", "round ledger query isolation", "--compact")
            self.assertEqual(before["query_handoff"], after["query_handoff"])

    def test_unresolved_work_blocks_assessment_but_stop_does_not_clear_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, owner = self.fixture(directory)
            self.record(root, opening())
            project = resolve_project(str(root), str(self.memory_home(root)))
            current = owner.state(root, change)
            # Controlled unresolved metadata, not a claim about an actual running child.
            reserve_operation(project, current, "unknown-round-work", "monitoring",
                              {"call": {"expected_revision": current["state_revision"]}}, {"active_check_key": "unknown"})
            self.assertEqual("schema_work_in_progress", self.record(root, assessment(root), failure=True)["code"])
            self.record(root, decision(1, "stop"))
            operation = self.command(root, "maintain-system", "--operation-key", "unknown-round-work")["operation"]
            self.assertEqual("running", operation["state"])

    def test_concurrent_assessments_use_revision_compare_and_swap(self):
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, owner = self.fixture(directory)
            self.record(root, opening())
            project = resolve_project(str(root), str(self.memory_home(root)))
            request = assessment(root)
            def run(index):
                try:
                    return record_round(project, {**request, "record_key": "concurrent-" + str(index)}, True)["records_written"]
                except SystemEvolutionError as error:
                    return error.code
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(run, range(2)))
            self.assertCountEqual([True, "round_revision_conflict"], results)
            self.assertEqual(2, self.read(root)["event"]["revision"])

    def test_failed_schema_install_rolls_back_actual_ddl_and_preserves_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, owner = self.fixture(directory, migrate=False)
            project = resolve_project(str(root), str(self.memory_home(root)))
            backup = Path(directory) / "interrupted-rounds.db"
            def fail(conn):
                create_rounds_schema(conn)
                raise RuntimeError("Controlled interruption after round DDL")
            with patch.object(migrations, "create_rounds_schema", side_effect=fail):
                with self.assertRaisesRegex(RuntimeError, "Controlled interruption"):
                    migrations.migrate_governance(project, "system-rounds-v1", str(backup), True)
            for path in (backup, project.db_path):
                with closing(sqlite3.connect(path)) as conn:
                    self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name=?", (TABLE,)).fetchone())
                    self.assertIsNone(conn.execute("SELECT version FROM runtime_schema_versions WHERE component='system_evolution_rounds'").fetchone())
                    self.assertEqual("ok", conn.execute("PRAGMA integrity_check").fetchone()[0])

    def test_installed_copy_and_actual_old_runtime_preserve_round_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, owner = self.fixture(directory, installed=True)
            self.record(root, opening())
            old = Path(directory) / "old-runtime"
            old.mkdir()
            repository = Path(__file__).resolve().parents[1]
            env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_LAZY_FETCH="1")
            raw = subprocess.check_output(["git", "-c", "protocol.allow=never", "archive", "--format=tar", "4d5e068e68a107437aee2df7edd39acb595d311f", "tools"], cwd=repository, env=env)
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
            subprocess.run([sys.executable, str(old / "tools/agent_memory.py"), "update", "--project", str(root),
                            "--memory-home", str(self.memory_home(root)), "--type", "semantic", "--fact", "Synthetic old writer after round migration."],
                           check=True, capture_output=True)
            self.assertEqual(1, len(self.list_records(root, "semantic")))
            old_query = subprocess.run([sys.executable, str(old / "tools/agent_memory.py"), "context", "--project", str(root),
                                       "--memory-home", str(self.memory_home(root)), "--query", "old writer round migration", "--compact", "--json"],
                                      check=True, capture_output=True, text=True)
            current = self.command(root, "context", "--query", "old writer round migration", "--compact")
            self.assertEqual(json.loads(old_query.stdout)["query_handoff"], current["query_handoff"])
            self.assertEqual(1, self.read(root)["event"]["revision"])

    def test_invalid_revisions_digest_and_incomplete_adoption_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, owner = self.fixture(directory)
            self.record(root, opening())
            invalid = assessment(root)
            invalid["observations_digest"] = "0" * 64
            self.assertEqual("round_binding_mismatch", self.record(root, invalid, failure=True)["code"])
            invalid = assessment(root)
            invalid["expected_revision"] = True
            self.assertIn("code", self.record(root, invalid, failure=True))
            opinion = assessment(root)
            opinion["finding"] = "supported"
            self.record(root, opinion)
            self.assertEqual("round_decision_incomplete", self.record(root, decision(2, "adopt_candidate"), failure=True)["code"])
            self.record(root, decision(2))
            self.assertEqual("round_no_new_input", self.record(root, assessment(root, 3), failure=True)["code"])
            value = json.loads((root / "observations.json").read_text())
            value["tasks"][1].update(outcome="fail", verification="test", evidence_refs=["synthetic-later-counterexample"])
            (root / "observations.json").write_text(json.dumps(value))
            late = assessment(root, 3)
            late["finding"] = "contradicted"
            event = self.record(root, late)["event"]
            self.assertTrue(event["receipt"]["late_assessment"])
            self.assertEqual("decided", event["receipt"]["state"])
            self.assertEqual("inconclusive", event["receipt"]["decision"])
            self.assertEqual(3, event["receipt"]["decision_revision"])
            self.assertEqual("round_closed", self.record(root, decision(4, "keep_baseline"), failure=True)["code"])

    def test_parent_lineage_frozen_budget_and_exhaustion_use_a_second_actual_application(self):
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, owner = self.fixture(directory)
            original_plan = (root / "outcome-plan.json").read_bytes()
            self.record(root, opening())
            self.record(root, assessment(root))
            self.record(root, decision(2, "rollback"))
            self.assertEqual("after\n", (root / "value.txt").read_text())
            owner.command(root, "maintain-system-rollback", "--id", "1", "--expected-revision", "6",
                          "--operation-key", "parent-code-rollback", "--application-key", "apply-layout", "--execute")
            report = synthetic_report()
            report["task_ref"] = {"key": "synthetic-child-task", "origin": "client_local"}
            report["change_proposals"][0]["acceptance_criteria"] = ["Observe the controlled candidate after-file layout."]
            saved = owner.command(root, "reflect-system", "--review-key", "child-review", "--payload", json.dumps(report))
            proposal_id = saved["proposal_id"]
            plan = outcomes.outcome_plan()
            plan.update(proposal_id=proposal_id, prepared_state_revision=2, round_key="child-round")
            (root / "outcome-plan.json").write_text(json.dumps(plan))
            accept = json.loads((root / "acceptance.json").read_text())
            accept.update(proposal_id=proposal_id, prepared_state_revision=2)
            for item in accept["gates"] + accept["criteria"]:
                item["run_key"] = "child-run"
            (root / "acceptance.json").write_text(json.dumps(accept))
            prepared = owner.command(root, "maintain-system-status", "--id", str(proposal_id), "--expected-revision", "1",
                                     "--status", "prepared", "--note", "Predeclare the second controlled round.", "--development-root", str(root),
                                     "--base-version", change["artifact_manifest"]["base_version"], "--artifact-file", "candidate.patch",
                                     "--artifact-file", "acceptance.json", "--artifact-file", "outcome-plan.json")["change"]
            candidate = owner.candidate(root, Path(directory) / "candidates", prepared, key="child-candidate", execute=True)["candidate"]
            check = json.loads((root / "plan.json").read_text())
            check.update(proposal_id=proposal_id, prepared_state_revision=2, artifact_digest=prepared["artifact_digest"],
                         candidate_key="child-candidate", candidate_digest=candidate["receipt"]["candidate_digest"])
            (root / "child-check.json").write_text(json.dumps(check))
            owner.command(root, "maintain-system-check", "--id", str(proposal_id), "--expected-revision", "2",
                          "--run-key", "child-run", "--plan-file", str(root / "child-check.json"), "--execute")
            review = json.loads((root / "review.json").read_text())
            review.update(proposal_id=proposal_id, prepared_state_revision=2, candidate_key="child-candidate",
                          candidate_digest=candidate["receipt"]["candidate_digest"])
            (root / "child-review.json").write_text(json.dumps(review))
            owner.command(root, "maintain-system-accept", "--id", str(proposal_id), "--expected-revision", "2",
                          "--operation-key", "child-accept", "--acceptance-file", "acceptance.json", "--review-file", "child-review.json", "--execute")
            owner.command(root, "maintain-system-apply", "--id", str(proposal_id), "--expected-revision", "3",
                          "--operation-key", "child-apply", "--target-root", str(root), "--recovery-home", str(recovery), "--execute")
            child = {**opening(), "record_key": "open-child", "round_key": "child-round", "parent_round_key": "synthetic-round",
                     "proposal_id": proposal_id, "application_key": "child-apply"}
            changed = {**child, "budget": {"max_rounds": 3, "max_assessments": 2}}
            self.assertEqual("round_budget_conflict", self.record(root, changed, failure=True)["code"])
            event = self.record(root, child)["event"]
            self.assertEqual(2, event["receipt"]["round_index"])
            self.assertEqual("synthetic-round", event["receipt"]["opening"]["parent_round_key"])
            (root / "outcome-plan.json").write_bytes(original_plan)
            late = assessment(root, 3)
            late["finding"] = "contradicted"
            self.record(root, late)
            third = {**child, "record_key": "open-third", "round_key": "third-round", "parent_round_key": "child-round"}
            self.assertEqual("round_budget_exhausted", self.record(root, third, failure=True)["code"])
            self.assertEqual("rollback", self.read(root)["event"]["receipt"]["decision"])

    def test_stop_and_unknown_schema_do_not_silently_resume_or_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, owner = self.fixture(directory)
            self.record(root, opening())
            self.record(root, decision(1, "stop"))
            self.assertEqual("round_closed", self.record(root, assessment(root, 2), failure=True)["code"])
            child = {**opening(), "record_key": "after-stop", "round_key": "after-stop", "parent_round_key": "synthetic-round"}
            self.assertEqual("round_parent_conflict", self.record(root, child, failure=True)["code"])
            database = self.project_memory_dir(root) / "memory.db"
            with closing(sqlite3.connect(database)) as conn:
                conn.execute("UPDATE runtime_schema_versions SET version='future-rounds' WHERE component='system_evolution_rounds'")
                conn.commit()
            self.assertEqual("round_schema_unsupported", self.failed(root, "maintain-system-round")["code"])
            with closing(sqlite3.connect(database)) as conn:
                conn.execute("UPDATE runtime_schema_versions SET version='system-rounds-v1' WHERE component='system_evolution_rounds'")
                conn.execute("DROP TRIGGER system_rounds_no_update")
                conn.commit()
            self.assertEqual("round_schema_unsupported", self.failed(root, "maintain-system-round")["code"])
