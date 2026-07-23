# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.benchmark_failure_analysis import (
    analyze_agent_failures,
    analyze_context_failures,
)


class BenchmarkFailureAnalysisTests(unittest.TestCase):
    def test_context_failures_are_mapped_to_the_correct_owning_layer(self) -> None:
        result = {
            "cases": [
                {
                    "case_id": "missing-anchor",
                    "checks": {
                        "expected_anchors_recalled": False,
                        "minimum_source_span_recall_met": False,
                        "context_within_budget": True,
                    },
                }
            ]
        }
        analysis = analyze_context_failures(result)
        self.assertEqual("repair_required", analysis["status"])
        self.assertEqual("candidate_generation", analysis["primary_failure_class"])
        classes = {item["failure_class"] for item in analysis["failures"]}
        self.assertEqual({"candidate_generation", "passage_selection"}, classes)
        self.assertTrue(all(item["method_reference_ids"] for item in analysis["failures"]))
        self.assertTrue(all(item["prohibited_shortcut"] for item in analysis["failures"]))

    def test_context_pass_has_no_repair_recommendation(self) -> None:
        analysis = analyze_context_failures({"cases": [{"case_id": "ok", "checks": {"x": True}}]})
        self.assertEqual("clear", analysis["status"])
        self.assertEqual([], analysis["failures"])

    def test_agent_quality_and_efficiency_failures_stay_separate(self) -> None:
        result = {
            "gate_checks": {
                "context_agent_root_cause_non_regression": False,
                "complete_pairs": True,
            },
            "efficiency_gate_checks": {
                "token_overhead_within_budget": False,
                "source_search_non_regression": True,
            },
        }
        analysis = analyze_agent_failures(result)
        self.assertEqual("repair_required", analysis["status"])
        self.assertEqual(1, analysis["quality_failure_count"])
        self.assertEqual(1, analysis["efficiency_failure_count"])
        self.assertEqual(
            {"agent_protocol", "agent_efficiency"},
            {item["failure_class"] for item in analysis["failures"]},
        )


if __name__ == "__main__":
    unittest.main()
