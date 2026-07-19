# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from tools.agent_memory_runtime.benchmark_context_setup import validated_reflections
from tools.agent_memory_runtime.context_capability import (
    limit_scenario_cases,
    summarize_context,
)
from tools.agent_memory_runtime.context_capability_cases import expand_context_cases
from tools.agent_memory_runtime.context_capability_eval import (
    evaluate_context_capability,
)
from tools.agent_memory_runtime.context_capability_governance import (
    context_capability_summary,
)
from tools.agent_memory_runtime.context_anchor_selection import (
    path_context_for_log_anchors,
    path_scoped_code_anchors,
    relevant_log_anchors,
)
from tools.agent_memory_runtime.context_compact import (
    diverse_code_anchors,
    minimize_guards,
)
from tools.agent_memory_runtime.query_intents import (
    infer_memory_intent_v2,
    reflection_gate_decision,
)
from tools.agent_memory_runtime.query_handoff import strong_code_identity


class ContextCapabilityEvalTests(unittest.TestCase):
    def test_context_gate_runs_all_scenarios_unless_limit_is_explicit(self) -> None:
        cases = [{"id": f"case-{index}"} for index in range(25)]

        self.assertEqual(cases, limit_scenario_cases(cases, None))
        self.assertEqual(cases[:4], limit_scenario_cases(cases, 4))

    def test_query_variants_expand_with_shared_oracle_and_bounded_ids(self) -> None:
        value = case()
        value["query_variants"] = [
            {"id": "original", "description": "Profile route is wrong."},
            {"id": "zh", "description": "Profile 路由跳错页面。"},
        ]

        expanded = expand_context_cases([value])

        self.assertEqual(
            ["route-case::original", "route-case::zh"],
            [item["id"] for item in expanded],
        )
        self.assertTrue(all(item["scenario_id"] == "route-case" for item in expanded))
        self.assertTrue(all(item["oracle"] == value["oracle"] for item in expanded))
        value["query_variants"] = [{"id": f"v{index}", "description": "x"} for index in range(6)]
        with self.assertRaises(SystemExit):
            expand_context_cases([value])

    def test_query_robustness_groups_variant_failures_by_scenario(self) -> None:
        value = case()
        value["query_variants"] = [
            {"id": "a", "description": "a"},
            {"id": "b", "description": "b"},
        ]
        cases = expand_context_cases([value])
        observations = []
        for item in cases:
            measured = observation()
            measured["case_id"] = item["id"]
            observations.append(measured)
        observations[1]["anchor_paths"] = ["src/Other.ets"]

        result = evaluate_context_capability(cases, observations)

        profile = result["capability_profile"]["query_robustness"]
        self.assertEqual("fail", profile["status"])
        self.assertEqual(1, profile["scenario_count"])
        self.assertEqual(0.5, profile["variant_pass_rate"])
        self.assertEqual(["b"], profile["scenarios"][0]["failed_variants"])

    def test_code_context_gate_scores_retrieval_without_agent_output(self) -> None:
        cases = [case()]
        observations = [observation()]

        result = evaluate_context_capability(cases, observations)

        self.assertEqual("pass", result["system_context_gate"])
        self.assertEqual(1.0, result["capability_profile"]["code_locator"]["anchor_recall"])
        self.assertEqual(
            "informational",
            result["capability_profile"]["source_evidence"]["status"],
        )
        self.assertFalse(result["audit"]["agent_invoked"])
        self.assertFalse(result["audit"]["source_bodies_persisted"])

    def test_forbidden_anchor_and_missing_expected_file_fail_gate(self) -> None:
        value = observation()
        value["anchor_paths"] = ["src/Other.ets"]
        value["primary_anchor_paths"] = ["src/Other.ets"]

        result = evaluate_context_capability([case()], [value])

        scored = result["cases"][0]
        self.assertEqual("fail", result["system_context_gate"])
        self.assertEqual(0.0, scored["anchor_recall"])
        self.assertEqual(["src/Other.ets"], scored["forbidden_anchor_hits"])
        self.assertFalse(scored["checks"]["expected_anchors_recalled"])
        self.assertFalse(scored["checks"]["forbidden_anchors_absent"])

    def test_explicit_log_experience_and_path_requirements_are_gated(self) -> None:
        value = case()
        value["oracle"]["context_requirements"] = {
            "required_log_keywords": ["session invalid"],
            "required_experience_types": ["correction_experience"],
            "required_path_files": ["src/Session.ets"],
            "min_relation_hints": 1,
            "require_source_excerpt": True,
        }
        measured = observation()
        measured.update({
            "log_keywords": ["session invalid"],
            "log_evidence_texts": ["SessionService session invalid"],
            "experience_types": ["correction_experience"],
            "path_files": ["src/Session.ets"],
            "relation_hint_count": 1,
        })

        passed = evaluate_context_capability([value], [measured])
        self.assertEqual("pass", passed["system_context_gate"])
        self.assertEqual("pass", passed["capability_profile"]["log_graph"]["status"])
        self.assertEqual("pass", passed["capability_profile"]["experience"]["status"])
        self.assertEqual("pass", passed["capability_profile"]["causal_context"]["status"])

        measured["log_evidence_texts"] = []
        failed = evaluate_context_capability([value], [measured])
        self.assertEqual("fail", failed["system_context_gate"])
        self.assertFalse(failed["cases"][0]["checks"]["required_log_keywords_recalled"])

    def test_log_oracle_checks_emitter_and_forbidden_noise(self) -> None:
        value = case()
        value["oracle"]["context_requirements"] = {
            "required_log_files": ["src/Session.ets"],
            "forbidden_log_files": ["src/Network.ets"],
            "forbidden_log_keywords": ["generic timeout"],
        }
        measured = observation()
        measured.update({
            "log_anchor_paths": ["src/Session.ets"],
            "log_anchor_count": 1,
            "log_keywords": ["session invalid"],
            "log_evidence_texts": ["SessionService session invalid"],
        })

        passed = evaluate_context_capability([value], [measured])
        self.assertEqual("pass", passed["system_context_gate"])

        measured["log_anchor_paths"].append("src/Network.ets")
        measured["log_evidence_texts"].append("Network generic timeout")
        failed = evaluate_context_capability([value], [measured])
        self.assertFalse(failed["cases"][0]["checks"]["forbidden_log_files_absent"])
        self.assertFalse(failed["cases"][0]["checks"]["forbidden_log_keywords_absent"])

    def test_experience_oracle_separates_main_and_guard_lanes(self) -> None:
        value = case()
        value["oracle"]["context_requirements"] = {
            "require_expected_anchors": False,
            "required_main_experience_phrases": ["bounded session retry"],
            "forbidden_main_experience_phrases": ["retry every failure"],
            "required_guard_experience_phrases": ["401 means invalid session"],
        }
        measured = observation()
        measured.update({
            "main_experience_texts": ["Use bounded session retry after refresh."],
            "guard_experience_texts": ["401 means invalid session, not network timeout."],
            "experience_ref_count": 1,
            "experience_types": ["procedure_experience", "correction_experience"],
        })

        result = evaluate_context_capability([value], [measured])

        self.assertEqual("pass", result["system_context_gate"])
        self.assertEqual("informational", result["capability_profile"]["code_locator"]["status"])
        self.assertEqual("pass", result["capability_profile"]["experience"]["status"])

    def test_causal_oracle_checks_relations_and_forbidden_branch(self) -> None:
        value = case()
        value["oracle"]["context_requirements"] = {
            "required_path_files": ["src/Session.ets"],
            "required_path_relations": ["calls", "emits_log"],
            "forbidden_path_files": ["src/Cache.ets"],
            "min_path_candidates": 1,
        }
        measured = observation()
        measured.update({
            "path_files": ["src/Profile.ets", "src/Session.ets"],
            "path_relations": ["calls", "emits_log"],
            "path_candidate_count": 1,
        })

        passed = evaluate_context_capability([value], [measured])
        self.assertEqual("pass", passed["system_context_gate"])

        measured["path_files"].append("src/Cache.ets")
        failed = evaluate_context_capability([value], [measured])
        self.assertFalse(failed["cases"][0]["checks"]["forbidden_path_files_absent"])

    def test_duplicate_or_missing_observation_fails_closed(self) -> None:
        with self.assertRaises(SystemExit):
            evaluate_context_capability([case()], [])
        with self.assertRaises(SystemExit):
            evaluate_context_capability([case()], [observation(), observation()])

    def test_context_summary_keeps_signals_but_drops_source_bodies(self) -> None:
        context = {
            "schema_version": "agent-context-compact/v1",
            "query_handoff": {
                "code_anchors": [{
                    "file_path": "src/Profile.ets",
                    "role": "primary",
                    "source_excerpts": [{"content": "private-source-marker"}],
                }],
                "log_anchors": [{"file_path": "src/Profile.ets"}],
                "log_keywords": ["route failed"],
                "experience_refs": [{"experience_type": "procedure_experience"}],
                "semantic_refs": [{"semantic_id": 3}],
                "relation_hints": [{"relation": "calls"}],
                "path_context": {
                    "path_candidates": [{
                        "entry": {"file_path": "src/Entry.ets"},
                        "nodes": [{"file_path": "src/Profile.ets"}],
                    }]
                },
            },
            "evidence_gaps": ["runtime_verification_missing"],
            "output_budget": {"estimated_tokens": 321},
        }

        measured = summarize_context("route-case", context, 25, 7)

        self.assertEqual(["src/Profile.ets"], measured["excerpt_paths"])
        self.assertEqual(["src/Entry.ets", "src/Profile.ets"], measured["path_files"])
        self.assertEqual(1, measured["relation_hint_count"])
        self.assertNotIn("private-source-marker", str(measured))

    def test_strong_log_code_identity_gets_one_slot_without_weak_log_noise(self) -> None:
        values = [
            {"source": "wiki", "file_path": "src/Chat.ets", "symbol": "Chat"},
            {"source": "wiki", "file_path": "src/Detail.ets", "symbol": "Detail"},
            {"source": "wiki", "file_path": "src/Bottom.ets", "symbol": "Bottom"},
            {
                "source": "log_emitter",
                "file_path": "src/ChatList.ets",
                "symbol": "Stack",
                "identity_match": True,
            },
            {
                "source": "log_emitter",
                "file_path": "src/Noise.ets",
                "symbol": "debug",
                "identity_match": False,
            },
        ]

        anchors = diverse_code_anchors(values, include_log_emitters=False)

        self.assertEqual("src/ChatList.ets", anchors[1]["file_path"])
        self.assertNotIn("src/Noise.ets", {item["file_path"] for item in anchors})
        self.assertTrue(strong_code_identity({
            "match_reasons": ["exact_function", "log_context"],
            "score": 7.2,
        }))
        self.assertFalse(strong_code_identity({
            "match_reasons": ["log_context"],
            "score": 9.0,
        }))

    def test_governance_summary_exposes_system_gate_separately_from_agent_ab(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            result = evaluate_context_capability([case()], [observation()])
            result["failure_analysis"] = {
                "status": "clear",
                "primary_failure_class": None,
                "failure_count": 0,
            }
            result["case_seal"] = {"status": "verified", "digest": "abc"}
            result["recorded_at"] = "2026-07-18T00:00:00Z"
            (runtime / "last_context_capability.json").write_text(
                json.dumps(result), encoding="utf-8"
            )

            summary = context_capability_summary(SimpleNamespace(runtime_dir=runtime))

        self.assertEqual("pass", summary["system_context_gate"])
        self.assertEqual(1.0, summary["anchor_recall"])
        self.assertEqual(1.0, summary["expected_anchor_mrr"])
        self.assertIsNone(summary["source_span_recall"])
        self.assertEqual("informational", summary["abstention_status"])
        self.assertEqual("pass", summary["query_robustness_status"])
        self.assertEqual(1.0, summary["query_variant_pass_rate"])
        self.assertEqual([], summary["failed_case_ids"])
        self.assertEqual("clear", summary["failure_analysis_status"])
        self.assertEqual("verified", summary["case_seal_status"])

    def test_context_setup_accepts_only_bounded_reflection_fixtures(self) -> None:
        values = validated_reflections({"reflections": [{"task": "one"}]})
        self.assertEqual([{"task": "one"}], values)
        with self.assertRaises(SystemExit):
            validated_reflections({"commands": ["unsafe"]})
        with self.assertRaises(SystemExit):
            validated_reflections({"reflections": [{}] * 9})

    def test_minimal_guard_keeps_identity_and_path_scope_drops_unrelated_backfill(self) -> None:
        payload = {
            "correction_guards": [{
                "id": 1,
                "experience_type": "correction_experience",
                "task": "401 means invalid session correction",
                "warnings": ["bounded warning"],
            }],
            "semantic_patch_notes": [],
            "blocked_memory_notes": [],
            "conflict_notes": [],
        }
        minimize_guards(payload)
        self.assertEqual(
            "401 means invalid session correction",
            payload["correction_guards"][0]["task"],
        )
        anchors = [
            {"file_path": "src/Payment.ets"},
            {"file_path": "src/Network.ets"},
        ]
        path = {
            "activated": True,
            "path_candidates": [{
                "entry": {"file_path": "src/Checkout.ets"},
                "emitter": {"file_path": "src/Payment.ets"},
                "nodes": [],
            }],
        }
        self.assertEqual(
            ["src/Payment.ets"],
            [item["file_path"] for item in path_scoped_code_anchors(anchors, path)],
        )

    def test_negative_log_clause_scopes_logs_and_paths(self) -> None:
        logs = [
            {"file_path": "src/Payment.ets", "message_template": "duplicate order rejected"},
            {"file_path": "src/Network.ets", "message_template": "generic network timeout"},
        ]
        selected = relevant_log_anchors(
            logs,
            "Find duplicate order rejected without following generic network timeout noise.",
        )
        path = {
            "activated": True,
            "path_candidates": [
                {"emitter": {"file_path": "src/Payment.ets"}},
                {"emitter": {"file_path": "src/Network.ets"}},
            ],
        }

        self.assertEqual(["src/Payment.ets"], [item["file_path"] for item in selected])
        scoped = path_context_for_log_anchors(path, selected)
        self.assertEqual(1, len(scoped["path_candidates"]))

    def test_semantic_question_and_procedure_correction_guard_intents(self) -> None:
        self.assertEqual(
            "code_business_semantics",
            infer_memory_intent_v2("In current ProfileService, what does refresh 401 mean?"),
        )
        self.assertEqual(
            "code_business_semantics",
            infer_memory_intent_v2("Explain the business meaning of ProfileService refresh 401."),
        )
        self.assertEqual(
            "code_business_semantics",
            infer_memory_intent_v2("ProfileService refresh 401 的业务含义是什么？"),
        )
        relevant = reflection_gate_decision(
            "Use bounded session retry workflow to diagnose profile load failed.",
            "procedure_reuse",
            {
                "experience_type": "correction_experience",
                "trigger_condition": "profile load failed session invalid",
                "confidence": 0.9,
                "quality_score": 0.9,
            },
            "procedure_reuse",
        )
        unrelated = reflection_gate_decision(
            "How to diagnose profile route blank screen?",
            "procedure_reuse",
            {
                "experience_type": "correction_experience",
                "trigger_condition": "runtime evidence includes session invalid",
                "confidence": 0.9,
                "quality_score": 0.9,
            },
            "procedure_reuse",
        )
        self.assertTrue(relevant["allowed"])
        self.assertFalse(unrelated["allowed"])


def case() -> dict:
    return {
        "id": "route-case",
        "task_type": "diagnosis",
        "task": {"description": "Profile route opens the wrong destination."},
        "oracle": {
            "expected_files": ["src/Profile.ets"],
            "forbidden_files": ["src/Other.ets"],
        },
    }


def observation() -> dict:
    return {
        "schema_version": "agent-context-capability-observation/v1",
        "case_id": "route-case",
        "context_schema_version": "agent-context-compact/v1",
        "anchor_paths": ["src/Profile.ets", "src/Support.ets"],
        "ordered_anchor_paths": ["src/Profile.ets", "src/Support.ets"],
        "primary_anchor_paths": ["src/Profile.ets"],
        "excerpt_paths": ["src/Profile.ets"],
        "excerpt_spans": [],
        "log_anchor_paths": [],
        "log_keywords": [],
        "log_evidence_texts": [],
        "experience_types": [],
        "main_experience_texts": [],
        "guard_experience_texts": [],
        "semantic_ref_count": 0,
        "path_files": [],
        "path_relations": [],
        "path_candidate_count": 0,
        "relation_hint_count": 0,
        "evidence_gaps": [],
        "context_token_estimate": 420,
        "memory_prepare_ms": 20,
        "query_elapsed_ms": 5,
    }


if __name__ == "__main__":
    unittest.main()
