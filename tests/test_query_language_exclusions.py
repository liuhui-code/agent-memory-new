# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_language import excluded_code_candidate


class QueryLanguageExclusionTests(unittest.TestCase):
    def test_role_constraint_filters_card_and_model_candidates(self) -> None:
        query = "Return the reusable list Builder rather than a card or data model."

        self.assertTrue(excluded_code_candidate(
            query, {"file_path": "src/widgets/WorkCard.ets"},
        ))
        self.assertTrue(excluded_code_candidate(
            query, {"file_path": "src/viewmodels/GalleryListViewModel.ets"},
        ))
        self.assertFalse(excluded_code_candidate(
            query, {"file_path": "src/views/WorkGalleryPage.ets"},
        ))

    def test_named_constraint_does_not_remove_shared_prefix_owner(self) -> None:
        query = "Locate the view, not the ArticleRecord entity."

        self.assertTrue(excluded_code_candidate(
            query, {"file_path": "src/entities/ArticleRecord.ets"},
        ))
        self.assertFalse(excluded_code_candidate(
            query, {"file_path": "src/views/ArticleMarkupView.ets"},
        ))


if __name__ == "__main__":
    unittest.main()
