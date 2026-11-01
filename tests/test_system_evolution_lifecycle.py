# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Synthetic file-rule lifecycle, actual file/SQLite effects, no real-user case claims."""

from __future__ import annotations

import hashlib
import json
import os
import select
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests import test_system_evolution_candidates as fixtures
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime import system_evolution_application as application
from tools.agent_memory_runtime.system_evolution_check_process import stop_process
from tools.agent_memory_runtime.system_evolution_lifecycle_store import reserve_operation


CHECK = '''import json, subprocess, sys
from pathlib import Path
gate = sys.argv[1]
observed = {"value": Path("value.txt").read_text(), "added": Path("added.txt").is_file(), "deleted": not Path("delete.txt").exists()}
assert observed == {"value": "after\\n", "added": True, "deleted": True}
if gate == "negative_cases":
    assert observed["value"] != "before\\n" and not Path("delete.txt").exists()
elif gate == "compatibility":
    assert set(observed) == {"value", "added", "deleted"} and Path("check.py").is_file()
elif gate == "cost":
    assert sum(Path(name).stat().st_size for name in ("value.txt", "added.txt")) < 1024
elif gate == "rollback":
    assert subprocess.check_output(["git", "show", "HEAD:value.txt"]) == b"before\\n"
if gate == "monitor-fail":
    raise SystemExit(7)
Path(gate + ".json").write_text(json.dumps({"schema_version": "synthetic-file-rule/v1", "gate": gate, "observed": observed}))
'''


class SystemEvolutionLifecycleTests(AgentMemoryTestBase):
    git = fixtures.SystemEvolutionCandidateTests.git
    command = fixtures.SystemEvolutionCandidateTests.command
    failed = fixtures.SystemEvolutionCandidateTests.failed
    candidate = fixtures.SystemEvolutionCandidateTests.candidate
    base_fixture = fixtures.SystemEvolutionCandidateTests.fixture

    def run_memory(self, project: Path, *args: str, **kwargs):
        runtime = getattr(self, "installed_runtime", None)
        if runtime is None:
            return super().run_memory(project, *args, **kwargs)
        return subprocess.run([sys.executable, str(runtime), *args, "--project", str(project),
                               "--memory-home", str(self.memory_home(project))], text=True, capture_output=True, check=True)

    def fixture(self, directory: str, *, monitor_fails: bool = False,
                prepared_artifacts: dict[str, dict] | None = None) -> tuple[Path, Path, dict, dict]:
        root, home, change = self.base_fixture(directory, check_script=CHECK,
                                               baseline_files=getattr(self, "baseline_files", None),
                                               candidate_files=getattr(self, "candidate_files", None),
                                               baseline_modes=getattr(self, "baseline_modes", None))
        if getattr(self, "install_current_copy", False):
            installer = Path(__file__).resolve().parents[1] / "install.py"
            subprocess.run([sys.executable, str(installer), "--project", str(root), "--memory-home", str(self.memory_home(root))],
                           check=True, capture_output=True)
            self.installed_runtime = root / "tools/agent_memory.py"
        source = [{"path": "check.py", "digest": hashlib.sha256(CHECK.encode()).hexdigest()}]
        gates = ["functionality", "negative_cases", "compatibility", "cost", "rollback"]
        checks = [{"key": gate, "argv": [sys.executable, "check.py", gate], "assertion_indices": [0],
                   "timeout_seconds": 5, "result_files": [gate + ".json"]} for gate in gates]
        accept = {"schema_version": "system-change-acceptance-plan/v1", "proposal_id": change["id"],
                  "prepared_state_revision": 3,
                  "gates": [{"key": gate, "run_key": "lifecycle-run", "check_key": gate, "result_file": gate + ".json"} for gate in gates],
                  "criteria": [{"index": 0, "run_key": "lifecycle-run", "check_key": "functionality", "result_file": "functionality.json"}],
                  "follow_up": {"source_files": source, "checks": [{"key": "monitor", "argv": [sys.executable, "check.py", "monitor-fail" if monitor_fails else "monitor"],
                       "assertion_indices": [0], "timeout_seconds": 5, "result_files": ["monitor.json"]}],
                       "close_condition": "One declared synthetic layout check passes on the actual applied directory; no efficacy claim."}}
        (root / "acceptance.json").write_text(json.dumps(accept), encoding="utf-8")
        extra = []
        for name, document in (prepared_artifacts or {}).items():
            (root / name).write_text(json.dumps(document), encoding="utf-8")
            extra.extend(["--artifact-file", name])
        change = self.command(root, "maintain-system-status", "--id", str(change["id"]), "--expected-revision", "2",
                              "--status", "prepared", "--note", "Predeclare synthetic acceptance and follow-up.",
                              "--development-root", str(root), "--base-version", change["artifact_manifest"]["base_version"],
                              "--artifact-file", "candidate.patch", "--artifact-file", "acceptance.json", *extra)["change"]
        candidate = self.candidate(root, home, change, execute=True)["candidate"]
        plan = {"schema_version": "system-change-check-plan/v3", "proposal_id": change["id"], "prepared_state_revision": 3,
                "artifact_digest": change["artifact_digest"], "candidate_key": candidate["candidate_key"],
                "candidate_digest": candidate["receipt"]["candidate_digest"], "source_files": source, "checks": checks}
        (root / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        self.command(root, "maintain-system-check", "--id", str(change["id"]), "--expected-revision", "3",
                     "--run-key", "lifecycle-run", "--plan-file", str(root / "plan.json"), "--execute")
        review = {"schema_version": "system-change-acceptance-review/v1", "proposal_id": change["id"], "prepared_state_revision": 3,
                  "candidate_key": candidate["candidate_key"], "candidate_digest": candidate["receipt"]["candidate_digest"],
                  "reviewer_ref": "synthetic-fixture-not-a-real-model-review",
                  "criterion_reviews": [{"index": 0, "reason": "Controlled script reads the three actual candidate paths and asserts their declared layout."}],
                  "gate_reviews": [{"key": gate, "reason": "Synthetic scoped " + gate + " assertion; not a production or external gate."} for gate in gates],
                  "source_use_review": "The declared local check.py executes in the candidate. Its digest is bound; this fixture does not authenticate a real reviewer."}
        (root / "review.json").write_text(json.dumps(review), encoding="utf-8")
        self.command(root, "maintain-system-migrate", "--target-version", "system-evolution-v2",
                     "--backup-file", str(Path(directory) / "before-lifecycle.db"), "--execute")
        recovery = Path(directory) / "recovery"
        recovery.mkdir()
        return root, recovery, change, candidate

    def accept(self, root: Path, change: dict, execute: bool = True, failure: bool = False) -> dict:
        args = ["maintain-system-accept", "--id", str(change["id"]), "--expected-revision", "3", "--operation-key", "accept-layout",
                "--acceptance-file", "acceptance.json", "--review-file", "review.json"]
        return (self.failed if failure else self.command)(root, *args, *(["--execute"] if execute else []))

    def apply(self, root: Path, recovery: Path, change: dict, execute: bool = True, failure: bool = False) -> dict:
        args = ["maintain-system-apply", "--id", str(change["id"]), "--expected-revision", "4", "--operation-key", "apply-layout",
                "--target-root", str(root), "--recovery-home", str(recovery)]
        return (self.failed if failure else self.command)(root, *args, *(["--execute"] if execute else []))

    def state(self, root: Path, change: dict) -> dict:
        return self.command(root, "maintain-system", "--change-id", str(change["id"]))["change"]

    def _full_lifecycle_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, candidate = self.fixture(directory)
            self.assertFalse(self.accept(root, change, execute=False)["proposal_state_changed"])
            self.assertEqual("prepared", self.state(root, change)["state"])
            accepted = self.accept(root, change)
            self.assertFalse(accepted["promotion_eligible"])
            self.assertEqual("checked", self.state(root, change)["state"])
            refused = self.failed(root, "maintain-system-migrate", "--target-version", "system-evolution-v1",
                                  "--backup-file", str(Path(directory) / "blocked-downgrade.db"), "--execute")
            self.assertEqual("schema_downgrade_blocked", refused["code"])
            self.assertEqual("checked", self.state(root, change)["state"])
            self.assertTrue(self.accept(root, change)["reused"])
            os.chmod(root / "value.txt", 0o600)
            index_before = self.git(root, "diff", "--cached", "--binary")
            self.assertFalse(self.apply(root, recovery, change, execute=False)["application_performed"])
            self.assertEqual("before\n", (root / "value.txt").read_text())

            applied = self.apply(root, recovery, change)
            self.assertTrue(applied["application_performed"])
            self.assertEqual("after\n", (root / "value.txt").read_text())
            self.assertEqual(0o600, (root / "value.txt").stat().st_mode & 0o777)
            self.assertFalse((root / "delete.txt").exists())
            self.assertTrue((root / "added.txt").exists())
            self.assertEqual(index_before, self.git(root, "diff", "--cached", "--binary"))
            self.run_memory(root, "update", "--type", "semantic", "--fact", "Synthetic write after actual code application.")
            for status, revision in (("monitoring", 5), ("closed", 6)):
                result = self.command(root, "maintain-system-follow-up", "--id", str(change["id"]), "--expected-revision", str(revision),
                                      "--operation-key", status + "-layout", "--status", status, "--note", "Controlled follow-up only.", "--execute")
                self.assertEqual("completed", result["operation"]["state"])
                self.assertEqual(status, self.state(root, change)["state"])
            rolled = self.command(root, "maintain-system-rollback", "--id", str(change["id"]), "--expected-revision", "7",
                                  "--operation-key", "rollback-layout", "--application-key", "apply-layout", "--execute")
            self.assertTrue(rolled["operation"]["receipt"]["code_rollback_performed"])
            self.assertEqual("rolled_back", self.state(root, change)["state"])
            self.assertEqual("before\n", (root / "value.txt").read_text())
            self.assertEqual(0o600, (root / "value.txt").stat().st_mode & 0o777)
            self.assertEqual("remove\n", (root / "delete.txt").read_text())
            self.assertFalse((root / "added.txt").exists())
            self.assertEqual(1, len(self.list_records(root, "semantic")))
            self.assertTrue((root / "monitor.json").exists())
            self.assertTrue(self.apply(root, recovery, change)["reused"])
            self.assertEqual("before\n", (root / "value.txt").read_text())

    def test_accept_apply_monitor_close_and_actual_rollback_preserve_archive_writes(self) -> None:
        self._full_lifecycle_case()

    def test_installed_copy_runs_the_complete_lifecycle(self) -> None:
        self.install_current_copy = True
        self._full_lifecycle_case()

    def test_interruption_after_a_file_write_resumes_without_repeating_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, candidate = self.fixture(directory)
            self.accept(root, change)
            project = resolve_project(str(root), str(self.memory_home(root)))
            original = application.replace_file
            writes = []
            def interrupt(target, desired, raw, permissions=None):
                original(target, desired, raw, permissions)
                writes.append(desired["path"])
                raise RuntimeError("Controlled interruption after atomic replacement")
            with patch.object(application, "replace_file", side_effect=interrupt):
                with self.assertRaisesRegex(RuntimeError, "Controlled interruption"):
                    application.apply_change(project, change["id"], 4, "apply-layout", str(root), str(recovery), True)
            self.assertEqual("checked", self.state(root, change)["state"])
            self.assertEqual("interrupted", self.command(root, "maintain-system", "--operation-key", "apply-layout")["operation"]["state"])
            with patch.object(application, "replace_file", wraps=original) as resumed:
                application.resume_application(project, "apply-layout", True)
                self.assertNotIn(writes[0], [call.args[1]["path"] for call in resumed.call_args_list])
            self.assertEqual("applied", self.state(root, change)["state"])
            self.assertEqual("after\n", (root / "value.txt").read_text())

    def test_changed_observed_result_prevents_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, candidate = self.fixture(directory)
            (Path(candidate["receipt"]["binding"]["root"]) / "functionality.json").write_text("Changed controlled output.", encoding="utf-8")
            self.assertEqual("acceptance_result_changed", self.accept(root, change, failure=True)["code"])
            self.assertEqual("prepared", self.state(root, change)["state"])

    def test_live_writer_lock_and_hard_process_exit_are_recovered_from_actual_images(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, candidate = self.fixture(directory)
            self.accept(root, change)
            source = Path(__file__).resolve().parents[1]
            arguments = [str(source / "tools/agent_memory.py"), "maintain-system-apply", "--id", str(change["id"]),
                         "--expected-revision", "4", "--operation-key", "hard-crash-apply", "--target-root", str(root),
                         "--recovery-home", str(recovery), "--project", str(root), "--memory-home", str(self.memory_home(root)), "--execute", "--json"]
            script = ("import os, runpy, sys\n"
                      f"sys.path.insert(0, {str(source / 'tools')!r})\n"
                      "import agent_memory_runtime.system_evolution_application as application\n"
                      "original = application.replace_file\n"
                      "def controlled_exit(*args, **kwargs):\n"
                      "    original(*args, **kwargs)\n"
                      "    print('FILE_WRITTEN', flush=True)\n"
                      "    sys.stdin.buffer.read(1)\n"
                      "    os._exit(77)\n"
                      "application.replace_file = controlled_exit\n"
                      f"sys.argv = {arguments!r}\n"
                      f"runpy.run_path({arguments[0]!r}, run_name='__main__')\n")
            process = subprocess.Popen([sys.executable, "-c", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, cwd=source, start_new_session=True)
            try:
                ready, _, _ = select.select([process.stdout], [], [], 20)
                self.assertTrue(ready, "Controlled writer did not reach the replacement boundary.")
                self.assertEqual(b"FILE_WRITTEN\n", process.stdout.readline())
                self.assertIsNone(process.poll())
                preview = self.command(root, "maintain-system-resume", "--operation-key", "hard-crash-apply")
                self.assertFalse(preview["application_performed"])
                self.assertEqual("running", preview["operation"]["state"])
                blocked = self.failed(root, "maintain-system-resume", "--operation-key", "hard-crash-apply", "--execute")
                self.assertEqual("application_in_progress", blocked["code"])
                timestamp = (root / "added.txt").stat().st_mtime_ns
                process.stdin.write(b"x")
                process.stdin.flush()
                self.assertEqual(77, process.wait(timeout=10))
                saved = self.command(root, "maintain-system", "--operation-key", "hard-crash-apply")
                self.assertEqual("running", saved["operation"]["state"])
                result = self.command(root, "maintain-system-resume", "--operation-key", "hard-crash-apply", "--execute")
                self.assertEqual("completed", result["operation"]["state"])
                self.assertEqual(timestamp, (root / "added.txt").stat().st_mtime_ns)
                self.assertEqual("after\n", (root / "value.txt").read_text())
                self.assertEqual("applied", self.state(root, change)["state"])
            finally:
                stop_process(process)
                process.stdin.close()
                process.stdout.close()
                process.stderr.close()

    def test_missing_agent_gate_review_prevents_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, candidate = self.fixture(directory)
            path = root / "review.json"
            review = json.loads(path.read_text())
            review["gate_reviews"].pop()
            path.write_text(json.dumps(review), encoding="utf-8")
            self.assertEqual("acceptance_review_missing", self.accept(root, change, failure=True)["code"])
            self.assertEqual("prepared", self.state(root, change)["state"])

    def test_preimage_conflicts_and_later_user_edits_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, candidate = self.fixture(directory)
            self.accept(root, change)
            (root / "value.txt").write_text("A user edit before application.\n", encoding="utf-8")
            self.assertEqual("application_target_conflict", self.apply(root, recovery, change, failure=True)["code"])
            (root / "value.txt").write_text("before\n", encoding="utf-8")
            self.apply(root, recovery, change)
            (root / "value.txt").write_text("A user edit after application.\n", encoding="utf-8")
            result = self.failed(root, "maintain-system-rollback", "--id", str(change["id"]), "--expected-revision", "5",
                                 "--operation-key", "conflicting-rollback", "--application-key", "apply-layout", "--execute")
            self.assertEqual("application_target_conflict", result["code"])
            self.assertEqual("A user edit after application.\n", (root / "value.txt").read_text())

    def test_new_run_cannot_reuse_preexisting_result_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, candidate = self.fixture(directory)
            result = self.failed(root, "maintain-system-check", "--id", str(change["id"]), "--expected-revision", "3",
                                 "--run-key", "new-run-with-stale-output", "--plan-file", str(root / "plan.json"), "--execute")
            self.assertEqual("check_output_exists", result["code"])

    def test_failed_monitor_retains_observed_exit_when_no_result_file_was_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, candidate = self.fixture(directory, monitor_fails=True)
            self.accept(root, change)
            self.apply(root, recovery, change)
            result = self.failed(root, "maintain-system-follow-up", "--id", str(change["id"]), "--expected-revision", "5",
                                 "--operation-key", "failed-monitor", "--status", "monitoring", "--note", "Controlled exit 7 without output.", "--execute")
            self.assertIn("operation", result)
            self.assertEqual("failed", result["operation"]["state"])
            self.assertEqual(7, result["operation"]["receipt"]["results"][0]["exit_code"])
            self.assertEqual("applied", self.state(root, change)["state"])

    def test_existing_executable_mode_bits_are_not_widened_by_content_application(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.baseline_modes = {"value.txt": 0o744}
            root, recovery, change, candidate = self.fixture(directory)
            self.accept(root, change)
            self.assertEqual(0o744, (root / "value.txt").stat().st_mode & 0o777)
            self.apply(root, recovery, change)
            self.assertEqual(0o744, (root / "value.txt").stat().st_mode & 0o777)

    def test_resolution_preview_abort_and_checked_invalidation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, recovery, change, candidate = self.fixture(directory)
            project = resolve_project(str(root), str(self.memory_home(root)))
            call = {"proposal_id": change["id"], "expected_revision": 3, "kind": "accept",
                    "acceptance_file": "acceptance.json", "review_file": "review.json"}
            reserve_operation(project, change, "queued-accept", "accept", {"call": call}, {"phase": "reserved"})
            preview = self.command(root, "maintain-system-resolve", "--operation-key", "queued-accept")
            self.assertEqual("running", preview["operation"]["state"])
            resolved = self.command(root, "maintain-system-resolve", "--operation-key", "queued-accept", "--execute")
            self.assertEqual("failed", resolved["operation"]["state"])
            self.assertEqual("aborted_without_success_claim", resolved["operation"]["receipt"]["outcome"])
            self.assertTrue(self.command(root, "maintain-system-resolve", "--operation-key", "queued-accept", "--execute")["reused"])
            self.assertEqual("prepared", self.state(root, change)["state"])
            self.accept(root, change)
            self.command(root, "maintain-system-follow-up", "--id", str(change["id"]), "--expected-revision", "4",
                         "--operation-key", "invalidate-checked", "--status", "needs_evidence", "--note", "Controlled invalidation.", "--execute")
            self.assertEqual("needs_evidence", self.state(root, change)["state"])
            # Controlled unknown-child metadata, not evidence of a live or terminated process.
            current = self.state(root, change)
            reserve_operation(project, current, "unknown-monitor", "monitoring",
                              {"call": {"expected_revision": current["state_revision"]}}, {"active_check_key": "unobserved-child"})
            refused = self.failed(root, "maintain-system-resolve", "--operation-key", "unknown-monitor", "--execute")
            self.assertEqual("execution_observation_required", refused["code"])
