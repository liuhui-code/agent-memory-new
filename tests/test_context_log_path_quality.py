# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from tools.agent_memory_runtime.context_capability import summarize_context
from tools.agent_memory_runtime.context_capability_eval import evaluate_context_capability
from tools.agent_memory_runtime.context_capability_governance import context_capability_summary


class ContextLogPathQualityTests(unittest.TestCase):
    def test_summary_preserves_log_path_identity_and_truncation(self) -> None:
        measured = summarize_context(
            "wrapped-log",
            compact_context([
                log_anchor(
                    "static_wrapped",
                    [
                        "src/pages/ProfilePage.ets#load",
                        "src/services/ProfileService.ets#reportFailure",
                        "src/log/Logger.ets#error",
                    ],
                    truncated=True,
                ),
            ]),
            12,
            4,
        )

        self.assertEqual(["static_wrapped"], measured["log_evidence_classes"])
        self.assertEqual(1, measured["wrapped_log_path_count"])
        self.assertEqual(1, measured["truncated_log_path_count"])
        self.assertEqual(
            "src/pages/ProfilePage.ets#load",
            measured["log_path_candidates"][0]["locations"][0],
        )

    def test_log_path_oracle_scores_recall_precision_and_evidence_class(self) -> None:
        case = capability_case({
            "required_log_evidence_classes": ["direct", "static_wrapped"],
            "required_log_effect_paths": [path_spec("static_wrapped", [
                "src/pages/ProfilePage.ets#load",
                "src/services/ProfileService.ets#reportFailure",
            ])],
            "allowed_log_effect_paths": [path_spec("static_wrapped", [
                "src/pages/ProfilePage.ets#load",
                "src/services/ProfileService.ets#reportFailure",
            ])],
            "min_log_path_precision": 1.0,
            "max_log_path_candidates": 2,
        })
        measured = observation([
            log_candidate("static_wrapped", [
                "src/pages/ProfilePage.ets#load",
                "src/services/ProfileService.ets#reportFailure",
                "src/log/Logger.ets#error",
            ]),
        ], evidence_classes=["direct", "static_wrapped"])

        result = evaluate_context_capability([case], [measured])

        scored = result["cases"][0]
        self.assertEqual("pass", result["system_context_gate"])
        self.assertEqual(1.0, scored["log_path_recall"])
        self.assertEqual(1.0, scored["log_path_precision"])
        self.assertEqual("pass", result["capability_profile"]["log_path_quality"]["status"])

    def test_unexpected_inferred_path_and_hidden_truncation_fail_closed(self) -> None:
        expected = path_spec("static_wrapped", [
            "src/pages/ProfilePage.ets#load",
            "src/services/ProfileService.ets#reportFailure",
        ])
        case = capability_case({
            "required_log_effect_paths": [expected],
            "allowed_log_effect_paths": [expected],
            "min_log_path_precision": 1.0,
            "max_log_path_candidates": 1,
            "require_log_truncation_signal": True,
        })
        measured = observation([
            log_candidate("static_wrapped", expected["locations"]),
            log_candidate("inferred_wrapped", [
                "src/pages/ProfilePage.ets#load",
                "src/noise/RemoteReporter.ets#report",
            ]),
        ])

        result = evaluate_context_capability([case], [measured])

        scored = result["cases"][0]
        self.assertEqual("fail", result["system_context_gate"])
        self.assertEqual(0.5, scored["log_path_precision"])
        self.assertFalse(scored["checks"]["minimum_log_path_precision_met"])
        self.assertFalse(scored["checks"]["maximum_log_path_candidates_met"])
        self.assertFalse(scored["checks"]["log_path_truncation_reported"])

    def test_invalid_log_path_oracle_is_rejected(self) -> None:
        value = capability_case({
            "required_log_effect_paths": [{
                "evidence_class": "static_wrapped",
                "locations": ["src/Profile.ets#load"] * 9,
            }],
        })

        with self.assertRaisesRegex(SystemExit, "log effect path"):
            evaluate_context_capability([value], [observation([])])

    def test_governance_summary_exposes_log_path_metrics(self) -> None:
        expected = path_spec("static_wrapped", ["src/Profile.ets#load"])
        result = evaluate_context_capability(
            [capability_case({
                "required_log_effect_paths": [expected],
                "allowed_log_effect_paths": [expected],
                "min_log_path_precision": 1.0,
            })],
            [observation([log_candidate("static_wrapped", expected["locations"])])],
        )
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            (runtime / "last_context_capability.json").write_text(
                json.dumps(result), encoding="utf-8"
            )

            summary = context_capability_summary(SimpleNamespace(runtime_dir=runtime))

        self.assertEqual("pass", summary["log_path_quality_status"])
        self.assertEqual(1.0, summary["log_path_recall"])
        self.assertEqual(1.0, summary["log_path_precision"])


def compact_context(logs: list[dict]) -> dict:
    return {
        "schema_version": "agent-context-compact/v1",
        "query_handoff": {
            "code_anchors": [],
            "log_anchors": logs,
            "path_context": {"path_candidates": []},
        },
        "output_budget": {"estimated_tokens": 200},
    }


def log_anchor(evidence_class: str, locations: list[str], truncated: bool = False) -> dict:
    return {
        "file_path": locations[0].split("#", 1)[0],
        "function": locations[0].split("#", 1)[1],
        "message_template": "profile load failed",
        "evidence_class": evidence_class,
        "call_path_locations": locations,
        "truncated": truncated,
    }


def path_spec(evidence_class: str, locations: list[str]) -> dict:
    return {"evidence_class": evidence_class, "locations": locations}


def log_candidate(evidence_class: str, locations: list[str], truncated: bool = False) -> dict:
    return {
        "file_path": locations[0].split("#", 1)[0],
        "function": locations[0].split("#", 1)[1],
        "evidence_class": evidence_class,
        "locations": locations,
        "truncated": truncated,
    }


def capability_case(requirements: dict) -> dict:
    return {
        "id": "wrapped-log",
        "task_type": "diagnosis",
        "task": {"description": "profile load failed"},
        "oracle": {
            "expected_files": [],
            "forbidden_files": [],
            "context_requirements": {
                "require_expected_anchors": False,
                **requirements,
            },
        },
    }


def observation(
    paths: list[dict], evidence_classes: list[str] | None = None,
) -> dict:
    return {
        "schema_version": "agent-context-capability-observation/v1",
        "case_id": "wrapped-log",
        "context_schema_version": "agent-context-compact/v1",
        "anchor_paths": [],
        "ordered_anchor_paths": [],
        "primary_anchor_paths": [],
        "candidate_anchor_paths": [],
        "excerpt_paths": [],
        "excerpt_spans": [],
        "log_anchor_paths": [],
        "log_anchor_count": len(paths),
        "log_keywords": [],
        "log_evidence_texts": [],
        "log_evidence_classes": evidence_classes or [
            str(item["evidence_class"]) for item in paths
        ],
        "log_path_candidates": paths,
        "wrapped_log_path_count": len(paths),
        "truncated_log_path_count": sum(bool(item.get("truncated")) for item in paths),
        "experience_types": [],
        "main_experience_texts": [],
        "guard_experience_texts": [],
        "semantic_ref_count": 0,
        "path_files": [],
        "path_relations": [],
        "path_candidate_count": 0,
        "relation_hint_count": 0,
        "evidence_gaps": [],
        "context_token_estimate": 200,
        "memory_prepare_ms": 1,
        "query_elapsed_ms": 1,
    }


if __name__ == "__main__":
    unittest.main()
