# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.agent_benchmark_eval import (
    evaluate_agent_benchmark,
    score_observation,
)
from tools.agent_memory_runtime.agent_benchmark_treatment import (
    context_exposure_manifest,
    external_context_projection,
    investigation_contract,
    treatment_metadata,
)
from tools.agent_memory_runtime.agent_benchmark_measurement import measurement_contract_audit
from tools.agent_memory_runtime.agent_benchmark_paired_cost import paired_effect_summary
from tools.agent_memory_runtime.agent_benchmark_protocol import runner_instructions
from tools.agent_memory_runtime.context_capability import summarize_context
from tools.agent_memory_runtime.source_exploration import source_exploration_within_budget


class AgentBenchmarkMeasurementContractTests(unittest.TestCase):
    def test_external_projection_manifest_is_body_free_and_deterministic(self) -> None:
        context = {
            "query_handoff": {
                "code_anchors": [{
                    "file_path": "src/Owner.ets",
                    "source_excerpts": [{"start_line": 4, "content": "secret"}],
                }],
            },
        }

        projected = external_context_projection(context)
        manifest = context_exposure_manifest(projected, "external_metadata_only")

        self.assertNotIn("secret", str(projected))
        self.assertEqual("context-exposure/v1", manifest["schema_version"])
        self.assertEqual("external_metadata_only", manifest["delivery"])
        self.assertEqual(64, len(manifest["payload_digest"]))
        self.assertEqual(manifest, context_exposure_manifest(projected, "external_metadata_only"))

    def test_investigation_contract_is_context_independent(self) -> None:
        baseline = investigation_contract()
        memory = investigation_contract()

        self.assertEqual(baseline, memory)
        self.assertEqual("shared-investigation/v1", baseline["schema_version"])
        self.assertEqual(3, baseline["limits"]["searches"])
        self.assertEqual(runner_instructions("baseline"), runner_instructions("memory"))

    def test_context_gate_reports_the_external_agent_projection(self) -> None:
        context = {
            "query_handoff": {"code_anchors": [{
                "file_path": "src/Owner.ets",
                "source_excerpts": [{
                    "start_line": 2, "end_line": 3, "content": "private body",
                }],
            }]},
        }

        summary = summarize_context("case-1", context, 1, 2)
        exposure = summary["context_exposure"]

        self.assertNotEqual(
            exposure["gate_full"]["payload_digest"],
            exposure["agent_external"]["payload_digest"],
        )
        self.assertEqual("external_metadata_only", exposure["agent_external"]["delivery"])

    def test_v2_treatments_enforce_context_as_the_only_variable(self) -> None:
        values = [
            treatment_observation("baseline", None),
            treatment_observation("memory", {"summary": "context"}),
        ]

        self.assertEqual("pass", measurement_contract_audit(values)["status"])
        values[1]["treatment_metadata"]["investigation_contract_digest"] = "different"
        self.assertEqual("fail", measurement_contract_audit(values)["status"])

    def test_paired_costs_do_not_hide_the_worst_case(self) -> None:
        values = [
            cost_observation("a", "baseline", 100),
            cost_observation("a", "memory", 80),
            cost_observation("b", "baseline", 100),
            cost_observation("b", "memory", 130),
        ]

        tokens = paired_effect_summary(values)["metrics"]["token_estimate"]

        self.assertEqual(0.05, tokens["mean_overhead_ratio"])
        self.assertEqual(0.3, tokens["worst_overhead_ratio"])

    def test_v2_budget_applies_to_baseline_and_memory(self) -> None:
        baseline = exploration_observation("baseline", None)
        memory = exploration_observation("memory", {"summary": "context"})
        self.assertTrue(source_exploration_within_budget([baseline, memory]))

        baseline["source_search_count"] = 4
        self.assertFalse(source_exploration_within_budget([baseline, memory]))

    def test_mechanism_credit_requires_oracle_grounded_span(self) -> None:
        case = benchmark_case()
        grounded = score_observation(case, observation(10, 12))
        wrong_span = score_observation(case, observation(80, 90))

        self.assertEqual(1.0, grounded["mechanism_evidence_score"])
        self.assertTrue(grounded["mechanism_grounded"])
        self.assertEqual(0.0, wrong_span["mechanism_evidence_score"])
        self.assertFalse(wrong_span["causal_level_match"])
        self.assertLess(wrong_span["agent_outcome_score"], grounded["agent_outcome_score"])

    def test_result_separates_protocol_calibration_from_real_cases(self) -> None:
        cases = [
            benchmark_case("mutation", "mutation-case"),
            benchmark_case("reviewed_git_fix", "real-case"),
        ]
        observations = []
        for case in cases:
            for variant in ("baseline", "memory"):
                observations.append({
                    **observation(10, 12),
                    "case_id": case["id"],
                    "variant": variant,
                    "trial_index": 1,
                })

        result = evaluate_agent_benchmark({"suite": "development"}, cases, observations)

        self.assertEqual(1, result["evidence_segments"]["protocol_calibration"]["case_count"])
        self.assertEqual(1, result["evidence_segments"]["real_cases"]["case_count"])


def benchmark_case(kind: str = "reviewed_git_fix", case_id: str = "case-1") -> dict:
    return {
        "id": case_id,
        "task_type": "diagnosis",
        "review_status": "validated",
        "provenance": {"kind": kind},
        "oracle": {
            "expected_files": ["src/Owner.ets"],
            "forbidden_files": [],
            "root_cause_category": "state",
            "expected_causal_level": "supported",
            "mechanism_assertions": [{
                "file_path": "src/Owner.ets",
                "symbol": "load",
                "start_line": 8,
                "end_line": 14,
            }],
        },
    }


def observation(start_line: int, end_line: int) -> dict:
    return {
        "root_cause_category": "state",
        "predicted_files": ["src/Owner.ets"],
        "supporting_files": [],
        "causal_level": "supported",
        "verification_status": "unknown",
        "query_rounds": 1,
        "token_estimate": 100,
        "elapsed_ms": 100,
        "mechanism_evidence": [{
            "file_path": "src/Owner.ets",
            "symbol": "load",
            "start_line": start_line,
            "end_line": end_line,
            "claim": "The returned page replaces the accumulated list.",
        }],
    }


def treatment_observation(variant: str, context: dict | None) -> dict:
    return {
        "variant": variant,
        "latency_metrics_reported": True,
        "treatment_metadata": treatment_metadata(variant, context),
    }


def cost_observation(case_id: str, variant: str, tokens: int) -> dict:
    return {
        "case_id": case_id,
        "trial_index": 1,
        "variant": variant,
        "token_estimate": tokens,
    }


def exploration_observation(variant: str, context: dict | None) -> dict:
    return {
        **treatment_observation(variant, context),
        "exploration_metrics_reported": True,
        "source_file_count": 1,
        "source_search_count": 1,
        "primary_anchor_hit_count": 1 if variant == "memory" else 0,
        "non_anchor_file_count": 0 if variant == "memory" else 1,
        "expansion_rounds": 0,
        "expansion_file_count": 0,
        "expansion_reason_codes": [],
        "stop_reason": "supported_cause_found",
        "evidence_basis": "direct_source_mechanism",
        "mechanism_evidence_files": ["src/Owner.ets"],
        "predicted_files": ["src/Owner.ets"],
        "investigated_files": ["src/Owner.ets"],
    }


if __name__ == "__main__":
    unittest.main()
