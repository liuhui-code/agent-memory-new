# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.context_evidence_funnel import (
    assess_evidence_funnel,
    evidence_funnel_profile,
)


class ContextEvidenceFunnelTests(unittest.TestCase):
    def test_reports_first_missing_callable_after_file_survives(self) -> None:
        result = assess_evidence_funnel(
            {"src/Profile.ets"},
            {"required_source_spans": [{"file_path": "src/Profile.ets", "symbol": "commit"}]},
            {
                "candidate_anchor_paths": ["src/Profile.ets"],
                "hierarchical_file_paths": ["src/Profile.ets"],
                "hierarchical_callable_refs": [],
                "hierarchical_source_ranges": [],
                "callable_evidence": {},
                "primary_anchor_paths": ["src/Profile.ets"],
                "anchor_paths": ["src/Profile.ets"],
            },
        )

        self.assertEqual("callable", result["first_loss"])
        self.assertTrue(result["stages"]["candidate_file"])
        self.assertFalse(result["stages"]["callable"])

    def test_profile_is_informational_and_aggregates_stage_rates(self) -> None:
        result = evidence_funnel_profile([
            {"evidence_funnel": {"first_loss": "callable", "stages": {"candidate_file": True}}},
            {"evidence_funnel": {"first_loss": "evidence_primary", "stages": {"candidate_file": False}}},
        ])

        self.assertEqual("informational", result["status"])
        self.assertEqual({"callable": 1, "evidence_primary": 1}, result["first_loss_counts"])
        self.assertEqual(0.5, result["stage_pass_rates"]["candidate_file"])


if __name__ == "__main__":
    unittest.main()
