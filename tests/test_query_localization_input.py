# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.agent_memory_runtime.query_results import localization_input


class QueryLocalizationInputTests(unittest.TestCase):
    def test_reuses_main_matches_without_an_exclusion(self) -> None:
        matches = {"wiki_matches": [{"id": 1}]}

        with patch(
            "tools.agent_memory_runtime.query_results.collect_matches_with_audit",
        ) as collect:
            selected, direct_scores_safe = localization_input(
                SimpleNamespace(), "locate the render owner", matches, False,
            )

        self.assertIs(matches, selected)
        self.assertFalse(direct_scores_safe)
        collect.assert_not_called()

    @patch("tools.agent_memory_runtime.query_results.gate_matches_by_intent")
    @patch("tools.agent_memory_runtime.query_results.collect_matches_with_audit")
    def test_retrieves_positive_query_for_exclusion_localization(
        self, collect: object, gate: object,
    ) -> None:
        positive_matches = {"wiki_matches": [
            {"id": 2, "file_path": "src/views/ArticleMarkupView.ets"},
            {"id": 3, "file_path": "src/entities/ArticleRecord.ets"},
        ]}
        filtered_matches = {"wiki_matches": [positive_matches["wiki_matches"][0]]}
        collect.return_value = SimpleNamespace(matches=positive_matches)
        gate.return_value = {"matches": filtered_matches}

        original = "locate the view rather than the ArticleRecord entity"
        selected, direct_scores_safe = localization_input(
            SimpleNamespace(),
            original,
            {"wiki_matches": [{"id": 1}]},
            True,
        )

        self.assertIs(filtered_matches, selected)
        self.assertTrue(direct_scores_safe)
        collect.assert_called_once_with(
            unittest.mock.ANY, "locate the view article", enable_passage_shadow=True,
        )
        gate.assert_called_once_with(unittest.mock.ANY, original, filtered_matches)


if __name__ == "__main__":
    unittest.main()
