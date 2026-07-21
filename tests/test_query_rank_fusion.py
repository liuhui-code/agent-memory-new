# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_rank_fusion import ReciprocalRankFusion


class QueryRankFusionTests(unittest.TestCase):
    def test_independent_channel_support_outranks_single_channel_hits(self) -> None:
        fusion = ReciprocalRankFusion(rank_constant=60)

        result = fusion.fuse({
            "lexical": [10, 20, 30],
            "structural": [20, 40],
            "passage": [50, 20],
        }, limit=5)

        self.assertEqual(20, result.candidates[0].record_id)
        self.assertEqual(
            {"lexical", "structural", "passage"},
            {item.channel for item in result.candidates[0].contributions},
        )

    def test_channel_weights_keep_weak_fallback_from_crowding_primary_recall(self) -> None:
        fusion = ReciprocalRankFusion(
            rank_constant=60,
            channel_weights={"identity": 1.2, "method": 0.5},
        )

        result = fusion.fuse({
            "identity": [1, 2],
            "method": [3, 4, 5],
        }, limit=2)

        self.assertEqual([1, 2], [item.record_id for item in result.candidates])

    def test_prefix_weights_apply_to_dynamic_channel_names(self) -> None:
        fusion = ReciprocalRankFusion(
            channel_weights={"term_fts": 1.3, "broad_fts": 1.0},
        )

        result = fusion.fuse({
            "broad_fts": [1, 2],
            "term_fts:1": [3, 4],
        }, limit=2)

        self.assertEqual([3, 4], [item.record_id for item in result.candidates])

    def test_ties_are_deterministic_and_expose_bounded_audit(self) -> None:
        fusion = ReciprocalRankFusion(rank_constant=60)
        rankings = {"first": [8], "second": [9]}

        first = fusion.fuse(rankings, limit=1)
        second = fusion.fuse(rankings, limit=1)

        self.assertEqual([8], [item.record_id for item in first.candidates])
        self.assertEqual(first, second)
        self.assertEqual("reciprocal_rank_fusion/v1", first.provider)
        self.assertEqual({"first": 1, "second": 1}, first.channel_counts)
        self.assertEqual(1, len(first.candidates))


if __name__ == "__main__":
    unittest.main()
