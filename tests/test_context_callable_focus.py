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

    def test_no_path_does_not_promote_uncertain_primary(self) -> None:
        anchors = [
            {"file_path": "src/Lexical.ets"},
            {"file_path": "src/Other.ets"},
        ]
        evidence = {"certainty": "uncertain", "primary": {
            "file_path": "src/Callable.ets",
            "symbol": "apply",
            "source_range": {"start_line": 8, "end_line": 12},
        }}

        result = focus_callable_anchors(anchors, evidence, False)

        self.assertEqual(anchors, result)

    def test_incomplete_path_reserves_locatable_uncertain_primary(self) -> None:
        anchors = [{"file_path": "src/Emitter.ets"}]
        evidence = {"certainty": "uncertain", "primary": {
            "file_path": "src/Callable.ets",
            "symbol": "apply",
            "source_range": {"start_line": 8, "end_line": 12},
        }}
        path = {
            "activated": True,
            "path_candidates": [{"complete": False, "truncated": False}],
        }

        result = focus_callable_anchors(anchors, evidence, path)

        self.assertEqual(
            ["src/Emitter.ets", "src/Callable.ets"],
            [item["file_path"] for item in result],
        )

    def test_explicit_portfolio_requires_bounded_point_certainty(self) -> None:
        evidence = {
            "certainty": "uncertain",
            "primary": {"file_path": "src/First.ets"},
            "passage_portfolio": {
                "state": "composed",
                "selection_basis": ["explicit_cross_file_targets"],
                "members": [
                    {"file_path": "src/First.ets", "symbol": "first", "source_range": {"start_line": 3, "end_line": 5}},
                    {"file_path": "src/Second.ets", "symbol": "second", "source_range": {"start_line": 7, "end_line": 9}},
                ],
            },
        }

        result = focus_callable_anchors([], evidence, False)

        self.assertEqual([], result)

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

    def test_preferred_artifact_role_can_override_incidental_graph_neighbor(self) -> None:
        anchors = [
            {"file_path": "src/Caller.ets", "graph_neighbor": True},
            {"file_path": "test/LeasePolicy.test.ets"},
        ]
        evidence = {"certainty": "bounded", "primary": {
            "file_path": "src/LeasePolicy.ets",
            "symbol": "resumeLease",
            "source_range": {"start_line": 4, "end_line": 9},
            "reasons": ["exact_symbol", "implementation_artifact_role"],
            "artifact_role": "production",
            "artifact_query_intent": "implementation",
            "artifact_role_competition": True,
            "artifact_role_representative": True,
        }}

        focused = focus_callable_anchors(anchors, evidence, False)

        self.assertEqual(["src/LeasePolicy.ets"], [item["file_path"] for item in focused])

    def test_artifact_role_without_direct_identity_keeps_graph_neighbor(self) -> None:
        anchors = [
            {"file_path": "src/Target.ets"},
            {"file_path": "src/Caller.ets", "graph_neighbor": True},
        ]
        evidence = {"certainty": "bounded", "primary": {
            "file_path": "src/Target.ets",
            "source_range": {"start_line": 4, "end_line": 9},
            "reasons": ["semantic_mechanism", "implementation_artifact_role"],
            "artifact_role": "production",
            "artifact_query_intent": "implementation",
            "artifact_role_competition": True,
            "artifact_role_representative": True,
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

    def test_complete_path_contract_keeps_exclusive_scope(self) -> None:
        anchors = [{"file_path": "src/PathEntry.ets"}]
        evidence = {"certainty": "bounded", "primary": {
            "file_path": "src/Coordinator.ets",
            "source_range": {"start_line": 8, "end_line": 14},
        }}
        path = {
            "activated": True,
            "path_candidates": [{"complete": True, "truncated": False}],
        }

        self.assertEqual(anchors, focus_callable_anchors(anchors, evidence, path))

    def test_wrapped_log_path_keeps_exclusive_scope(self) -> None:
        anchors = [{"file_path": "src/WrappedCaller.ets"}]
        evidence = {"certainty": "uncertain", "primary": {
            "file_path": "src/Noise.ets",
            "source_range": {"start_line": 8, "end_line": 14},
        }}
        path = {
            "activated": True,
            "wrapped_log_evidence": True,
            "path_candidates": [{"complete": False, "truncated": False}],
        }

        self.assertEqual(anchors, focus_callable_anchors(anchors, evidence, path))

    def test_incomplete_path_fuses_explicit_portfolio_before_path_anchor(self) -> None:
        anchors = [{"file_path": "src/Emitter.ets"}]
        evidence = {
            "certainty": "bounded",
            "primary": {"file_path": "src/First.ets"},
            "passage_portfolio": {
                "state": "composed",
                "selection_basis": ["explicit_cross_file_targets"],
                "members": [
                    {"file_path": "src/First.ets", "symbol": "first", "source_range": {"start_line": 3, "end_line": 5}},
                    {"file_path": "src/Second.ets", "symbol": "second", "source_range": {"start_line": 7, "end_line": 9}},
                ],
            },
        }
        path = {
            "activated": True,
            "path_candidates": [{"complete": False, "truncated": False}],
        }

        result = focus_callable_anchors(anchors, evidence, path)

        self.assertEqual(
            ["src/First.ets", "src/Second.ets", "src/Emitter.ets"],
            [item["file_path"] for item in result],
        )


if __name__ == "__main__":
    unittest.main()
