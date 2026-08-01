# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors


class ContextCallableFocusTests(unittest.TestCase):
    def test_focuses_only_bounded_callable_evidence_outside_path_queries(self) -> None:
        anchors = [{"file_path": "src/Target.ets"}, {"file_path": "src/Noise.ets"}]
        evidence = {"certainty": "bounded", "primary": {
            "file_path": "src/Target.ets", "source_range": {"start_line": 4},
        }}

        result = focus_callable_anchors(anchors, evidence, path_activated=False)

        self.assertEqual(["src/Target.ets"], [item["file_path"] for item in result])

    def test_preserves_candidates_when_evidence_is_uncertain_or_path_scoped(self) -> None:
        anchors = [{"file_path": "src/Target.ets"}, {"file_path": "src/Noise.ets"}]
        uncertain = {"certainty": "uncertain", "primary": {"file_path": "src/Target.ets"}}

        self.assertEqual(anchors, focus_callable_anchors(anchors, uncertain, False))
        self.assertEqual(anchors, focus_callable_anchors(anchors, uncertain, True))

    def test_bounded_primary_overrides_incidental_graph_neighbor(self) -> None:
        anchors = [{"file_path": "src/Target.ets"}, {"file_path": "src/Caller.ets", "graph_neighbor": True}]
        evidence = {"certainty": "bounded", "primary": {
            "file_path": "src/Target.ets",
            "symbol": "applyTarget",
            "target_owner_kind_match": True,
            "source_range": {"start_line": 4, "end_line": 9},
        }}

        focused = focus_callable_anchors(anchors, evidence, False)

        self.assertEqual(["src/Target.ets"], [item["file_path"] for item in focused])
        self.assertEqual("applyTarget", focused[0]["symbol"])
        self.assertEqual((4, 9), (focused[0]["start_line"], focused[0]["end_line"]))

    def test_preserves_graph_neighbor_without_explicit_target_role_match(self) -> None:
        anchors = [
            {"file_path": "src/Target.ets"},
            {"file_path": "src/Caller.ets", "graph_neighbor": True},
        ]
        evidence = {"certainty": "bounded", "primary": {
            "file_path": "src/Target.ets",
            "source_range": {"start_line": 4, "end_line": 9},
        }}

        self.assertEqual(anchors, focus_callable_anchors(anchors, evidence, False))

    def test_materializes_bounded_primary_missing_from_serving_anchors(self) -> None:
        evidence = {"certainty": "bounded", "primary": {
            "file_path": "src/Coordinator.ets",
            "symbol": "activate",
            "target_owner_kind_match": True,
            "source_range": {"start_line": 8, "end_line": 14},
        }}

        focused = focus_callable_anchors(
            [{"file_path": "src/Unrelated.ets"}], evidence, False,
        )

        self.assertEqual(["src/Coordinator.ets"], [item["file_path"] for item in focused])
        self.assertEqual("callable_evidence", focused[0]["source"])
        self.assertEqual("activate", focused[0]["symbol"])

    def test_activated_path_keeps_exclusive_scope_for_bounded_evidence(self) -> None:
        anchors = [{"file_path": "src/PathEntry.ets"}]
        evidence = {"certainty": "bounded", "primary": {
            "file_path": "src/Coordinator.ets",
            "source_range": {"start_line": 8, "end_line": 14},
        }}

        self.assertEqual(anchors, focus_callable_anchors(anchors, evidence, True))


if __name__ == "__main__":
    unittest.main()
