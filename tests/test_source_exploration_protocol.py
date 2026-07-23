# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.agent_benchmark_protocol import validate_observation
from tools.agent_memory_runtime.source_exploration import (
    assign_anchor_roles,
    source_exploration_within_budget,
)


class SourceExplorationProtocolTests(unittest.TestCase):
    def test_protocol_marks_complete_exploration_metrics_as_reported(self) -> None:
        observation = validate_observation(response())

        self.assertTrue(observation["exploration_metrics_reported"])
        self.assertEqual(["missing_caller"], observation["expansion_reason_codes"])
        self.assertEqual(["src/Router.ets"], observation["supporting_files"])
        self.assertTrue(source_exploration_within_budget([observation]))

    def test_unknown_reason_fails_budget_gate_without_rejecting_response(self) -> None:
        value = response()
        value["expansion_reason_codes"] = ["look_around"]
        value["expansion_trace"][0]["reason"] = "look_around"

        observation = validate_observation(value)

        self.assertFalse(source_exploration_within_budget([observation]))

    def test_anchor_roles_and_each_expansion_budget_are_bounded(self) -> None:
        anchors = assign_anchor_roles([{"file_path": f"src/{index}.ets"} for index in range(8)])
        observation = validate_observation(response())

        self.assertEqual(["primary"] * 3, [item["role"] for item in anchors[:3]])
        self.assertEqual(["expansion"] * 2, [item["role"] for item in anchors[3:]])
        self.assertEqual(5, len(anchors))

        observation["source_file_count"] = 5
        observation["primary_anchor_hit_count"] = 1
        self.assertFalse(source_exploration_within_budget([observation]))

    def test_source_search_budget_is_enforced(self) -> None:
        observation = validate_observation(response())
        observation["source_search_count"] = 4

        self.assertFalse(source_exploration_within_budget([observation]))

    def test_audited_codex_policies_require_search_telemetry(self) -> None:
        for policy in (
            "anchor_first_gap_driven_v4",
            "anchor_first_sufficient_evidence_v5",
            "anchor_first_ledgered_stop_v6",
            "anchor_first_search_ledger_v7",
            "anchor_first_deterministic_expansion_v8",
        ):
            with self.subTest(policy=policy):
                observation = validate_observation(response())
                observation["runner_metadata"] = {
                    "runner": "codex_cli",
                    "retrieval_policy": policy,
                }

                self.assertFalse(source_exploration_within_budget([observation]))
                observation["source_search_count_source"] = "runner_telemetry"
                if policy == "anchor_first_ledgered_stop_v6":
                    observation["cost_metrics_reported"] = True
                    observation["source_read_count"] = 2
                if policy == "anchor_first_deterministic_expansion_v8":
                    observation.update({
                        "expansion_file_count": 1,
                        "expansion_rounds": 1,
                        "expansion_accounting_source": "runner_investigated_files",
                    })
                self.assertTrue(source_exploration_within_budget([observation]))

    def test_v6_codex_runner_enforces_read_ledger(self) -> None:
        value = response()
        value.update({
            "cost_metrics_reported": True,
            "source_read_count": 2,
        })
        observation = validate_observation(value)
        observation["runner_metadata"] = {
            "runner": "codex_cli",
            "retrieval_policy": "anchor_first_ledgered_stop_v6",
        }
        observation["source_search_count_source"] = "runner_telemetry"

        self.assertTrue(source_exploration_within_budget([observation]))
        observation["source_read_count"] = 3
        self.assertFalse(source_exploration_within_budget([observation]))

    def test_v7_read_amplification_does_not_change_quality_gate(self) -> None:
        value = response()
        value.update({
            "cost_metrics_reported": True,
            "source_read_count": 5,
        })
        observation = validate_observation(value)
        observation["runner_metadata"] = {
            "runner": "codex_cli",
            "retrieval_policy": "anchor_first_search_ledger_v7",
        }
        observation["source_search_count_source"] = "runner_telemetry"

        self.assertTrue(source_exploration_within_budget([observation]))

    def test_v8_uses_runner_expansion_count_instead_of_trace_coverage(self) -> None:
        value = response()
        value.update({
            "investigated_files": [
                "src/Profile.ets", "src/A.ets", "src/B.ets", "src/C.ets",
            ],
            "supporting_files": ["src/A.ets", "src/B.ets", "src/C.ets"],
            "source_file_count": 4,
            "primary_anchor_hit_count": 1,
            "non_anchor_file_count": 3,
            "expansion_file_count": 3,
            "expansion_rounds": 2,
            "expansion_accounting_source": "runner_investigated_files",
            "expansion_trace": [
                {"reason": "missing_caller", "files": ["src/A.ets", "src/B.ets"]},
            ],
        })
        observation = validate_observation(value)
        observation["runner_metadata"] = {
            "runner": "codex_cli",
            "retrieval_policy": "anchor_first_deterministic_expansion_v8",
        }
        observation["source_search_count_source"] = "runner_telemetry"

        self.assertEqual(2, observation["expansion_rounds"])
        self.assertTrue(source_exploration_within_budget([observation]))

        observation["expansion_file_count"] = 2
        self.assertFalse(source_exploration_within_budget([observation]))

    def test_v7_still_requires_complete_expansion_trace(self) -> None:
        value = response()
        value.update({
            "investigated_files": ["src/Profile.ets", "src/Router.ets", "src/A.ets"],
            "supporting_files": ["src/Router.ets", "src/A.ets"],
            "source_file_count": 3,
            "primary_anchor_hit_count": 1,
            "non_anchor_file_count": 2,
        })
        observation = validate_observation(value)
        observation["runner_metadata"] = {
            "runner": "codex_cli",
            "retrieval_policy": "anchor_first_search_ledger_v7",
        }
        observation["source_search_count_source"] = "runner_telemetry"

        self.assertFalse(source_exploration_within_budget([observation]))

    def test_supported_stop_requires_direct_mechanism_in_causal_file(self) -> None:
        inference_only = validate_observation(response())
        inference_only["evidence_basis"] = "inference_only"
        self.assertFalse(source_exploration_within_budget([inference_only]))

        unrelated = validate_observation(response())
        unrelated["mechanism_evidence_files"] = ["src/Router.ets"]
        self.assertFalse(source_exploration_within_budget([unrelated]))

        boundary_supported = validate_observation(response())
        boundary_supported["mechanism_evidence_files"] = [
            "src/Profile.ets",
            "src/Router.ets",
        ]
        self.assertTrue(source_exploration_within_budget([boundary_supported]))

        direct = validate_observation(response())
        self.assertTrue(source_exploration_within_budget([direct]))

    def test_two_rounds_allow_three_audited_non_anchor_files(self) -> None:
        value = response()
        value.update({
            "supporting_files": ["src/A.ets", "src/B.ets", "src/C.ets"],
            "investigated_files": [
                "src/Profile.ets", "src/A.ets", "src/B.ets", "src/C.ets",
            ],
            "source_file_count": 4,
            "primary_anchor_hit_count": 1,
            "non_anchor_file_count": 3,
            "expansion_rounds": 2,
            "expansion_reason_codes": ["missing_caller", "missing_state_owner"],
            "expansion_trace": [
                {"reason": "missing_caller", "files": ["src/A.ets", "src/B.ets"]},
                {"reason": "missing_state_owner", "files": ["src/C.ets"]},
            ],
        })

        self.assertTrue(source_exploration_within_budget([validate_observation(value)]))

    def test_two_rounds_preserve_repeated_reasons_and_allow_four_files(self) -> None:
        value = response()
        value.update({
            "supporting_files": [
                "src/Primary2.ets", "src/Primary3.ets",
                "src/A.ets", "src/B.ets", "src/C.ets", "src/D.ets",
            ],
            "investigated_files": [
                "src/Profile.ets", "src/Primary2.ets", "src/Primary3.ets",
                "src/A.ets", "src/B.ets", "src/C.ets", "src/D.ets",
            ],
            "source_file_count": 7,
            "primary_anchor_hit_count": 3,
            "non_anchor_file_count": 4,
            "expansion_rounds": 99,
            "expansion_reason_codes": ["missing_caller"],
            "expansion_trace": [
                {"reason": "missing_caller", "files": ["src/A.ets", "src/B.ets"]},
                {"reason": "missing_caller", "files": ["src/C.ets", "src/D.ets"]},
            ],
        })

        observation = validate_observation(value)

        self.assertEqual(2, observation["expansion_rounds"])
        self.assertEqual(
            ["missing_caller", "missing_caller"],
            observation["expansion_reason_codes"],
        )
        self.assertTrue(source_exploration_within_budget([observation]))

    def test_expansion_trace_rejects_unaudited_or_oversized_rounds(self) -> None:
        unaudited = response()
        unaudited["expansion_trace"][0]["files"] = ["src/Unknown.ets"]
        self.assertFalse(source_exploration_within_budget([validate_observation(unaudited)]))

        oversized = response()
        oversized["expansion_trace"][0]["files"] = [
            "src/Router.ets", "src/A.ets", "src/B.ets",
        ]
        oversized["investigated_files"].extend(["src/A.ets", "src/B.ets"])
        self.assertFalse(source_exploration_within_budget([validate_observation(oversized)]))

    def test_inference_only_can_stop_with_explicit_uncertainty(self) -> None:
        observation = validate_observation(response())
        observation["evidence_basis"] = "inference_only"
        observation["mechanism_evidence_files"] = []
        observation["stop_reason"] = "no_new_evidence"
        observation["causal_level"] = "association"

        self.assertTrue(source_exploration_within_budget([observation]))

    def test_old_response_does_not_activate_new_gate(self) -> None:
        value = response()
        for key in (
            "expansion_rounds",
            "source_search_count",
            "expansion_reason_codes",
            "stop_reason",
            "primary_anchor_hit_count",
            "non_anchor_file_count",
        ):
            value.pop(key)

        observation = validate_observation(value)

        self.assertFalse(observation["exploration_metrics_reported"])
        self.assertTrue(source_exploration_within_budget([observation]))


def response() -> dict:
    return {
        "schema_version": "agent-benchmark-response/v1",
        "case_id": "case-1",
        "variant": "memory",
        "root_cause_category": "route",
        "predicted_files": ["src/Profile.ets"],
        "supporting_files": ["src/Router.ets", "src/Profile.ets"],
        "investigated_files": ["src/Profile.ets", "src/Router.ets"],
        "causal_level": "supported",
        "verification_status": "unknown",
        "query_rounds": 1,
        "source_search_count": 2,
        "expansion_rounds": 1,
        "expansion_reason_codes": ["missing_caller"],
        "expansion_trace": [
            {"reason": "missing_caller", "files": ["src/Router.ets"]}
        ],
        "stop_reason": "supported_cause_found",
        "evidence_basis": "direct_source_mechanism",
        "mechanism_evidence_files": ["src/Profile.ets"],
        "source_file_count": 2,
        "memory_anchor_hit_count": 1,
        "primary_anchor_hit_count": 1,
        "non_anchor_file_count": 1,
        "token_estimate": 100,
        "elapsed_ms": 10,
        "summary": "The route caller selects the wrong target.",
    }


if __name__ == "__main__":
    unittest.main()
