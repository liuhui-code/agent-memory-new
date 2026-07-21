# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_caller_ownership import (
    caller_owner_query,
    indirect_seed_scores,
)
from tools.agent_memory_runtime.query_code_focus import focus_code_candidates


class QueryCallerOwnershipTests(unittest.TestCase):
    def test_caller_intent_and_indirect_seed_are_bounded(self) -> None:
        self.assertTrue(caller_owner_query("return the actual caller context"))
        self.assertTrue(caller_owner_query("定位 onClick 调用方"))
        self.assertFalse(caller_owner_query("show controller implementation"))
        items = [
            {"file_path": "src/dialogs/CloseAdapter.ets", "score": 20.0},
            {"file_path": "src/pages/OwnerPage.ets", "score": 30.0},
        ]
        self.assertEqual(
            {"src/dialogs/CloseAdapter.ets": 20.0},
            indirect_seed_scores(items),
        )

    def test_caller_owner_focuses_before_lexical_helper(self) -> None:
        caller = {
            "file_path": "src/pages/OwnerPage.ets",
            "score": 20.0,
            "match_reasons": ["graph_neighbor", "caller_owner"],
        }
        helper = {
            "file_path": "src/dialogs/CloseAdapter.ets",
            "score": 40.0,
            "match_reasons": ["exact_path_segment"],
        }
        focused, activated = focus_code_candidates(
            [helper, caller], "return the actual caller context"
        )
        self.assertTrue(activated)
        self.assertEqual([caller], focused)


if __name__ == "__main__":
    unittest.main()
