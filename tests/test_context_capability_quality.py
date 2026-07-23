# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.context_capability_eval import evaluate_context_capability
from tools.agent_memory_runtime.context_compact import compact_context


class ContextCapabilityQualityTests(unittest.TestCase):
    def test_top_k_precision_and_source_span_are_hard_gates(self) -> None:
        value = capability_case({
            "required_top_k": 2,
            "min_anchor_precision": 0.5,
            "required_source_spans": [{
                "file_path": "src/Profile.ets",
                "start_line": 40,
                "end_line": 55,
            }],
            "min_source_span_recall": 1.0,
            "require_source_excerpt": True,
        })
        measured = capability_observation()

        passed = evaluate_context_capability([value], [measured])
        self.assertEqual("pass", passed["system_context_gate"])
        self.assertEqual(1, passed["cases"][0]["first_expected_anchor_rank"])
        self.assertEqual(1.0, passed["cases"][0]["source_span_recall"])

        measured["ordered_anchor_paths"] = ["src/Noise.ets", "src/Other.ets", "src/Profile.ets"]
        measured["anchor_paths"] = list(measured["ordered_anchor_paths"])
        failed = evaluate_context_capability([value], [measured])
        self.assertFalse(failed["cases"][0]["checks"]["expected_anchors_within_top_k"])
        self.assertFalse(failed["cases"][0]["checks"]["minimum_anchor_precision_met"])

    def test_abstention_requires_empty_evidence_and_declared_gaps(self) -> None:
        value = capability_case({
            "require_expected_anchors": False,
            "require_abstention": True,
            "required_evidence_gaps": ["no_code_anchor", "no_log_anchor"],
        })
        measured = capability_observation()
        measured.update({
            "anchor_paths": [],
            "ordered_anchor_paths": [],
            "primary_anchor_paths": [],
            "excerpt_paths": [],
            "excerpt_spans": [],
            "anchor_count": 0,
            "evidence_gaps": ["no_code_anchor", "no_log_anchor"],
        })

        passed = evaluate_context_capability([value], [measured])
        self.assertEqual("pass", passed["capability_profile"]["abstention"]["status"])

        measured["anchor_count"] = 1
        failed = evaluate_context_capability([value], [measured])
        self.assertFalse(failed["cases"][0]["checks"]["abstention_observed"])

    def test_compact_gaps_describe_final_not_suppressed_evidence(self) -> None:
        compact = compact_context({
            "query": "unknown incident",
            "query_handoff": {
                "log_anchors": [],
                "code_anchors": [{
                    "source": "log_emitter",
                    "file_path": "src/Noise.ets",
                    "identity_match": False,
                }],
                "path_context": {"activated": False, "path_candidates": []},
            },
        })

        self.assertEqual([], compact["query_handoff"]["code_anchors"])
        self.assertIn("no_code_anchor", compact["evidence_gaps"])
        self.assertIn("no_log_anchor", compact["evidence_gaps"])


def capability_case(requirements: dict) -> dict:
    return {
        "id": "quality-case",
        "task_type": "diagnosis",
        "task": {"description": "Profile issue"},
        "oracle": {
            "expected_files": ["src/Profile.ets"],
            "forbidden_files": [],
            "context_requirements": requirements,
        },
    }


def capability_observation() -> dict:
    return {
        "schema_version": "agent-context-capability-observation/v1",
        "case_id": "quality-case",
        "context_schema_version": "agent-context-compact/v1",
        "anchor_paths": ["src/Profile.ets", "src/Support.ets"],
        "ordered_anchor_paths": ["src/Profile.ets", "src/Support.ets"],
        "primary_anchor_paths": ["src/Profile.ets"],
        "excerpt_paths": ["src/Profile.ets"],
        "excerpt_spans": [{"file_path": "src/Profile.ets", "start_line": 35, "end_line": 60}],
        "anchor_count": 2,
        "log_anchor_count": 0,
        "experience_ref_count": 0,
        "semantic_ref_count": 0,
        "path_candidate_count": 0,
        "relation_hint_count": 0,
        "evidence_gaps": [],
        "context_token_estimate": 400,
    }


if __name__ == "__main__":
    unittest.main()
