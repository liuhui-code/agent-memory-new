# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.context_capability_cases import expand_context_cases
from tools.agent_memory_runtime.context_capability_eval import evaluate_context_capability


class ContextCapabilityStageTests(unittest.TestCase):
    def test_stage_variant_overrides_only_its_context_oracle(self) -> None:
        value = case()
        value["query_variants"] = [
            {
                "id": "orientation",
                "investigation_stage": "orientation",
                "description": "The bridge call exits the application.",
                "oracle_override": {
                    "expected_files": ["src/BridgeEntry.ets"],
                    "context_requirements": {"required_top_k": 1},
                },
            },
            {
                "id": "focused",
                "investigation_stage": "focused",
                "description": "The undefined native method is thrown from the bridge.",
                "oracle_override": {
                    "expected_files": ["src/BaseBridge.ets"],
                    "context_requirements": {"required_top_k": 2},
                },
            },
        ]

        expanded = expand_context_cases([value])

        self.assertEqual("orientation", expanded[0]["investigation_stage"])
        self.assertEqual(["src/BridgeEntry.ets"], expanded[0]["oracle"]["expected_files"])
        self.assertEqual(["src/BaseBridge.ets"], expanded[1]["oracle"]["expected_files"])
        self.assertEqual(["src/FinalFix.ets"], value["oracle"]["expected_files"])
        self.assertTrue(expanded[0]["oracle"]["context_requirements"]["require_source_excerpt"])

    def test_oracle_override_requires_a_known_investigation_stage(self) -> None:
        value = case()
        value["query_variants"] = [{
            "id": "focused",
            "description": "candidate",
            "oracle_override": {"expected_files": ["src/BaseBridge.ets"]},
        }]
        with self.assertRaisesRegex(SystemExit, "investigation_stage"):
            expand_context_cases([value])

        value["query_variants"][0]["investigation_stage"] = "diagnose"
        with self.assertRaisesRegex(SystemExit, "investigation_stage"):
            expand_context_cases([value])

    def test_stage_profile_reports_each_step_and_complete_scenarios(self) -> None:
        value = case()
        value["query_variants"] = [
            {
                "id": "orientation",
                "investigation_stage": "orientation",
                "description": "first",
                "oracle_override": {"expected_files": ["src/Entry.ets"]},
            },
            {
                "id": "focused",
                "investigation_stage": "focused",
                "description": "second",
                "oracle_override": {"expected_files": ["src/Owner.ets"]},
            },
        ]
        cases = expand_context_cases([value])
        observations = [
            observation(cases[0]["id"], "src/Entry.ets"),
            observation(cases[1]["id"], "src/Owner.ets"),
        ]

        result = evaluate_context_capability(cases, observations)

        profile = result["capability_profile"]["investigation_stages"]
        self.assertEqual("pass", profile["status"])
        self.assertEqual(1, profile["complete_scenario_count"])
        self.assertEqual(1.0, profile["stages"]["orientation"]["pass_rate"])
        self.assertEqual(1.0, profile["stages"]["focused"]["pass_rate"])

    def test_multiple_wordings_in_one_stage_must_all_pass(self) -> None:
        value = case()
        value["query_variants"] = [
            {
                "id": "orientation-a",
                "investigation_stage": "orientation",
                "description": "first wording",
                "oracle_override": {"expected_files": ["src/Entry.ets"]},
            },
            {
                "id": "orientation-b",
                "investigation_stage": "orientation",
                "description": "second wording",
                "oracle_override": {"expected_files": ["src/Entry.ets"]},
            },
        ]
        cases = expand_context_cases([value])
        observations = [
            observation(cases[0]["id"], "src/Entry.ets"),
            observation(cases[1]["id"], "src/Noise.ets"),
        ]

        result = evaluate_context_capability(cases, observations)

        profile = result["capability_profile"]["investigation_stages"]
        self.assertEqual("fail", profile["scenarios"][0]["stages"]["orientation"])
        self.assertEqual(0, profile["complete_scenario_count"])


def case() -> dict:
    return {
        "id": "bridge-crash",
        "task_type": "diagnosis",
        "task": {"description": "The bridge call exits the application."},
        "oracle": {
            "expected_files": ["src/FinalFix.ets"],
            "forbidden_files": [],
            "context_requirements": {"require_source_excerpt": True},
        },
    }


def observation(case_id: str, file_path: str) -> dict:
    return {
        "schema_version": "agent-context-capability-observation/v1",
        "case_id": case_id,
        "context_schema_version": "agent-context-compact/v1",
        "anchor_paths": [file_path],
        "ordered_anchor_paths": [file_path],
        "primary_anchor_paths": [file_path],
        "candidate_anchor_paths": [file_path],
        "excerpt_paths": [file_path],
        "excerpt_spans": [],
        "log_anchor_paths": [],
        "log_keywords": [],
        "log_evidence_texts": [],
        "experience_types": [],
        "main_experience_texts": [],
        "guard_experience_texts": [],
        "path_files": [],
        "path_relations": [],
        "path_candidate_count": 0,
        "relation_hint_count": 0,
        "evidence_gaps": [],
        "context_token_estimate": 320,
        "memory_prepare_ms": 10,
        "query_elapsed_ms": 5,
    }


if __name__ == "__main__":
    unittest.main()
