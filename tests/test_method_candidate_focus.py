# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_code_focus import focus_code_candidates


def candidate(path: str, score: float, coverage: int = 0) -> dict[str, object]:
    reasons = ["multi_term_method_evidence"] if coverage >= 3 else []
    return {
        "file_path": path,
        "score": score,
        "method_evidence_coverage": coverage,
        "match_reasons": reasons,
    }


def exact_candidate(path: str, score: float) -> dict[str, object]:
    item = candidate(path, score)
    item["match_reasons"] = ["exact_symbol"]
    return item


def structural_candidate(path: str, score: float) -> dict[str, object]:
    item = candidate(path, score)
    item["match_reasons"] = ["structural_behavior"]
    return item


def path_candidate(path: str, score: float) -> dict[str, object]:
    item = candidate(path, score)
    item["match_reasons"] = ["exact_path_segment"]
    return item


def explicit_method_candidate(path: str, score: float) -> dict[str, object]:
    item = candidate(path, score, 2)
    item["match_reasons"] = ["exact_path_segment"]
    item["recall_lanes"] = ["method_body_fts"]
    return item


class MethodCandidateFocusTests(unittest.TestCase):
    def test_strong_method_evidence_suppresses_unrelated_path_identity_noise(self) -> None:
        owner = candidate("src/runtime/LeaseController.ets", 36.0, 3)
        noise = candidate("src/models/InteractionState.ets", 40.0)

        focused, activated = focus_code_candidates([noise, owner], "cleanup failure")

        self.assertTrue(activated)
        self.assertEqual([owner], focused)

    def test_two_term_method_evidence_does_not_override_normal_ranking(self) -> None:
        weak = candidate("src/runtime/WeakOwner.ets", 36.0, 2)
        normal = candidate("src/models/InteractionState.ets", 40.0)

        focused, activated = focus_code_candidates([normal, weak], "state source")

        self.assertFalse(activated)
        self.assertEqual([normal, weak], focused)

    def test_high_scoring_exact_owner_preserves_multi_owner_selection(self) -> None:
        method = candidate("src/pages/SearchPage.ets", 40.0, 3)
        exact = exact_candidate("src/services/SearchService.ets", 45.0)

        focused, activated = focus_code_candidates([exact, method], "search owner")

        self.assertFalse(activated)
        self.assertEqual([exact, method], focused)

    def test_high_scoring_structural_owner_is_not_replaced_by_method_noise(self) -> None:
        method = candidate("src/components/Preview.ets", 28.0, 3)
        structural = structural_candidate("src/sharing/Collector.ets", 44.0)

        focused, activated = focus_code_candidates([structural, method], "combine records")

        self.assertFalse(activated)
        self.assertEqual([structural, method], focused)

    def test_weak_structural_fallback_does_not_hide_direct_method_evidence(self) -> None:
        method = candidate("src/pools/ThumbnailPool.ets", 3.5, 3)
        structural = structural_candidate("src/cache/GenericCache.ets", 4.0)

        focused, activated = focus_code_candidates([structural, method], "删除 key")

        self.assertTrue(activated)
        self.assertEqual([method], focused)

    def test_target_path_segment_competes_with_context_method_evidence(self) -> None:
        context = candidate("src/pages/RuleCreatorPage.ets", 40.0, 3)
        target = path_candidate("src/pages/RuleEditorPage.ets", 38.0)

        focused, activated = focus_code_candidates([context, target], "editor state")

        self.assertFalse(activated)
        self.assertEqual([context, target], focused)

    def test_generic_path_segment_does_not_block_method_evidence(self) -> None:
        method = candidate("src/coordinators/SourceSwapCoordinator.ets", 36.0, 3)
        noise = path_candidate("src/models/InteractionState.ets", 40.0)

        focused, activated = focus_code_candidates([noise, method], "state owner")

        self.assertTrue(activated)
        self.assertEqual([method], focused)

    def test_dominant_explicit_member_identity_can_focus_two_term_method(self) -> None:
        owner = explicit_method_candidate(
            "src/coordinators/SourceSwapCoordinator.ets", 36.0
        )
        noise = candidate("src/network/NetworkClient.ets", 16.0)

        focused, activated = focus_code_candidates(
            [owner, noise], "reset phase then call openSource"
        )

        self.assertTrue(activated)
        self.assertEqual([owner], focused)

    def test_explicit_member_identity_requires_score_dominance(self) -> None:
        owner = explicit_method_candidate("src/coordinators/Owner.ets", 30.0)
        competitor = candidate("src/services/Competitor.ets", 20.0)

        focused, activated = focus_code_candidates(
            [owner, competitor], "reset phase then call openSource"
        )

        self.assertFalse(activated)
        self.assertEqual([owner, competitor], focused)


if __name__ == "__main__":
    unittest.main()
