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

    def test_chinese_page_constraint_filters_page_not_component(self) -> None:
        query = "定位复用组件的间距源码，不要返回列表页和详情页。"

        self.assertTrue(excluded_code_candidate(
            query, {"file_path": "src/pages/NotificationDetailsPage.ets"},
        ))
        self.assertFalse(excluded_code_candidate(
            query, {"file_path": "src/widgets/NotificationRow.ets"},
        ))

    def test_chinese_service_constraint_filters_service_not_store(self) -> None:
        query = "定位状态仓的提交所有者，不要返回服务或适配器。"

        self.assertTrue(excluded_code_candidate(
            query, {"file_path": "src/services/ProfileService.ets"},
        ))
        self.assertFalse(excluded_code_candidate(
            query, {"file_path": "src/stores/ProfileStore.ets"},
        ))


if __name__ == "__main__":
    unittest.main()
