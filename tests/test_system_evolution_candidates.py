# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Synthetic candidate/subject regressions; not product or real-task evidence."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_system_evolution import synthetic_report
from tests.test_system_evolution_triggers import synthetic_trigger
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.system_evolution_candidates import (
    candidate_request, prepare_candidate, prepared_candidate_context,
)


SCRIPT = (
    "from pathlib import Path\n"
    "assert Path('value.txt').read_text() == 'after\\n'\n"
    "assert Path('added.txt').read_text() == 'new\\n'\n"
    "assert not Path('delete.txt').exists()\n"
    "Path('executed-in.txt').write_text(str(Path.cwd()))\n"
)


class SystemEvolutionCandidateTests(AgentMemoryTestBase):
    def git(self, root: Path, *args: str) -> bytes:
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        return subprocess.run(["git", "-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid",
                               "-c", f"core.hooksPath={os.devnull}", "-C", str(root), *args],
                              env=env, check=True, capture_output=True).stdout

    def command(self, root: Path, *args: str) -> dict:
        return json.loads(self.run_memory(root, *args, "--json").stdout)

    def failed(self, root: Path, *args: str) -> dict:
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            self.run_memory(root, *args, "--json")
        self.assertEqual(1, caught.exception.returncode)
        return json.loads(caught.exception.stdout)

    def fixture(self, directory: str, *, trigger: dict | None = None, check_script: str = SCRIPT,
                baseline_files: dict[str, str] | None = None, candidate_files: dict[str, str] | None = None,
                baseline_modes: dict[str, int] | None = None) -> tuple[Path, Path, dict]:
        root = Path(directory) / "project"
        root.mkdir()
        home = Path(directory) / "candidates"
        home.mkdir()
        templates = Path(directory) / "empty-template"
        templates.mkdir()
        self.git(root, "init", "--quiet", f"--template={templates}")
        (root / ".gitignore").write_text("candidate.patch\nplan.json\nexecuted-in.txt\n__pycache__/\n", encoding="utf-8")
        (root / "value.txt").write_text("before\n", encoding="utf-8")
        (root / "delete.txt").write_text("remove\n", encoding="utf-8")
        (root / "check.py").write_text(check_script, encoding="utf-8")
        for name, contents in (baseline_files or {}).items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
        for name, mode in (baseline_modes or {}).items():
            os.chmod(root / name, mode)
        self.git(root, "add", ".")
        self.git(root, "commit", "--quiet", "-m", "Synthetic controlled base")
        base = self.git(root, "rev-parse", "HEAD").decode().strip()
        (root / "value.txt").write_text("after\n", encoding="utf-8")
        (root / "added.txt").write_text("new\n", encoding="utf-8")
        (root / "delete.txt").unlink()
        for name, contents in (candidate_files or {}).items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
        self.git(root, "add", "--all")
        patch = self.git(root, "diff", "--cached", "--binary")
        self.git(root, "read-tree", "HEAD")
        (root / "value.txt").write_text("before\n", encoding="utf-8")
        (root / "delete.txt").write_text("remove\n", encoding="utf-8")
        (root / "added.txt").unlink()
        for name in candidate_files or {}:
            if name in (baseline_files or {}):
                (root / name).write_text(baseline_files[name], encoding="utf-8")
            else:
                (root / name).unlink()
        (root / "candidate.patch").write_bytes(patch)
        self.run_memory(root, "init")
        report = synthetic_report()
        report["change_proposals"][0]["acceptance_criteria"] = ["Observe the controlled candidate after-file layout."]
        review_key = "synthetic-review"
        if trigger is not None:
            decision = self.command(root, "reflect-system-trigger", "--payload", json.dumps(trigger), "--claim")
            self.assertTrue(decision["claim_created"])
            self.assertFalse(decision["model_invoked"])
            report.update(decision["report_binding"])
            review_key = decision["review_key"]
        saved = self.command(root, "reflect-system", "--review-key", review_key, "--payload", json.dumps(report))
        prepared = self.command(root, "maintain-system-status", "--id", str(saved["proposal_id"]), "--expected-revision", "1",
                                "--status", "prepared", "--note", "Synthetic patch preparation.", "--development-root", str(root),
                                "--base-version", base, "--artifact-file", "candidate.patch")
        return root, home, prepared["change"]

    def candidate(self, root: Path, home: Path, change: dict, *, execute: bool = False,
                  key: str = "synthetic-candidate", failure: bool = False) -> dict:
        args = ["maintain-system-candidate", "--id", str(change["id"]), "--expected-revision", str(change["state_revision"]),
                "--candidate-key", key, "--patch-file", "candidate.patch", "--candidate-home", str(home)]
        if execute:
            args.append("--execute")
        return (self.failed if failure else self.command)(root, *args)

    def plan(self, root: Path, change: dict, candidate: dict) -> dict:
        target = Path(candidate["receipt"]["binding"]["root"])
        return {
            "schema_version": "system-change-check-plan/v2", "proposal_id": change["id"],
            "prepared_state_revision": change["state_revision"], "artifact_digest": change["artifact_digest"],
            "candidate_key": candidate["candidate_key"], "candidate_digest": candidate["receipt"]["candidate_digest"],
            "source_files": [{"path": "check.py", "digest": hashlib.sha256((target / "check.py").read_bytes()).hexdigest()}],
            "checks": [{"key": "synthetic-subject-check", "argv": [sys.executable, "check.py"],
                        "assertion_indices": [0], "timeout_seconds": 5}],
        }

    def run_plan(self, root: Path, plan: dict, failure: bool = False) -> dict:
        path = root / "plan.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        return (self.failed if failure else self.command)(root, "maintain-system-check", "--id", str(plan["proposal_id"]),
                   "--expected-revision", str(plan["prepared_state_revision"]), "--run-key", "synthetic-run",
                   "--plan-file", str(path), "--execute")

    def tables(self, root: Path) -> set[str]:
        with closing(sqlite3.connect(self.project_memory_dir(root) / "memory.db")) as conn:
            return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def test_preview_does_not_clone_or_initialize_candidate_storage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, home, change = self.fixture(directory)
            before = self.tables(root)
            result = self.candidate(root, home, change)
            self.assertEqual("system-change-candidate-preview/v1", result["schema_version"])
            self.assertFalse(result["candidate_prepared"])
            self.assertEqual(before, self.tables(root))
            self.assertEqual([], list(home.iterdir()))
            self.assertEqual("before\n", (root / "value.txt").read_text())

    def test_candidate_changes_only_the_owned_copy_and_reuses_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, home, change = self.fixture(directory)
            original_index = self.git(root, "diff", "--cached", "--binary")
            result = self.candidate(root, home, change, execute=True)
            candidate = result["candidate"]
            self.assertEqual("ready", candidate["state"])
            target = Path(candidate["receipt"]["binding"]["root"])
            self.assertEqual("after\n", (target / "value.txt").read_text())
            self.assertEqual("new\n", (target / "added.txt").read_text())
            self.assertFalse((target / "delete.txt").exists())
            self.assertEqual("before\n", (root / "value.txt").read_text())
            self.assertTrue((root / "delete.txt").exists())
            self.assertFalse((root / "added.txt").exists())
            self.assertEqual(original_index, self.git(root, "diff", "--cached", "--binary"))
            repeated = self.candidate(root, home, change, execute=True)
            self.assertTrue(repeated["reused"])
            self.assertEqual(candidate["operation_root"], repeated["candidate"]["operation_root"])
            self.assertEqual(1, len(list(home.iterdir())))
            detail = self.command(root, "maintain-system", "--candidate-key", "synthetic-candidate")
            self.assertEqual(candidate["receipt"], detail["candidate"]["receipt"])
            self.assertFalse(result["promotion_eligible"])
            self.assertFalse(result["application_performed"])

    def test_delayed_reservation_reuses_completed_history_after_parent_advances(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, home, change = self.fixture(directory)
            project = resolve_project(str(root), str(self.memory_home(root)))
            request = candidate_request(change["id"], change["state_revision"], "candidate.patch", str(home))
            # Capture a second caller's context before the first caller completes.
            stale_context = prepared_candidate_context(project, change["id"], change["state_revision"],
                                                       "synthetic-candidate", request)
            candidate = self.candidate(root, home, change, execute=True)["candidate"]
            self.command(root, "maintain-system-status", "--id", str(change["id"]), "--expected-revision", "2",
                         "--status", "needs_evidence", "--note", "Synthetic parent advancement after preparation.")
            module = "tools.agent_memory_runtime.system_evolution_candidates"
            with patch(f"{module}.prepared_candidate_context", return_value=stale_context), patch(
                    f"{module}.tempfile.mkdtemp", side_effect=AssertionError("Historical retries must not create a directory.")):
                repeated = prepare_candidate(project, change["id"], change["state_revision"],
                                             "synthetic-candidate", "candidate.patch", str(home), execute=True)
            self.assertTrue(repeated["reused"])
            self.assertEqual(candidate, repeated["candidate"])
            self.assertEqual(1, len(list(home.iterdir())))
            detail = self.command(root, "maintain-system", "--change-id", str(change["id"]))
            self.assertEqual("needs_evidence", detail["change"]["state"])
            self.assertEqual(3, detail["change"]["state_revision"])
            self.assertEqual(1, len(detail["candidates"]))

    def test_v2_check_runs_in_the_actual_candidate_and_does_not_promote(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, home, change = self.fixture(directory)
            candidate = self.candidate(root, home, change, execute=True)["candidate"]
            result = self.run_plan(root, self.plan(root, change, candidate))
            receipt = result["run"]["receipt"]
            target = Path(candidate["receipt"]["binding"]["root"])
            self.assertEqual("all_exit_zero", receipt["outcome"])
            self.assertEqual(str(target), receipt["execution_root"])
            self.assertEqual(str(target), (target / "executed-in.txt").read_text())
            self.assertFalse((root / "executed-in.txt").exists())
            self.assertTrue(receipt["binding_before"]["candidate"]["matches"])
            self.assertFalse(result["evidence_verified"])
            detail = self.command(root, "maintain-system", "--change-id", str(change["id"]))
            self.assertEqual("prepared", detail["change"]["state"])
            self.assertEqual(1, len(detail["candidates"]))

    def test_claim_to_candidate_check_keeps_one_history_and_advisory_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            trigger = synthetic_trigger()
            root, home, change = self.fixture(directory, trigger=trigger)
            summary = self.command(root, "maintain-system")
            self.assertEqual(1, len(summary["trigger_claims"]))
            claim = summary["trigger_claims"][0]
            self.assertEqual("recorded", claim["state"])
            self.assertEqual(change["review_id"], claim["review_id"])
            self.assertFalse(claim["model_execution_observed"])
            report = self.command(root, "maintain-system", "--review-key", claim["review_key"])["report"]
            self.assertEqual(trigger["task_ref"], report["task_ref"])
            self.assertEqual("memory_error", report["trigger"])

            candidate = self.candidate(root, home, change, execute=True)["candidate"]
            self.assertEqual("ready", candidate["state"])
            plan = self.plan(root, change, candidate)
            checked = self.run_plan(root, plan)
            self.assertEqual("all_exit_zero", checked["run"]["receipt"]["outcome"])
            self.assertEqual(candidate["candidate_key"], checked["run"]["receipt"]["candidate_key"])
            self.assertEqual(candidate["receipt"]["candidate_digest"],
                             checked["run"]["plan_summary"]["candidate"]["candidate_digest"])
            marker = Path(candidate["receipt"]["binding"]["root"]) / "executed-in.txt"
            marker.write_text("Synthetic sentinel: a retry must not rerun the check.\n", encoding="utf-8")
            repeated_run = self.run_plan(root, plan)
            self.assertTrue(repeated_run["reused"])
            self.assertEqual(checked["run"], repeated_run["run"])
            self.assertTrue(marker.read_text().startswith("Synthetic sentinel:"))
            self.assertTrue(self.candidate(root, home, change, execute=True)["reused"])
            repeated_report = self.command(root, "reflect-system", "--review-key", claim["review_key"],
                                           "--payload", json.dumps(report))
            self.assertFalse(repeated_report["inserted"])
            repeated_trigger = self.command(root, "reflect-system-trigger", "--payload", json.dumps(trigger), "--claim")
            self.assertFalse(repeated_trigger["should_review"])
            self.assertEqual("already_reviewed", repeated_trigger["reason"])

            refused = self.failed(root, "maintain-system-status", "--id", str(change["id"]), "--expected-revision", "2",
                                  "--status", "checked", "--note", "A zero exit alone is insufficient for promotion.")
            self.assertEqual("verification_gate_unavailable", refused["code"])
            detail = self.command(root, "maintain-system", "--change-id", str(change["id"]))
            self.assertEqual("prepared", detail["change"]["state"])
            self.assertEqual(2, detail["change"]["state_revision"])
            self.assertEqual(1, len(detail["check_runs"]))
            self.assertEqual(1, len(detail["candidates"]))
            self.assertEqual(2, len(detail["events"]))
            self.assertEqual(1, len(list(home.iterdir())))
            self.assertFalse(checked["evidence_verified"])
            self.assertFalse(checked["promotion_eligible"])
            self.assertFalse(checked["application_performed"])
            for kind in ("semantic", "episode", "reflection"):
                self.assertEqual([], self.list_records(root, kind))
            handoff = self.command(root, "context", "--query", "SYNTHETIC_META_ONLY", "--compact")["query_handoff"]
            for field in ("experience_refs", "code_anchors", "log_anchors"):
                self.assertEqual([], handoff[field])
            self.assertEqual("before\n", (root / "value.txt").read_text())
            self.assertFalse((root / "executed-in.txt").exists())

    def test_omitted_changed_file_and_git_config_drift_prevent_check_execution(self) -> None:
        for changed in ("value.txt", ".git/config"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as directory:
                root, home, change = self.fixture(directory)
                candidate = self.candidate(root, home, change, execute=True)["candidate"]
                plan = self.plan(root, change, candidate)
                target = Path(candidate["receipt"]["binding"]["root"])
                with (target / changed).open("a", encoding="utf-8") as handle:
                    handle.write("\n# controlled drift\n")
                result = self.run_plan(root, plan, failure=True)
                self.assertEqual("check_binding_mismatch", result["code"])
                self.assertFalse((target / "executed-in.txt").exists())
                self.assertNotIn("system_change_check_runs", self.tables(root))

    def test_wrong_candidate_digest_is_rejected_before_running(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, home, change = self.fixture(directory)
            candidate = self.candidate(root, home, change, execute=True)["candidate"]
            plan = self.plan(root, change, candidate)
            plan["candidate_digest"] = "0" * 64
            result = self.run_plan(root, plan, failure=True)
            self.assertEqual("candidate_binding_changed", result["code"])

    def test_failed_patch_is_retained_and_not_automatically_retried(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, home, change = self.fixture(directory)
            (root / "candidate.patch").write_text("Not a valid patch; controlled failure.\n", encoding="utf-8")
            changed = self.command(root, "maintain-system-status", "--id", str(change["id"]), "--expected-revision", "2",
                                   "--status", "prepared", "--note", "Synthetic invalid patch.", "--development-root", str(root),
                                   "--base-version", change["artifact_manifest"]["base_version"], "--artifact-file", "candidate.patch")["change"]
            result = self.candidate(root, home, changed, execute=True, failure=True)
            self.assertEqual("failed", result["candidate"]["state"])
            self.assertTrue(Path(result["candidate"]["operation_root"]).exists())
            self.assertTrue(self.candidate(root, home, changed, execute=True, failure=True)["reused"])
            self.assertEqual(1, len(list(home.iterdir())))
            self.assertEqual("before\n", (root / "value.txt").read_text())

    def test_unresolved_preparation_blocks_state_updates_and_new_checks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, home, change = self.fixture(directory)
            candidate = self.candidate(root, home, change, execute=True)["candidate"]
            with closing(sqlite3.connect(self.project_memory_dir(root) / "memory.db")) as conn, conn:
                # Controlled unresolved-record fixture, not a statement about a live process.
                conn.execute("UPDATE system_change_candidates SET state='preparing', completed_at=NULL")
            repeated = self.candidate(root, home, change, execute=True, failure=True)
            self.assertEqual("candidate_in_progress", repeated["code"])
            blocked = self.failed(root, "maintain-system-status", "--id", str(change["id"]), "--expected-revision", "2",
                                  "--status", "rejected", "--note", "Controlled blocked update.")
            self.assertEqual("candidate_in_progress", blocked["code"])
            plan = self.plan(root, change, candidate)
            plan["schema_version"] = "system-change-check-plan/v1"
            plan.pop("candidate_key")
            plan.pop("candidate_digest")
            blocked = self.run_plan(root, plan, failure=True)
            self.assertEqual("candidate_in_progress", blocked["code"])

    def test_candidate_home_cannot_be_the_source_or_memory_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, _, change = self.fixture(directory)
            for home in (root, self.memory_home(root)):
                with self.subTest(home=home):
                    result = self.candidate(root, home, change, execute=True, failure=True)
                    self.assertEqual("invalid_candidate", result["code"])
            self.assertNotIn("system_change_candidates", self.tables(root))
