# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.context_capability import summarize_context
from tools.agent_memory_runtime.context_hierarchical_metrics import (
    assess_hierarchical_localization,
    localization_profile,
)


class ContextHierarchicalMetricsTests(unittest.TestCase):
    def test_keeps_file_callable_owner_and_range_separate(self) -> None:
        observation = {
            "hierarchical_schema_version": "agent-hierarchical-localization/v1",
            "hierarchical_file_paths": ["src/services/SnapshotService.ets"],
            "hierarchical_callable_refs": [{
                "file_path": "src/services/SnapshotService.ets",
                "symbol": "restoreSnapshot", "start_line": 4, "end_line": 16,
            }],
            "hierarchical_owner_refs": [{
                "file_path": "src/pages/SnapshotPage.ets",
                "symbol": "refreshSnapshot", "start_line": 7, "end_line": 9,
                "graph_depth": 1,
            }],
            "hierarchical_source_ranges": [{
                "file_path": "src/services/SnapshotService.ets",
                "symbol": "restoreSnapshot", "start_line": 5, "end_line": 9,
            }],
            "hierarchical_audit_elapsed_ms": 18,
        }
        score = assess_hierarchical_localization(
            {"src/services/SnapshotService.ets"},
            {
                "required_source_spans": [{"file_path": "src/Wrong.ets", "symbol": "wrong"}],
                "hierarchical_callable_spans": [{
                    "file_path": "src/services/SnapshotService.ets",
                    "symbol": "restoreSnapshot", "start_line": 5, "end_line": 8,
                }],
                "hierarchical_owner_spans": [{
                    "file_path": "src/pages/SnapshotPage.ets", "symbol": "refreshSnapshot"
                }],
                "hierarchical_range_spans": [{
                    "file_path": "src/services/SnapshotService.ets",
                    "symbol": "restoreSnapshot", "start_line": 5, "end_line": 8,
                }],
            },
            observation,
        )

        self.assertTrue(score["observed"])
        self.assertEqual(1.0, score["file_recall"])
        self.assertEqual(1.0, score["callable_recall"])
        self.assertEqual(1.0, score["owner_recall"])
        self.assertEqual(1.0, score["owner_precision"])
        self.assertEqual(1.0, score["range_recall"])

    def test_missing_audit_is_informational_serving_stage(self) -> None:
        score = assess_hierarchical_localization({"src/Profile.ets"}, {}, {})
        profile = localization_profile([{"hierarchical_localization": score}])

        self.assertFalse(score["observed"])
        self.assertEqual("informational_serving_stage", profile["status"])
        self.assertEqual(0, profile["observed_case_count"])
        self.assertEqual(0, profile["owner_evaluated_case_count"])
        self.assertIsNone(profile["file_recall"])

    def test_summary_uses_full_audit_without_exposing_source_bodies(self) -> None:
        context = {
            "schema_version": "agent-context-compact/v1",
            "query_handoff": {"code_anchors": [], "log_anchors": []},
            "output_budget": {"estimated_tokens": 123},
        }
        audit = {
            "query_audit": {
                "candidate_recall": {"tables": {}},
                "hierarchical_localization": {
                    "schema_version": "agent-hierarchical-localization/v1",
                    "file_candidates": [{"file_path": "src/Service.ets"}],
                    "callable_candidates": [
                        {"file_path": "src/Service.ets", "symbol": "restore"},
                    ],
                    "graph_owner_candidates": [
                        {"file_path": "src/Page.ets", "symbol": "refresh", "graph_depth": 1},
                    ],
                    "source_ranges": [{
                        "file_path": "src/Service.ets", "symbol": "restore",
                        "start_line": 5, "end_line": 8,
                    }],
                },
            },
        }

        observed = summarize_context("case", context, 10, 4, audit, 16)

        self.assertEqual([], observed["candidate_anchor_paths"])
        self.assertEqual(["src/Service.ets"], observed["hierarchical_file_paths"])
        self.assertEqual("refresh", observed["hierarchical_owner_refs"][0]["symbol"])
        self.assertEqual(5, observed["hierarchical_source_ranges"][0]["start_line"])
        self.assertNotIn("content", str(observed))


if __name__ == "__main__":
    unittest.main()
