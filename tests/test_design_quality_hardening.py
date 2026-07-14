# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.design_change_plan import build_change_plan
from tools.agent_memory_runtime.design_calibration import calibration_profile
from tools.agent_memory_runtime.design_eval import evaluate_case_pack
from tools.agent_memory_runtime.design_outcome import record_design_outcome
from tools.agent_memory_runtime.design_verification_evidence import load_test_report
from tools.agent_memory_runtime.storage import ensure_initialized, resolve_project


def proposal(candidate_id: str = "candidate") -> dict:
    return {
        "schema_version": "design-delta/v2",
        "id": candidate_id,
        "contract_id": "quality-contract",
        "goal": "Add independent profile cache and audit services",
        "anchors": [],
        "add_nodes": [
            {"id": "new:ProfileCache", "kind": "service", "file_path": "service/ProfileCache.ets"},
            {"id": "new:AuditService", "kind": "service", "file_path": "service/AuditService.ets"},
        ],
        "modify_nodes": [],
        "add_edges": [],
        "remove_edges": [],
        "assumptions": [],
        "invariants": ["Existing profile behavior remains unchanged"],
        "constraint_coverage": [],
        "quality_coverage": [],
        "coverage_evidence": [],
        "verification": {"tests": [], "observability": []},
    }


def architecture() -> dict:
    return {
        "nodes": [],
        "edges": [],
        "entry_points": [],
        "evidence_gaps": [],
        "audit": {"node_count": 0, "edge_count": 0},
    }


class DesignQualityHardeningTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "quality-hardening"
        self.root.mkdir()
        self.project = resolve_project(str(self.root), str(self.root / ".memory"))
        ensure_initialized(self.project)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_eval_marks_missing_metric_samples_not_evaluated(self) -> None:
        pack = {
            "schema_version": "design-eval-cases/v1",
            "cases": [{
                "id": "findings-only",
                "contract": {"id": "quality-contract", "goal": proposal()["goal"]},
                "proposals": [proposal()],
                "expected_findings": {},
            }],
        }

        result = evaluate_case_pack(self.project, pack)

        self.assertIsNone(result["metrics"]["candidate_preference_accuracy"])
        self.assertIsNone(result["metrics"]["planned_file_recall"])
        self.assertIsNone(result["metrics"]["finding_recall"])
        self.assertIsNone(result["metrics"]["supported_coverage_rate"])
        self.assertEqual(
            {"sample_count": 0, "status": "not_evaluated"},
            result["metric_coverage"]["candidate_preference_accuracy"],
        )
        self.assertEqual(
            {"sample_count": 0, "status": "not_evaluated"},
            result["metric_coverage"]["planned_file_recall"],
        )
        self.assertEqual("insufficient", result["quality_gate"]["status"])

    def test_contract_validity_is_calculated_from_candidate_findings(self) -> None:
        invalid = proposal("invalid")
        invalid["contract_id"] = "different-contract"
        pack = {
            "schema_version": "design-eval-cases/v1",
            "cases": [{
                "id": "contract-validity",
                "contract": {"id": "quality-contract", "goal": invalid["goal"]},
                "proposals": [invalid],
                "expected_findings": {"invalid": ["contract_id_mismatch"]},
            }],
        }

        result = evaluate_case_pack(self.project, pack)

        self.assertEqual(0.0, result["metrics"]["contract_validity_rate"])
        self.assertEqual(1, result["metric_coverage"]["contract_validity_rate"]["sample_count"])

    def test_unrelated_implementation_steps_are_parallel(self) -> None:
        plan = build_change_plan(proposal(), architecture(), revision=1)
        implementation = [step for step in plan["steps"] if step["operation"] == "add"]

        self.assertEqual(2, len(implementation))
        self.assertTrue(all(step["depends_on"] == [] for step in implementation))

    def test_verification_depends_only_on_covered_delta(self) -> None:
        value = proposal()
        value["verification"] = {"tests": ["profile cache test"], "observability": []}
        value["coverage_evidence"] = [{
            "target_type": "scenario",
            "target_id": "cache-quality",
            "delta_refs": ["new:ProfileCache"],
            "verification_refs": ["profile cache test"],
            "repository_refs": [],
        }]

        plan = build_change_plan(value, architecture(), revision=1)
        by_target = {step["target"]: step for step in plan["steps"]}

        self.assertEqual(
            [by_target["new:ProfileCache"]["id"]],
            by_target["test:profile cache test"]["depends_on"],
        )

    def test_compiler_report_maps_diagnostics_to_test_evidence(self) -> None:
        report = self.root / "compiler-report.json"
        report.write_text(
            '{"schema_version":"compiler-report/v1","command":"hvigor assembleHap",'
            '"verifies":["ArkTS compiles"],"diagnostics":[{'
            '"severity":"error","file":"service/ProfileCache.ets","line":4,'
            '"message":"unknown type"}]}',
            encoding="utf-8",
        )

        tests = load_test_report(str(report))

        self.assertEqual("failed", tests[0]["status"])
        self.assertIn("arkts compiles", tests[0]["verifies"])

    def test_historical_risk_requires_five_matching_reviewed_outcomes(self) -> None:
        verification = {
            "schema_version": "design-verification/v2",
            "candidate_id": "cache",
            "contract_id": "quality-contract",
            "status": "replan",
            "baseline_revision": 1,
            "current_revision": 1,
            "metrics": {},
            "verification": {"replan_triggers": ["planned_changes_missing"]},
            "calibration_features": {
                "archetype": "service", "change_size_bucket": "small",
                "risk_count": 1, "api_change_count": 0, "graph_delta_count": 0,
            },
        }
        for _ in range(4):
            record_design_outcome(self.project, verification, "failure")
        self.assertEqual(
            "insufficient_samples",
            calibration_profile(self.project, "service", "small")["status"],
        )

        record_design_outcome(self.project, verification, "success")
        profile = calibration_profile(self.project, "service", "small")

        self.assertEqual("advisory", profile["status"])
        self.assertEqual(0.8, profile["historical_risk_rate"])
        self.assertEqual("advisory_tie_break_only", profile["authority"])


if __name__ == "__main__":
    unittest.main()
