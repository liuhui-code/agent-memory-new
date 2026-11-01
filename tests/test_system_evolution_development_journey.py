# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Two-round installed R1–R4 journey; synthetic declarations, actual local effects."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests import test_system_evolution_handoffs as handoff_fixtures
from tests import test_system_evolution_handoffs_host as host_helpers
from tests import test_system_evolution_outcomes as outcome_fixtures
from tests import test_system_evolution_rounds as round_fixtures
from tests.test_system_evolution import synthetic_report


class SystemEvolutionDevelopmentJourneyTests(AgentMemoryTestBase):
    def stage(self, name, **facts):
        self.evidence["stages"].append({"name": name, **facts})

    def write_json(self, root, name, value):
        path = root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def child_application(self, directory, root, owner, parent, candidate_driver):
        self.evidence["current_step"] = "prepare_check_accept_apply_child"
        report = synthetic_report()
        report["task_ref"] = {"origin": "client_local", "key": "controlled-child-proposal-task"}
        report["change_proposals"][0]["acceptance_criteria"] = ["Observe the controlled candidate after-file layout."]
        saved = owner.command(root, "reflect-system", "--review-key", "controlled-child-review", "--payload", json.dumps(report))
        proposal_id = saved["proposal_id"]
        plan = handoff_fixtures.host_plan()
        plan.update(proposal_id=proposal_id, prepared_state_revision=2, round_key="controlled-child-round")
        plan["window"]["key"] = "controlled-child-window"
        self.write_json(root, "child-outcome-plan.json", plan)
        acceptance = json.loads((root / "acceptance.json").read_text())
        acceptance.update(proposal_id=proposal_id, prepared_state_revision=2)
        for item in acceptance["gates"] + acceptance["criteria"]:
            item["run_key"] = "controlled-child-run"
        monitor = acceptance["follow_up"]["checks"][0]
        monitor["argv"][-1] = "controlled-child-monitor"
        monitor["result_files"] = ["controlled-child-monitor.json"]
        self.write_json(root, "child-acceptance.json", acceptance)
        prepared = owner.command(root, "maintain-system-status", "--id", str(proposal_id), "--expected-revision", "1",
                                 "--status", "prepared", "--note", "Controlled pre-bound child, not real efficacy.",
                                 "--development-root", str(root), "--base-version", parent["artifact_manifest"]["base_version"],
                                 "--artifact-file", "candidate.patch", "--artifact-file", "child-acceptance.json",
                                 "--artifact-file", "child-outcome-plan.json")["change"]
        candidate = candidate_driver.candidate(root, Path(directory) / "candidates", prepared,
                                               key="controlled-child-candidate", execute=True)["candidate"]
        checks = json.loads((root / "plan.json").read_text())
        checks.update(proposal_id=proposal_id, prepared_state_revision=2, artifact_digest=prepared["artifact_digest"],
                      candidate_key="controlled-child-candidate", candidate_digest=candidate["receipt"]["candidate_digest"])
        check_file = self.write_json(root, "child-check.json", checks)
        owner.command(root, "maintain-system-check", "--id", str(proposal_id), "--expected-revision", "2",
                      "--run-key", "controlled-child-run", "--plan-file", str(check_file), "--execute")
        review = json.loads((root / "review.json").read_text())
        review.update(proposal_id=proposal_id, prepared_state_revision=2, candidate_key="controlled-child-candidate",
                      candidate_digest=candidate["receipt"]["candidate_digest"])
        self.write_json(root, "child-accept-review.json", review)
        owner.command(root, "maintain-system-accept", "--id", str(proposal_id), "--expected-revision", "2",
                      "--operation-key", "controlled-child-accept", "--acceptance-file", "child-acceptance.json",
                      "--review-file", "child-accept-review.json", "--execute")
        owner.command(root, "maintain-system-apply", "--id", str(proposal_id), "--expected-revision", "3",
                      "--operation-key", "controlled-child-apply", "--target-root", str(root),
                      "--recovery-home", str(Path(directory) / "recovery"), "--execute")
        owner.command(root, "maintain-system-follow-up", "--id", str(proposal_id), "--expected-revision", "4",
                      "--operation-key", "controlled-child-monitor", "--status", "monitoring",
                      "--note", "Actual controlled child monitor, not real-task efficacy.", "--execute")
        digest = hashlib.sha256((root / "child-outcome-plan.json").read_bytes()).hexdigest()
        observed = outcome_fixtures.observations(self.project_id(root), digest)
        observed.update(proposal_id=proposal_id, round_key="controlled-child-round", application_key="controlled-child-apply")
        for task in observed["tasks"]:
            task["task_ref"]["key"] = "controlled-child-declaration-" + str(task["sequence"])
        self.write_json(root, "child-observations.json", observed)
        opening = {**round_fixtures.opening(), "record_key": "controlled-open-child", "round_key": "controlled-child-round",
                   "parent_round_key": "synthetic-round", "proposal_id": proposal_id,
                   "application_key": "controlled-child-apply", "plan_file": "child-outcome-plan.json"}
        event = owner.record(root, opening)["event"]
        self.assertEqual(2, event["receipt"]["round_index"])
        self.assertEqual("synthetic-round", event["receipt"]["opening"]["parent_round_key"])
        return proposal_id, opening

    def test_installed_two_round_journey_preserves_history_query_and_memory(self):
        self.evidence = {"schema_version": "system-meta-development-journey/v1", "outcome": "not_completed",
                         "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         "scope": "controlled_two_round_installed_runtime", "production_or_sealed_evaluation": False,
                         "task_material": "synthetic_declarations_not_independent_efficacy_samples",
                         "model_invoked_by_driver": False, "efficacy_verified": False, "stages": []}
        outer = None
        try:
            with tempfile.TemporaryDirectory(prefix="memory-development-journey-") as directory:
                outer = Path(directory)
                driver = handoff_fixtures.SystemEvolutionHandoffTests()
                self.evidence["current_step"] = "install_and_apply_parent"
                root, owner, parent, applied = driver.fixture(directory, installed=True)
                repository = Path(__file__).resolve().parents[1]
                source_bundle = host_helpers.bundle_digest(repository, repository / "skills")
                self.assertEqual(source_bundle, host_helpers.bundle_digest(root, root / ".agents/skills"))
                self.evidence["runtime_skill_bundle_digest"] = source_bundle
                self.stage("installed_parent_application", state=applied.state(root, parent)["state"], bundle_matched=True)
                self.evidence["current_step"] = "post_parent_memory_write"
                owner.run_memory(root, "update", "--type", "semantic", "--fact", "Controlled journey Memory write after parent application.")

                self.evidence["current_step"] = "parent_window_handoff"
                parent_claim = driver.handoff(root)["handoff"]["claim"]
                parent_save = handoff_fixtures.completed(parent_claim)
                self.assertEqual("recorded", driver.handoff(root, parent_save)["decision"])
                owner.record(root, round_fixtures.decision(2, "rollback"))
                self.assertEqual("after\n", (root / "value.txt").read_text())
                self.stage("parent_assessment_and_advisory_decision", round_revision=3, actual_code_still_applied=True)
                self.evidence["current_step"] = "actual_parent_rollback"
                owner.command(root, "maintain-system-rollback", "--id", "1", "--expected-revision", "6",
                              "--operation-key", "controlled-parent-rollback", "--application-key", "apply-layout", "--execute")
                self.assertEqual("before\n", (root / "value.txt").read_text())
                self.assertEqual(1, len(owner.list_records(root, "semantic")))
                self.stage("actual_parent_rollback", code_restored=True, later_memory_write_preserved=True)

                child_id, child_opening = self.child_application(directory, root, owner, parent, applied)
                owner.run_memory(root, "update", "--type", "semantic", "--fact", "Controlled journey Memory write after child application.")
                query = owner.command(root, "context", "--query", "Controlled journey Memory write", "--compact")["query_handoff"]
                self.stage("actual_child_application_and_linkage", proposal_id=child_id, round_index=2, distinct_task_declarations=True)
                self.evidence["current_step"] = "shared_task_deduplication"
                child_request = {**handoff_fixtures.claim_request(), "round_key": "controlled-child-round",
                                 "observations_file": "child-observations.json"}
                self.assertEqual("task_review_already_consumed", driver.handoff(root, child_request)["reason"])
                child_request["task_ref"] = {"origin": "client_local", "key": "controlled-child-window-boundary"}
                granted = driver.handoff(root, child_request)
                self.assertTrue(granted["should_review"])
                child_claim = granted["handoff"]["claim"]
                self.stage("distinct_window_claim", same_task_rejected=True, new_task_granted_once=True)

                self.evidence["current_step"] = "late_parent_counter_declaration"
                later = json.loads((root / "observations.json").read_text())
                later["tasks"][1].update(outcome="fail", verification="test", evidence_refs=["controlled-late-counter-declaration"])
                self.write_json(root, "observations.json", later)
                assessment = round_fixtures.assessment(root, 3)
                assessment["finding"] = "contradicted"
                late = owner.record(root, assessment)["event"]
                self.assertEqual("rollback", late["receipt"]["decision"])
                self.assertEqual(3, late["receipt"]["decision_revision"])
                self.assertTrue(late["receipt"]["late_assessment"])
                self.assertEqual("rolled_back", late["receipt"]["context"]["proposal"]["state"])
                self.assertTrue(any(item["kind"] == "rollback" and item["state"] == "completed"
                                    for item in late["receipt"]["context"]["execution"]["operations"]))
                self.stage("late_parent_counter_declaration", original_decision_retained=True, actual_rollback_retained=True)

                self.evidence["current_step"] = "complete_child_after_parent_feedback"
                child_save = handoff_fixtures.completed(child_claim)
                child_save["round_key"] = "controlled-child-round"
                self.assertEqual("recorded", driver.handoff(root, child_save)["decision"])
                stop = {**round_fixtures.decision(2, "stop"), "round_key": "controlled-child-round",
                        "record_key": "controlled-stop-child"}
                owner.record(root, stop)
                forbidden = {**child_save["assessment"], "expected_revision": 3, "record_key": "controlled-no-resume"}
                self.assertEqual("round_closed", owner.record(root, forbidden, failure=True)["code"])
                third = {**child_opening, "record_key": "controlled-no-third", "round_key": "controlled-third-round",
                         "parent_round_key": "controlled-child-round"}
                self.assertEqual("round_budget_exhausted", owner.record(root, third, failure=True)["code"])
                self.stage("child_completion_and_stop", parent_feedback_did_not_invalidate_child=True,
                           stopped_round_rejected=True, third_round_budget_rejected=True)

                self.evidence["current_step"] = "actual_child_rollback_and_history"
                owner.command(root, "maintain-system-rollback", "--id", str(child_id), "--expected-revision", "5",
                              "--operation-key", "controlled-child-rollback", "--application-key", "controlled-child-apply", "--execute")
                self.assertEqual("before\n", (root / "value.txt").read_text())
                self.assertEqual(2, len(owner.list_records(root, "semantic")))
                for name in ("outcome-plan.json", "observations.json", "child-outcome-plan.json", "child-observations.json"):
                    (root / name).unlink()
                self.assertTrue(driver.handoff(root, parent_save)["reused"])
                self.assertTrue(driver.handoff(root, child_save)["reused"])
                old = owner.read(root, "--revision", "2")["event"]
                self.assertEqual(1, old["receipt"]["context"]["observations"]["counts"]["unknown"])
                self.assertEqual("rollback", owner.read(root)["event"]["receipt"]["decision"])
                self.stage("code_recovery_and_historical_reads", both_later_memory_writes_preserved=True,
                           deleted_inputs_did_not_break_history=True, old_unknown_retained=True)

                self.evidence["current_step"] = "r4_no_go_and_query_isolation"
                database = owner.project_memory_dir(root) / "memory.db"
                before = hashlib.sha256(database.read_bytes()).hexdigest()
                readiness = owner.command(root, "maintain-system-campaign-readiness")
                self.assertEqual("no_go", readiness["decision"])
                self.assertEqual(before, hashlib.sha256(database.read_bytes()).hexdigest())
                after = owner.command(root, "context", "--query", "Controlled journey Memory write", "--compact")["query_handoff"]
                self.assertEqual(query, after)
                self.assertFalse(readiness["activity_started"])
                self.stage("readiness_and_query_isolation", readiness="no_go", readiness_did_not_write=True,
                           query_handoff_unchanged=True, real_activity_started=False)
                self.evidence.update(outcome="passed", completed_rounds=2, semantic_writes_preserved=2,
                                     runtime_code_digest=readiness["runtime_identity"]["code_digest"])
        except BaseException as error:
            self.evidence.update(outcome="failed", failure_type=type(error).__name__)
            if isinstance(error, subprocess.CalledProcessError):
                try:
                    self.evidence["runtime_error_code"] = json.loads(error.stdout)["code"]
                except (ValueError, KeyError, TypeError):
                    pass
            raise
        finally:
            self.evidence["temporary_root_cleanup_completed"] = outer is not None and not outer.exists()
            target = os.environ.get("AGENT_MEMORY_DEVELOPMENT_JOURNEY_EVIDENCE")
            if target:
                Path(target).write_text(json.dumps(self.evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
