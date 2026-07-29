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

    def test_preserves_graph_neighbors_for_graph_context(self) -> None:
        anchors = [{"file_path": "src/Target.ets"}, {"file_path": "src/Caller.ets", "graph_neighbor": True}]
        evidence = {"certainty": "bounded", "primary": {
            "file_path": "src/Target.ets", "source_range": {"start_line": 4},
        }}

        self.assertEqual(anchors, focus_callable_anchors(anchors, evidence, False))


if __name__ == "__main__":
    unittest.main()
