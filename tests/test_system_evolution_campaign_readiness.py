# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""R4 preparation only: controlled input checks, no prospective real activity."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_campaign_input_contract import manifest
from tests.test_prospective_cohort_contract import protocol
from tests import test_system_evolution_candidates as candidate_fixtures
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.system_evolution_campaign_readiness import campaign_readiness


class SystemEvolutionCampaignReadinessTests(AgentMemoryTestBase):
    git = candidate_fixtures.SystemEvolutionCandidateTests.git

    def inputs(self, directory):
        root = Path(directory) / "project"
        root.mkdir()
        protocol_path, source_path = root / "protocol.json", root / "campaign.json"
        protocol_path.write_text(json.dumps(protocol("prospective_real_tasks")), encoding="utf-8")
        source_path.write_text(json.dumps(manifest(root, self.memory_home(root))), encoding="utf-8")
        return root, protocol_path, source_path

    def audit(self, root, *args):
        return json.loads(self.run_memory(root, "maintain-system-campaign-readiness", *args, "--json").stdout)

    def test_default_audit_reports_all_external_gaps_without_initialization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            result = self.audit(root)
            self.assertEqual("no_go", result["decision"])
            self.assertEqual(6, len(result["sections"]["external"]["missing_requirements"]))
            self.assertIn("unsupported_campaign_contract", result["blockers"])
            self.assertFalse(result["activity_started"])
            self.assertFalse(result["records_written"])
            self.assertFalse(self.memory_home(root).exists())
            self.assertEqual([], list(root.iterdir()))
            self.assertEqual(64, len(result["runtime_identity"]["code_digest"]))
            self.assertFalse(result["target_source"]["available"])

    def test_valid_legacy_declarations_are_not_authority_or_general_campaign_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            root, plan, source = self.inputs(directory)
            args = ("--protocol-file", str(plan), "--campaign-manifest", str(source))
            general = self.audit(root, *args)
            self.assertEqual("no_go", general["decision"])
            self.assertIn("unsupported_campaign_contract", general["blockers"])
            legacy = self.audit(root, *args, "--intent", "diagnosis_query")
            self.assertEqual("inputs_valid_only", legacy["decision"])
            self.assertFalse(legacy["execution_authorized"])
            self.assertFalse(legacy["evidence_verified"])
            self.assertFalse(legacy["sections"]["external"]["continuity_authenticated"])
            self.assertIsNone(legacy["sections"]["evidence"]["miss_rate"])
            rendered = json.dumps(legacy)
            for private in (str(root), "project-owner-secret", "queue-owner", "future issue queue"):
                self.assertNotIn(private, rendered)
            self.assertFalse(self.memory_home(root).exists())

    def test_calibration_unsupported_tasks_and_missing_fields_do_not_gain_real_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root, plan, source = self.inputs(directory)
            args = ("--protocol-file", str(plan), "--campaign-manifest", str(source), "--intent", "diagnosis_query")
            plan.write_text(json.dumps(protocol()), encoding="utf-8")
            self.assertIn("calibration_is_not_a_real_task_source", self.audit(root, *args)["blockers"])
            value = protocol("prospective_real_tasks")
            value["task_type"] = "workflow"
            plan.write_text(json.dumps(value), encoding="utf-8")
            self.assertIn("invalid_or_unsupported_protocol", self.audit(root, *args)["blockers"])
            plan.write_text(json.dumps(protocol("prospective_real_tasks")), encoding="utf-8")
            value = json.loads(source.read_text())
            del value["task_stream"]["continuity_owner_role"]
            source.write_text(json.dumps(value), encoding="utf-8")
            report = self.audit(root, *args)
            self.assertIn("future_task_stream", report["sections"]["external"]["missing_requirements"])
            self.assertEqual("no_go", report["decision"])
            self.assertFalse(self.memory_home(root).exists())

    def test_wrong_archive_and_invalid_bounded_json_are_reported_without_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root, plan, source = self.inputs(directory)
            value = json.loads(source.read_text())
            value["memory"]["task_start_memory_home"] = str(Path(directory) / "other")
            source.write_text(json.dumps(value), encoding="utf-8")
            result = self.audit(root, "--protocol-file", str(plan), "--campaign-manifest", str(source), "--intent", "diagnosis_query")
            self.assertIn("invalid_campaign_manifest_binding", result["blockers"])
            for bad in ('{"private":"SECRET_RAW","private":1}', '[' + ' ' * 32769 + ']', '{"private":"SECRET_RAW"', '[]'):
                source.write_text(bad, encoding="utf-8")
                result = self.audit(root, "--campaign-manifest", str(source))
                self.assertEqual("invalid", result["sections"]["campaign"]["manifest"]["status"])
                self.assertNotIn("SECRET_RAW", json.dumps(result))
            self.assertFalse(self.memory_home(root).exists())

    def test_rejected_cohort_creation_never_initializes_an_archive(self):
        cases = ("missing_manifest", "unsupported_task", "invalid_protocol", "invalid_manifest")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root, plan, source = self.inputs(directory)
                args = ["eval-cohort-create", "--protocol", str(plan)]
                if case == "unsupported_task":
                    value = protocol("prospective_real_tasks")
                    value["task_type"] = "workflow"
                    plan.write_text(json.dumps(value))
                elif case == "invalid_protocol":
                    plan.write_text("[]")
                elif case == "invalid_manifest":
                    source.write_text("{}")
                    args += ["--campaign-manifest", str(source)]
                with self.assertRaises(subprocess.CalledProcessError):
                    self.run_memory(root, *args, "--json")
                self.assertFalse(self.memory_home(root).exists(), case)

    def test_existing_archive_is_not_opened_or_changed_by_readiness_or_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root, plan, source = self.inputs(directory)
            self.run_memory(root, "init")
            self.run_memory(root, "update", "--type", "semantic", "--fact", "Synthetic R4 readiness query isolation.")
            before_query = json.loads(self.run_memory(root, "context", "--query", "R4 readiness query isolation", "--compact", "--json").stdout)
            db = self.project_memory_dir(root) / "memory.db"
            before = hashlib.sha256(db.read_bytes()).hexdigest()
            selected = resolve_project(str(root), str(self.memory_home(root)))
            with patch.object(sqlite3, "connect", side_effect=AssertionError("Readiness must not open SQLite")):
                result = campaign_readiness(selected, str(plan), str(source))
            self.assertFalse(result["sections"]["internal"]["archive_identity_checked"])
            with self.assertRaises(subprocess.CalledProcessError):
                self.run_memory(root, "eval-cohort-create", "--protocol", str(plan), "--json")
            self.assertEqual(before, hashlib.sha256(db.read_bytes()).hexdigest())
            after_query = json.loads(self.run_memory(root, "context", "--query", "R4 readiness query isolation", "--compact", "--json").stdout)
            self.assertEqual(before_query["query_handoff"], after_query["query_handoff"])

    def test_installed_readiness_uses_the_actual_runtime_code_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root, plan, source = self.inputs(directory)
            installer = Path(__file__).resolve().parents[1] / "install.py"
            subprocess.run([sys.executable, str(installer), "--project", str(root), "--memory-home", str(self.memory_home(root))],
                           check=True, capture_output=True)
            source_result = self.audit(root)
            command = [sys.executable, str(root / "tools/agent_memory.py"), "maintain-system-campaign-readiness",
                       "--project", str(root), "--memory-home", str(self.memory_home(root)), "--json"]
            installed = json.loads(subprocess.run(command, text=True, check=True, capture_output=True).stdout)
            self.assertEqual(source_result["runtime_identity"]["code_digest"], installed["runtime_identity"]["code_digest"])
            self.assertEqual(source_result["runtime_identity"]["file_count"], installed["runtime_identity"]["file_count"])
            self.assertFalse(installed["records_written"])

    def test_target_git_observation_distinguishes_revision_and_dirty_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            self.git(root, "init", "--quiet")
            (root / "tracked.txt").write_text("Controlled baseline\n")
            self.git(root, "add", "tracked.txt")
            self.git(root, "commit", "--quiet", "-m", "Controlled readiness baseline")
            clean = self.audit(root)
            self.assertTrue(clean["target_source"]["available"])
            self.assertFalse(clean["target_source"]["dirty"])
            (root / "tracked.txt").write_text("Controlled later edit\n")
            dirty = self.audit(root)
            self.assertTrue(dirty["target_source"]["dirty"])
            self.assertNotEqual(clean["target_source"]["status_digest"], dirty["target_source"]["status_digest"])
            self.assertEqual(clean["target_source"]["revision"], dirty["target_source"]["revision"])
            self.assertEqual(clean["runtime_identity"]["code_digest"], dirty["runtime_identity"]["code_digest"])
