# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_capability import summarize_context
from tools.agent_memory_runtime.context_capability_eval import evaluate_context_capability
from tools.agent_memory_runtime.query_callable_evidence_set import (
    build_callable_evidence_set,
)
from tools.agent_memory_runtime.context_evidence_set_metrics import (
    assess_evidence_set,
    evidence_set_profile,
)


class CallableEvidenceSetTests(unittest.TestCase):
    def test_explicit_single_target_with_typed_support_is_supported(self) -> None:
        result = build_callable_evidence_set(
            "Return the coordinator that restores the saved draft.",
            localization([
                candidate("src/DraftCoordinator.ets", "restore", "coordinator", target=True),
                candidate("src/DraftStore.ets", "load", "store"),
            ]),
            evidence("src/DraftCoordinator.ets", "restore"),
        )

        self.assertEqual("single", result["target_scope"]["kind"])
        self.assertEqual("single_candidate_supported", result["calibration"]["state"])
        self.assertIn("typed_target_owner", result["members"][0]["support_kinds"])

    def test_multi_target_query_requires_portfolio(self) -> None:
        result = build_callable_evidence_set(
            "Return both the row component and preview component typography sources.",
            localization([
                candidate("src/MessageRow.ets", "build", "component"),
                candidate("src/QuotedPreview.ets", "build", "component"),
            ]),
            evidence("src/MessageRow.ets", "build"),
        )

        self.assertEqual("multiple", result["target_scope"]["kind"])
        self.assertEqual("portfolio_required", result["calibration"]["state"])
        self.assertTrue(result["competition"]["same_owner_kind_alternative"])

    def test_graph_backed_alternative_keeps_competing_support_visible(self) -> None:
        graph_owner = candidate("src/Caller.ets", "onClick", "component")
        graph_owner.update({"graph_depth": 1, "graph_relations": ["calls"]})

        result = build_callable_evidence_set(
            "Locate the click owner for confirmation.",
            localization([
                candidate("src/DialogController.ets", "confirm", "controller"),
                graph_owner,
            ]),
            evidence("src/DialogController.ets", "confirm"),
        )

        self.assertTrue(result["competition"]["graph_backed_alternative"])
        self.assertEqual("portfolio_required", result["calibration"]["state"])

    def test_excluded_primary_is_conflicted(self) -> None:
        result = build_callable_evidence_set(
            "Return the production pool implementation, not the example class.",
            localization([
                candidate("src/examples/PoolExample.ets", "trim", "class"),
                candidate("src/pools/Pool.ets", "trim", "class"),
            ]),
            evidence("src/examples/PoolExample.ets", "trim"),
        )

        self.assertEqual("conflicted", result["calibration"]["state"])
        self.assertEqual(1, result["competition"]["excluded_member_count"])
        self.assertTrue(result["members"][0]["excluded_by_query"])

    def test_method_symbol_exclusion_is_guarded(self) -> None:
        result = build_callable_evidence_set(
            "Return the production policy; exclude showQuotaExample.",
            localization([
                candidate("src/ProductionPolicy.ets", "enforceQuota", "policy", True),
                candidate("src/ExamplePolicy.ets", "showQuotaExample", "policy"),
            ]),
            evidence("src/ProductionPolicy.ets", "enforceQuota"),
        )

        self.assertTrue(result["members"][1]["excluded_by_query"])

    def test_members_are_bounded_and_missing_evidence_is_insufficient(self) -> None:
        many = [
            candidate(f"src/Owner{index}.ets", f"run{index}", "class")
            for index in range(8)
        ]
        bounded = build_callable_evidence_set(
            "Locate the owner.", localization(many), evidence("src/Owner0.ets", "run0")
        )
        missing = build_callable_evidence_set("Locate the owner.", {}, {})

        self.assertEqual(3, len(bounded["members"]))
        self.assertEqual("insufficient", missing["calibration"]["state"])
        self.assertFalse(missing["serving_projection_changed"])

    def test_locatable_candidate_without_substantive_support_is_insufficient(self) -> None:
        weak = candidate("src/Incidental.ets", "render", "component")
        weak["reasons"] = []
        result = build_callable_evidence_set(
            "Find evidence for UNKNOWN_NONCE_77.",
            localization([weak]),
            evidence("src/Incidental.ets", "render"),
        )

        self.assertEqual("insufficient", result["calibration"]["state"])

    def test_semantic_mechanism_alone_remains_insufficient(self) -> None:
        weak = candidate("src/Incidental.ets", "render", "component")
        weak["reasons"] = ["semantic_mechanism"]
        result = build_callable_evidence_set(
            "Find evidence for UNKNOWN_NONCE_88.",
            localization([weak]),
            evidence("src/Incidental.ets", "render"),
        )

        self.assertEqual("insufficient", result["calibration"]["state"])

    def test_single_scope_accepts_determiner_plus_single_and_return_only(self) -> None:
        first = build_callable_evidence_set(
            "Return the single coordinator for rotation.", {}, {},
        )
        second = build_callable_evidence_set(
            "Return only the production policy, not the demo.", {}, {},
        )

        self.assertEqual("single", first["target_scope"]["kind"])
        self.assertEqual("single", second["target_scope"]["kind"])


class CallableEvidenceSetIntegrationTests(AgentMemoryTestBase):
    def test_full_context_audits_shadow_set_without_expanding_compact_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "evidence-set-project"
            root.mkdir()
            source = root / "src" / "DraftCoordinator.ets"
            source.parent.mkdir()
            source.write_text(
                "export class DraftCoordinator {\n"
                "  restoreDraft(): void { this.currentDraft = DraftStore.load() }\n"
                "}\n",
                encoding="utf-8",
            )
            self.run_memory(root, "init")
            self.run_memory(root, "learn-path", "--path", ".", "--json")

            full = json.loads(self.run_memory(
                root,
                "context",
                "--query",
                "Return the coordinator that restores the saved draft.",
                "--json",
            ).stdout)
            compact = json.loads(self.run_memory(
                root,
                "context",
                "--query",
                "Return the coordinator that restores the saved draft.",
                "--compact",
                "--json",
            ).stdout)

        audit = full["query_audit"]["callable_evidence_set"]
        self.assertEqual("shadow", audit["mode"])
        self.assertFalse(audit["serving_projection_changed"])
        self.assertNotIn("query_audit", compact)
        self.assertNotIn("callable_evidence_set", compact["query_handoff"])
        observation = summarize_context(
            "shadow-set", compact, 1, 1, audit_context=full, audit_ms=1,
        )
        result = evaluate_context_capability(
            [{
                "id": "shadow-set",
                "task_type": "diagnosis",
                "task": {"description": "Restore draft"},
                "oracle": {
                    "expected_files": ["src/DraftCoordinator.ets"],
                    "forbidden_files": [],
                    "context_requirements": {},
                },
            }],
            [observation],
        )

        self.assertEqual("shadow", observation["callable_evidence_set"]["mode"])
        profile = result["capability_profile"]["evidence_set_calibration"]
        self.assertEqual("informational", profile["status"])
        self.assertFalse(profile["serving_projection_changed"])


class CallableEvidenceSetMetricsTests(unittest.TestCase):
    def test_assessment_scores_shadow_scope_and_members_without_gate_checks(self) -> None:
        measured = assess_evidence_set(
            {"src/Row.ets", "src/Preview.ets"},
            {
                "callable_evidence_set": {
                    "mode": "shadow",
                    "target_scope": {"kind": "multiple"},
                    "members": [
                        {"file_path": "src/Row.ets"},
                        {"file_path": "src/Preview.ets"},
                    ],
                    "calibration": {"state": "portfolio_required"},
                }
            },
        )

        self.assertTrue(measured["target_scope_match"])
        self.assertEqual(1.0, measured["member_recall"])
        self.assertEqual("portfolio_required", measured["calibration_state"])
        self.assertNotIn("checks", measured)

    def test_profile_is_informational(self) -> None:
        profile = evidence_set_profile([
            {"evidence_set": {
                "observed": True,
                "target_scope_match": True,
                "member_recall": 1.0,
                "primary_precision": 1.0,
                "calibration_state": "single_candidate_supported",
            }},
            {"evidence_set": {
                "observed": True,
                "target_scope_match": False,
                "member_recall": 0.5,
                "primary_precision": 0.0,
                "calibration_state": "unresolved",
            }},
        ])

        self.assertEqual("informational", profile["status"])
        self.assertEqual(0.5, profile["target_scope_accuracy"])
        self.assertEqual(0.75, profile["member_recall"])

    def test_explicit_oracle_scores_state_and_forbidden_members(self) -> None:
        measured = assess_evidence_set(
            {"src/Unavailable.ets"},
            {
                "callable_evidence_set": {
                    "mode": "shadow",
                    "target_scope": {"kind": "unknown"},
                    "members": [{"file_path": "src/Noise.ets"}],
                    "calibration": {"state": "insufficient"},
                }
            },
            {
                "target_scope": "unknown",
                "expected_member_files": ["src/Unavailable.ets"],
                "expected_primary_files": ["src/Unavailable.ets"],
                "forbidden_member_files": ["src/Noise.ets"],
                "allowed_states": ["insufficient"],
            },
        )

        self.assertTrue(measured["target_scope_match"])
        self.assertTrue(measured["calibration_state_match"])
        self.assertEqual(["src/Noise.ets"], measured["forbidden_member_hits"])

    def test_excluded_member_is_a_guard_not_an_active_forbidden_hit(self) -> None:
        measured = assess_evidence_set(
            {"src/Production.ets"},
            {"callable_evidence_set": {
                "mode": "shadow",
                "target_scope": {"kind": "single"},
                "members": [
                    {"file_path": "src/Production.ets"},
                    {"file_path": "src/Demo.ets", "excluded_by_query": True},
                ],
                "calibration": {"state": "single_candidate_supported"},
            }},
            {"forbidden_member_files": ["src/Demo.ets"]},
        )

        self.assertEqual([], measured["forbidden_member_hits"])
        self.assertEqual(1, measured["guarded_exclusion_count"])


def localization(candidates: list[dict[str, object]]) -> dict[str, object]:
    return {
        "callable_candidates": candidates,
        "source_ranges": [
            {
                "file_path": item["file_path"],
                "symbol": item["symbol"],
                "start_line": 3,
                "end_line": 8,
            }
            for item in candidates
        ],
    }


def candidate(
    path: str, symbol: str, owner_kind: str, target: bool = False,
) -> dict[str, object]:
    return {
        "file_path": path,
        "symbol": symbol,
        "owner_name": path.rsplit("/", 1)[-1].split(".", 1)[0],
        "owner_kind": owner_kind,
        "score": 12.0,
        "evidence_score": 8.0,
        "reasons": ["source_locatable"],
        "graph_depth": 0,
        "graph_relations": [],
        **({"target_owner_kind_match": True} if target else {}),
    }


def evidence(path: str, symbol: str) -> dict[str, object]:
    return {
        "certainty": "bounded",
        "primary": {"file_path": path, "symbol": symbol},
        "alternatives": [],
    }


if __name__ == "__main__":
    unittest.main()
