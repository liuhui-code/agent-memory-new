# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_language import (
    excluded_result_roles,
    positive_retrieval_query,
)


class QueryLanguageTests(unittest.TestCase):
    def test_chinese_result_exclusion_is_not_positive_retrieval_evidence(self) -> None:
        query = "返回 LIKE 参数和 products 页面，不要返回 ProductRecord。"

        self.assertEqual(
            "返回 LIKE 参数和 products 页面， product",
            positive_retrieval_query(query),
        )

    def test_english_result_exclusion_can_name_multiple_candidates(self) -> None:
        query = "Locate the divider; do not return InventoryRecord or InventoryItem."

        self.assertEqual(
            "Locate the divider; inventory",
            positive_retrieval_query(query),
        )

    def test_behavioral_negative_statement_is_preserved(self) -> None:
        query = "Search should not block rendering without network access."

        self.assertEqual(query, positive_retrieval_query(query))

    def test_example_role_is_extracted_from_result_exclusion(self) -> None:
        self.assertEqual(
            {"sample"},
            excluded_result_roles("Return ownership; exclude sample code."),
        )

    def test_comparison_clause_does_not_drive_target_retrieval(self) -> None:
        query = "The editor arrow is wrong, unlike the creator page. Locate editor binding."
        self.assertEqual(
            "The editor arrow is wrong, Locate editor binding. editor",
            positive_retrieval_query(query),
        )

    def test_instead_of_clause_remains_problem_evidence(self) -> None:
        query = "Restore starts creation instead of opening the picker. Locate command binding."
        self.assertEqual(query, positive_retrieval_query(query))

    def test_plain_not_clause_after_target_is_result_context(self) -> None:
        query = "Locate the command owner, not transfer infrastructure or row views."
        self.assertEqual("Locate the command owner", positive_retrieval_query(query))

    def test_omit_clause_is_not_positive_path_evidence(self) -> None:
        query = "Return the page handler; omit service and repository neighbors."

        self.assertEqual(
            "Return the page handler;",
            positive_retrieval_query(query),
        )

    def test_target_screen_role_bridges_to_code_identifier(self) -> None:
        self.assertEqual(
            "Locate the existing-rule editing screen owner. editor",
            positive_retrieval_query("Locate the existing-rule editing screen owner."),
        )
        self.assertEqual(
            "定位规则编辑页的状态绑定。 editor",
            positive_retrieval_query("定位规则编辑页的状态绑定。"),
        )


if __name__ == "__main__":
    unittest.main()
