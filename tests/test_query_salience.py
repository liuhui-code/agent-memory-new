# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_salience_score import apply_salience_score
from tools.agent_memory_runtime.query_code_selection import (
    preserve_salient_evidence_candidates,
)


class QuerySalienceTests(unittest.TestCase):
    def test_lane_score_uses_bounded_prefix_coverage(self) -> None:
        score, reasons, coverage = apply_salience_score(
            ["exec", "failed", "errno", "permission", "denied", "bash"],
            "execl data app bin bash",
            2.0,
            [],
            True,
        )

        self.assertEqual(2, coverage)
        self.assertEqual(10.0, score)
        self.assertEqual(["salient_query_evidence"], reasons)

    def test_non_salient_lane_cannot_receive_bonus(self) -> None:
        self.assertEqual(
            (2.0, [], 0),
            apply_salience_score(["bash"], "bash", 2.0, [], False),
        )

    def test_serving_lane_preserves_bounded_file_diversity(self) -> None:
        focused = [{"file_path": "ui/Entry.ets", "match_reasons": []}]
        recalled = [
            *focused,
            {"file_path": "native/terminal.cpp", "match_reasons": ["salient_query_evidence"]},
            {"file_path": "build/Makefile", "match_reasons": ["salient_query_evidence"]},
            {"file_path": "other/noise.txt", "match_reasons": ["salient_query_evidence"]},
        ]

        selected = preserve_salient_evidence_candidates(focused, recalled)

        self.assertEqual(
            ["ui/Entry.ets", "native/terminal.cpp", "build/Makefile"],
            [item["file_path"] for item in selected],
        )


if __name__ == "__main__":
    unittest.main()
