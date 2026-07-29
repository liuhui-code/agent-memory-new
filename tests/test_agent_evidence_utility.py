# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.agent_evidence_utility import evaluate_agent_evidence_utility


class AgentEvidenceUtilityTests(unittest.TestCase):
    def test_reports_paired_evidence_utility_without_promotion_authority(self) -> None:
        result = evaluate_agent_evidence_utility(
            [{"id": "case-1", "oracle": {"expected_files": ["src/Profile.ets"]}}],
            [
                observation("baseline", ["src/Other.ets"], "budget_exhausted_report_uncertainty"),
                observation("memory", ["src/Profile.ets"], "evidence_sufficient"),
            ],
        )

        self.assertFalse(result["promotion_eligible"])
        self.assertEqual("informational", result["status"])
        self.assertEqual(1.0, result["metrics"]["memory"]["evidence_sufficiency_rate"])
        self.assertEqual(1.0, result["metrics"]["baseline"]["uncertainty_integrity_rate"])


def observation(variant: str, files: list[str], stop_reason: str) -> dict:
    return {
        "case_id": "case-1",
        "variant": variant,
        "investigated_files": files,
        "causal_level": "supported",
        "stop_reason": stop_reason,
        "memory_anchor_hit_count": 1 if variant == "memory" else 0,
        "source_search_count": 1,
        "non_anchor_file_count": 0,
    }


if __name__ == "__main__":
    unittest.main()
