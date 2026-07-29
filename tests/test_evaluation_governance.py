# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.evaluation_governance import validate_evaluation_governance


class EvaluationGovernanceTests(unittest.TestCase):
    def test_legacy_pack_remains_unclassified_and_valid(self) -> None:
        self.assertEqual(
            "legacy_unclassified",
            validate_evaluation_governance({"suite": "development", "cases": []})["status"],
        )

    def test_classified_development_pack_requires_lineage(self) -> None:
        pack = governed_pack("development", "editable", "project_neutral")

        result = validate_evaluation_governance(pack)

        self.assertTrue(result["tuning_allowed"])
        self.assertEqual("development", result["split"])

    def test_calibration_and_holdout_policies_fail_closed(self) -> None:
        with self.assertRaisesRegex(SystemExit, "frozen"):
            validate_evaluation_governance(governed_pack("calibration", "editable", "project_neutral"))
        with self.assertRaisesRegex(SystemExit, "external_holdout"):
            validate_evaluation_governance(governed_pack("holdout", "sealed", "project_neutral"))


def governed_pack(split: str, policy: str, isolation: str) -> dict:
    return {
        "suite": "holdout" if split == "holdout" else "development",
        "governance": {"evaluation": {
            "schema_version": "agent-evaluation-governance/v1",
            "split": split,
            "change_policy": policy,
            "source_isolation": isolation,
        }},
        "cases": [{"id": "case-1", "provenance": {
            "source_family": "test", "independence_basis": "separate fixture",
        }}],
    }


if __name__ == "__main__":
    unittest.main()
