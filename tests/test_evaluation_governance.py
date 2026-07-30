# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.evaluation_governance import (
    assess_promotion_policy,
    validate_evaluation_governance,
)


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

    def test_development_pack_can_use_reviewed_lineage_defaults(self) -> None:
        pack = governed_pack("development", "editable", "project_neutral")
        pack["cases"][0].pop("provenance")
        pack["governance"]["evaluation"]["lineage_defaults"] = {
            "source_family": "system-capability-fixtures/v1",
            "independence_basis": "reviewed project-neutral synthetic fixtures",
        }

        result = validate_evaluation_governance(pack)

        self.assertEqual("pack_defaults", result["lineage_mode"])

    def test_holdout_cannot_inherit_pack_level_lineage(self) -> None:
        pack = governed_pack("holdout", "sealed", "external_holdout")
        pack["cases"][0]["provenance"] = {"kind": "external_fixture"}
        pack["governance"]["evaluation"]["lineage_defaults"] = {
            "source_family": "external-project/v1",
            "independence_basis": "reviewed after implementation freeze",
        }

        with self.assertRaisesRegex(SystemExit, "explicit case lineage"):
            validate_evaluation_governance(pack)

    def test_calibration_and_holdout_policies_fail_closed(self) -> None:
        with self.assertRaisesRegex(SystemExit, "frozen"):
            validate_evaluation_governance(governed_pack("calibration", "editable", "project_neutral"))
        with self.assertRaisesRegex(SystemExit, "external_holdout"):
            validate_evaluation_governance(governed_pack("holdout", "sealed", "project_neutral"))

    def test_unclassified_pass_cannot_claim_external_promotion(self) -> None:
        policy = assess_promotion_policy(
            "pass",
            "not_required",
            {"status": "legacy_unclassified", "enforced": False},
            {"status": "unsealed", "required": False},
        )

        self.assertFalse(policy["eligible"])
        self.assertEqual("classify_evaluation_pack", policy["next_gate"])
        self.assertIn("evaluation_governance_not_enforced", policy["reasons"])

    def test_development_pass_stays_valid_without_becoming_promotion_evidence(self) -> None:
        policy = assess_promotion_policy(
            "pass",
            "not_required",
            governed_result("development"),
            {"status": "unsealed", "required": False},
        )

        self.assertFalse(policy["eligible"])
        self.assertEqual("prepare_external_holdout", policy["next_gate"])

    def test_only_verified_classified_holdout_can_reach_agent_ab(self) -> None:
        policy = assess_promotion_policy(
            "pass",
            "pass",
            governed_result("holdout"),
            {"status": "verified", "required": True},
        )

        self.assertTrue(policy["eligible"])
        self.assertEqual("paired_external_agent_ab", policy["next_gate"])
        self.assertEqual([], policy["reasons"])


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


def governed_result(split: str) -> dict:
    return {
        "status": "classified",
        "enforced": True,
        "split": split,
        "change_policy": "sealed" if split == "holdout" else "editable",
        "source_isolation": "external_holdout" if split == "holdout" else "project_neutral",
    }


if __name__ == "__main__":
    unittest.main()
