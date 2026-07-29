# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.agent_benchmark_cases import public_case, validate_case_pack
from tools.agent_memory_runtime.context_calibration import (
    assess_calibration,
    normalize_evaluation_profile,
    validate_calibrated_holdout,
)


def profile(role: str, level: str, mechanism: str) -> dict[str, object]:
    return {
        "target_domain": "native_arkts",
        "artifact_roles": [role],
        "target_levels": [level],
        "mechanism_kinds": [mechanism],
    }


def scored(case_id: str, status: str = "pass") -> dict[str, object]:
    return {
        "case_id": case_id,
        "status": status,
        "anchor_recall": 1.0 if status == "pass" else 0.0,
        "oracle_anchor_precision": 1.0 if status == "pass" else 0.0,
        "source_span_recall": 1.0 if status == "pass" else 0.0,
    }


class ContextCalibrationTests(unittest.TestCase):
    def test_profile_requires_supported_native_arkts_dimensions(self) -> None:
        normalized = normalize_evaluation_profile(
            profile("page", "callable", "ui_state"), "case-1"
        )

        self.assertEqual("native_arkts", normalized["target_domain"])
        self.assertEqual(
            ["viewmodel"],
            normalize_evaluation_profile(
                profile("viewmodel", "callable", "navigation"), "case-2"
            )["artifact_roles"],
        )
        with self.assertRaises(SystemExit):
            normalize_evaluation_profile({**profile("page", "callable", "ui_state"), "artifact_roles": ["preview"]}, "case-1")

    def test_assessment_reports_macro_metrics_and_coverage_gaps(self) -> None:
        cases = [
            {"id": "page", "evaluation_profile": profile("page", "callable", "ui_state")},
            {"id": "service", "evaluation_profile": profile("service", "file", "resource_io")},
        ]
        contract = {
            "target_domain": "native_arkts",
            "minimum_case_count": 2,
            "required_target_levels": ["file", "callable"],
            "required_artifact_roles": ["page", "service", "utility"],
            "required_mechanism_kinds": ["resource_io", "ui_state"],
        }

        result = assess_calibration(cases, [scored("page"), scored("service", "fail")], contract)

        self.assertEqual("fail", result["status"])
        self.assertEqual(["artifact_roles:utility"], result["contract_gaps"])
        self.assertEqual(0.5, result["macro_metrics"]["artifact_roles"]["pass_rate"])
        self.assertNotIn("task", str(result))

    def test_calibrated_holdout_requires_ets_targets_and_coverage(self) -> None:
        pack = {
            "suite": "holdout",
            "governance": {"calibration": {
                "target_domain": "native_arkts",
                "minimum_case_count": 2,
                "required_target_levels": ["file", "callable"],
                "required_artifact_roles": ["page", "service"],
                "required_mechanism_kinds": ["resource_io", "ui_state"],
            }},
            "cases": [
                {"evaluation_profile": profile("page", "callable", "ui_state"), "oracle": {"expected_files": ["src/Page.ets"]}},
                {"evaluation_profile": profile("service", "file", "resource_io"), "oracle": {"expected_files": ["src/Service.ets"]}},
            ],
        }

        validate_calibrated_holdout(pack)
        pack["cases"][1]["oracle"]["expected_files"] = ["src/Service.ts"]
        with self.assertRaises(SystemExit):
            validate_calibrated_holdout(pack)

    def test_profile_is_available_to_evaluation_but_hidden_from_agent_case(self) -> None:
        pack = {
            "schema_version": "agent-benchmark-cases/v1",
            "suite": "development",
            "cases": [{
                "id": "case-1",
                "task_type": "diagnosis",
                "review_status": "validated",
                "task": {"description": "Locate the durable preference write."},
                "source": {"changed_files": ["src/Storage.ets"]},
                "oracle": {"expected_files": ["src/Storage.ets"], "forbidden_files": []},
                "evaluation_profile": profile("utility", "file", "persistence"),
            }],
        }

        case = validate_case_pack(pack)["cases"][0]

        self.assertEqual("native_arkts", case["evaluation_profile"]["target_domain"])
        self.assertNotIn("evaluation_profile", public_case(case))


if __name__ == "__main__":
    unittest.main()
