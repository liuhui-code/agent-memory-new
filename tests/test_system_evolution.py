# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Controlled synthetic governance fixtures, not real tasks or approval evidence.

Execution results and scope are recorded separately in the system meta-reflection design.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


def synthetic_report(revision: int = 1) -> dict:
    return {
        "report_format": "system-meta-review/v1",
        "task_ref": {"key": "synthetic-task", "origin": "client_local"},
        "review_revision": revision, "trigger": "manual", "task_state": "completed",
        "task_outcome": "unknown", "memory_use": "unknown", "version_refs": {},
        "query_refs": [], "observations": [], "checks": [], "model_opinions": [],
        "target_components": ["rules"],
        "change_proposals": [{
            "target_component": "rules", "change_kind": "requirement",
            "problem": "SYNTHETIC_META_ONLY: controlled storage requirement, not an observed defect.",
            "proposed_change": "Prepare a synthetic artifact for a controlled governance test.",
            "evidence_refs": [], "acceptance_criteria": ["Keep synthetic governance outside project retrieval."],
            "compatibility": "Keep the existing query contract.", "rollback": "No product mutation in this fixture.",
            "proposal_state": "needs_evidence",
        }],
        "missing_evidence": ["Synthetic fixture has no real task or validation evidence."],
        "omitted_counts": {}, "additional_cost": {"tokens": None, "elapsed_ms": None},
        "review_status": "partial", "advisory_only": True,
    }


class SystemEvolutionTests(AgentMemoryTestBase):
    def command(self, root: Path, *args: str) -> dict:
        return json.loads(self.run_memory(root, *args, "--json").stdout)

    def save(self, root: Path, report: dict | None = None, key: str = "synthetic-review") -> dict:
        return self.command(root, "reflect-system", "--review-key", key,
                            "--payload", json.dumps(report if report is not None else synthetic_report()))

    def error(self, root: Path, *args: str) -> dict:
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            self.run_memory(root, *args, "--json")
        result = json.loads(caught.exception.stdout)
        self.assertEqual("system-evolution-error/v1", result["schema_version"])
        return result

    def table_names(self, root: Path) -> set[str]:
        with sqlite3.connect(self.project_memory_dir(root) / "memory.db") as conn:
            return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def test_read_does_not_create_archive_or_lazy_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            result = self.command(root, "maintain-system")
            self.assertFalse(result["available"])
            self.assertFalse(self.memory_home(root).exists())
            self.run_memory(root, "init")
            before = self.table_names(root)
            self.assertFalse(self.command(root, "maintain-system")["available"])
            self.assertEqual(before, self.table_names(root))
            self.assertNotIn("system_meta_reviews", before)

    def test_save_is_idempotent_and_separate_from_project_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_memory(root, "init")
            self.run_memory(root, "update", "--type", "semantic", "--fact", "Controlled baseline fact.")
            first = self.save(root)
            second = self.save(root)
            self.assertTrue(first["inserted"])
            self.assertFalse(second["inserted"])
            self.assertEqual(first["review"], second["review"])
            self.assertFalse(first["evidence_verified"])
            self.assertFalse(first["ranking_updated"])
            summary = self.command(root, "maintain-system")
            self.assertEqual({"review_revisions": 1, "review_threads": 1, "changes": 1}, summary["counts"])
            self.assertEqual(1, len(self.list_records(root, "semantic")))
            self.assertEqual([], self.list_records(root, "reflection"))
            self.assertEqual([], self.list_records(root, "episode"))
            searched = self.command(root, "search", "--query", "SYNTHETIC_META_ONLY")
            for kind in ("semantic_facts", "reflections", "episodes", "wiki_matches", "code_log_matches"):
                self.assertNotIn("SYNTHETIC_META_ONLY", json.dumps(searched.get(kind, [])))

    def test_governance_writes_preserve_a_nonempty_public_query_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            self.run_memory(root, "init")
            query = "synthetic baseline compatibility"
            self.run_memory(root, "update", "--type", "semantic",
                            "--fact", "Synthetic baseline compatibility is a controlled semantic fact.")
            before = self.command(root, "context", "--query", query, "--compact")
            self.assertTrue(before["query_handoff"]["semantic_refs"])
            full_before = self.command(root, "context", "--query", query)
            self.assertTrue(full_before["query_handoff"]["semantic_refs"])
            report = synthetic_report()
            report["change_proposals"][0]["problem"] = (
                f"SYNTHETIC_META_ONLY: {query}; deliberately overlapping governance text, not a real defect."
            )
            saved = self.save(root, report)
            (root / "candidate.patch").write_text("Synthetic artifact for isolation checking only.\n", encoding="utf-8")
            self.command(root, "maintain-system-status", "--id", str(saved["proposal_id"]), "--expected-revision", "1",
                         "--status", "prepared", "--note", "Controlled governance-only update.", "--development-root", str(root),
                         "--base-version", "synthetic-base", "--artifact-file", "candidate.patch")
            self.command(root, "maintain-system", "--change-id", str(saved["proposal_id"]))
            after = self.command(root, "context", "--query", query, "--compact")
            self.assertEqual(set(before), set(after))
            self.assertEqual(before["query_handoff"], after["query_handoff"])
            full_after = self.command(root, "context", "--query", query)
            self.assertEqual(set(full_before), set(full_after))
            self.assertEqual(full_before["query_handoff"], full_after["query_handoff"])
            self.assertEqual(1, len(self.list_records(root, "semantic")))
            self.assertEqual([], self.list_records(root, "reflection"))
            self.assertEqual([], self.list_records(root, "episode"))

    def test_revisions_are_immutable_consecutive_and_one_thread_per_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_memory(root, "init")
            self.save(root)
            changed = synthetic_report()
            changed["missing_evidence"].append("A different synthetic revision body.")
            self.assertEqual("revision_conflict", self.error(root, "reflect-system", "--review-key", "synthetic-review",
                             "--payload", json.dumps(changed))["code"])
            self.assertEqual("task_identity_conflict", self.error(root, "reflect-system", "--review-key", "other-thread",
                             "--payload", json.dumps(synthetic_report()))["code"])
            self.assertEqual("revision_conflict", self.error(root, "reflect-system", "--review-key", "synthetic-review",
                             "--payload", json.dumps(synthetic_report(3)))["code"])
            self.save(root, synthetic_report(2))
            summary = self.command(root, "maintain-system")
            self.assertEqual(2, summary["counts"]["review_revisions"])
            self.assertEqual(1, summary["counts"]["review_threads"])
            self.assertEqual(2, summary["counts"]["changes"])
            shown = self.command(root, "maintain-system", "--review-key", "synthetic-review", "--limit", "1")
            self.assertEqual(2, shown["report"]["review_revision"])
            self.assertTrue(shown["revisions_truncated"])

    def test_invalid_reports_do_not_initialize_governance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_memory(root, "init")
            before = self.table_names(root)
            for field, value in (("advisory_only", False), ("trigger", []), ("review_revision", True),
                                 ("review_status", "not_run"), ("raw_logs", "SYNTHETIC_PRIVATE_MARKER")):
                report = synthetic_report()
                report[field] = value
                result = self.error(root, "reflect-system", "--review-key", "synthetic-review", "--payload", json.dumps(report))
                self.assertEqual("invalid_report", result["code"])
                self.assertNotIn("SYNTHETIC_PRIVATE_MARKER", json.dumps(result))
            self.assertEqual(before, self.table_names(root))

    def test_check_verdict_needs_references_but_is_still_advisory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_memory(root, "init")
            report = synthetic_report()
            report["checks"] = [{"assertion": "Controlled fixture assertion, not an executed check.",
                                  "expected_ref": None, "observed_refs": [], "result": "pass", "scope": "synthetic"}]
            self.assertEqual("invalid_report", self.error(root, "reflect-system", "--review-key", "synthetic-review",
                             "--payload", json.dumps(report))["code"])
            report["checks"][0]["result"] = "not_run"
            saved = self.save(root, report)
            self.assertFalse(saved["evidence_verified"])

    def test_bounds_duplicate_json_keys_and_archive_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_memory(root, "init")
            report = synthetic_report()
            report["version_refs"] = {"archive_project_id": "different-synthetic-archive"}
            self.assertEqual("archive_identity_mismatch", self.error(root, "reflect-system", "--review-key", "synthetic-review",
                             "--payload", json.dumps(report))["code"])
            report = synthetic_report()
            report["query_refs"] = [f"query:synthetic-{index}" for index in range(9)]
            self.assertEqual("invalid_report", self.error(root, "reflect-system", "--review-key", "synthetic-review",
                             "--payload", json.dumps(report))["code"])
            self.assertEqual("invalid_report", self.error(root, "reflect-system", "--review-key", "synthetic-review",
                             "--payload", '{"report_format":"first","report_format":"second"}')["code"])
            self.assertEqual("invalid_report", self.error(root, "reflect-system", "--review-key", "synthetic-review",
                             "--payload", "x" * 4001)["code"])
            self.assertEqual("invalid_report", self.error(root, "maintain-system", "--review-key", "")["code"])
            self.assertEqual("invalid_request", self.error(root, "maintain-system", "--review-key", "synthetic-review",
                             "--status", "proposed")["code"])

    def test_prepared_observes_artifacts_without_verifying_or_applying(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_memory(root, "init")
            change_id = self.save(root)["proposal_id"]
            artifact = root / "candidate.patch"
            artifact.write_bytes(b"Controlled synthetic artifact; not a real product patch.\n")
            result = self.command(root, "maintain-system-status", "--id", str(change_id), "--expected-revision", "1",
                                  "--status", "prepared", "--note", "Synthetic artifact observation.",
                                  "--development-root", str(root), "--artifact-file", "candidate.patch", "--base-version", "synthetic-base")
            change = result["change"]
            self.assertEqual("prepared", change["state"])
            self.assertEqual(2, change["state_revision"])
            manifest = change["artifact_manifest"]
            self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), manifest["artifacts"][0]["digest"])
            self.assertFalse(manifest["checks_executed"])
            self.assertFalse(result["application_performed"])
            for target in ("checked", "applied"):
                rejected = self.error(root, "maintain-system-status", "--id", str(change_id), "--expected-revision", "2",
                                      "--status", target, "--note", "Synthetic unsupported promotion.")
                self.assertEqual("verification_gate_unavailable", rejected["code"])
            stale = self.error(root, "maintain-system-status", "--id", str(change_id), "--expected-revision", "1",
                               "--status", "rejected", "--note", "Synthetic stale writer.")
            self.assertEqual("state_conflict", stale["code"])
            shown = self.command(root, "maintain-system", "--change-id", str(change_id))
            self.assertEqual(2, shown["change"]["state_revision"])
            self.assertEqual(2, len(shown["events"]))

    def test_artifact_escape_rolls_back_state_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            outside = Path(directory) / "outside.patch"
            outside.write_text("Controlled external fixture.", encoding="utf-8")
            self.run_memory(root, "init")
            change_id = self.save(root)["proposal_id"]
            result = self.error(root, "maintain-system-status", "--id", str(change_id), "--expected-revision", "1",
                                "--status", "prepared", "--note", "Synthetic invalid artifact.",
                                "--development-root", str(root), "--artifact-file", "../outside.patch", "--base-version", "synthetic-base")
            self.assertEqual("invalid_artifact", result["code"])
            shown = self.command(root, "maintain-system", "--change-id", str(change_id))
            self.assertEqual(1, shown["change"]["state_revision"])
            self.assertEqual(1, len(shown["events"]))
