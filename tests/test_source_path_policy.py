# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_code_selection import diverse_code_matches
from tools.agent_memory_runtime.source_path_policy import (
    filter_explicit_language_candidates,
    filter_generated_candidates,
    is_generated_source_path,
)


def candidate(path: str, score: float) -> dict[str, object]:
    return {
        "file_path": path,
        "score": score,
        "match_reasons": ["exact_path_segment"],
    }


class SourcePathPolicyTests(unittest.TestCase):
    def test_known_generated_directories_are_classified(self) -> None:
        self.assertTrue(is_generated_source_path(".preview/cache/src/Page.ets"))
        self.assertTrue(is_generated_source_path("module/generated/Api.ts"))
        self.assertFalse(is_generated_source_path("src/pages/GeneratedReportPage.ets"))

    def test_canonical_candidate_replaces_higher_scored_generated_copy(self) -> None:
        generated = candidate(".preview/cache/src/Page.ets", 80.0)
        canonical = candidate("src/pages/Page.ets", 40.0)

        self.assertEqual(
            [canonical],
            filter_generated_candidates([generated, canonical]),
        )

    def test_generated_candidate_remains_as_bounded_fallback(self) -> None:
        generated = candidate("generated/client/Api.ts", 20.0)

        self.assertEqual([generated], filter_generated_candidates([generated]))

    def test_explicit_language_keeps_matching_runtime_implementation(self) -> None:
        python = candidate("tools/export_receipt.py", 80.0)
        arkts = candidate("src/ReceiptExporter.ets", 30.0)

        selected = diverse_code_matches(
            [python, arkts],
            3,
            query="Return the ArkTS implementation, not Python.",
        )

        self.assertEqual([arkts], selected)

    def test_ambiguous_language_query_preserves_candidates(self) -> None:
        python = candidate("tools/export_receipt.py", 80.0)
        arkts = candidate("src/ReceiptExporter.ets", 30.0)

        self.assertEqual(
            [python, arkts],
            filter_explicit_language_candidates(
                [python, arkts], "Compare ArkTS with Python"
            ),
        )



if __name__ == "__main__":
    unittest.main()
