# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_results import diverse_code_matches


class QueryResultDiversityTests(unittest.TestCase):
    def test_near_duplicate_layers_are_deferred_for_distinct_code_context(self) -> None:
        candidates = [
            code_item("src/viewmodel/Message/MessageDataSource.ets", "MessageDataSource"),
            code_item("src/viewmodel/Chat/ChatDataSource.ets", "ChatDataSource"),
            code_item("src/pages/Chat/ChatDetail.ets", "chatDataSource"),
            code_item("src/views/Chat/ChatDetailBottom.ets", "chatDataSource"),
            code_item("src/views/Message/MessageBubble.ets", "MessageBubble"),
        ]

        selected = diverse_code_matches(candidates, 3)

        self.assertEqual(
            [
                "src/viewmodel/Message/MessageDataSource.ets",
                "src/pages/Chat/ChatDetail.ets",
                "src/views/Message/MessageBubble.ets",
            ],
            [item["file_path"] for item in selected],
        )

    def test_graph_lane_reserves_one_strong_structural_neighbor(self) -> None:
        candidates = [
            code_item("src/viewmodel/MessageDataSource.ets", "MessageDataSource", 60.0),
            code_item("src/viewmodel/ChatDataSource.ets", "ChatDataSource", 58.0),
            code_item("src/pages/ChatDetail.ets", "ChatDetail", 52.0),
            code_item(
                "src/views/MessageBubble.ets",
                "MessageBubble",
                46.0,
                ["graph_neighbor", "graph_relation:routes_to"],
            ),
        ]

        selected = diverse_code_matches(candidates, 3)

        self.assertEqual("src/views/MessageBubble.ets", selected[1]["file_path"])

    def test_explicit_multi_step_paths_are_not_collapsed_or_interrupted(self) -> None:
        candidates = [
            code_item("src/pages/Login/PhoneNumber.ets", "PhoneNumber", 30.0),
            code_item("src/pages/Login/VerifyCode.ets", "VerifyCode", 29.0),
            code_item("src/pages/Login/Password.ets", "Password", 28.0),
            code_item(
                "src/pages/Index.ets",
                "Navigation",
                27.0,
                ["graph_neighbor", "graph_relation:routes_to"],
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            3,
            query="phone verification code and password login steps",
        )

        self.assertEqual(
            [item["file_path"] for item in candidates[:3]],
            [item["file_path"] for item in selected],
        )

    def test_graph_only_noise_does_not_create_compact_code_evidence(self) -> None:
        graph_only = code_item(
            "src/pages/DownloadsPage.ets",
            "DownloadsPage",
            4.0,
            ["graph_neighbor", "graph_relation:imports"],
        )

        self.assertEqual([], diverse_code_matches([graph_only], 5))

    def test_exact_behavior_owner_drops_unproven_graph_neighbors(self) -> None:
        candidates = [
            code_item(
                "src/views/InventoryList.ets",
                "InventoryList",
                44.0,
                ["exact_behavior_operation"],
            ),
            code_item(
                "src/pages/UnrelatedPage.ets",
                "UnrelatedPage",
                30.0,
                ["graph_neighbor", "graph_relation:imports"],
            ),
        ]

        selected = diverse_code_matches(candidates, 5)

        self.assertEqual(["src/views/InventoryList.ets"], [item["file_path"] for item in selected])


def code_item(
    file_path: str,
    symbol: str,
    score: float = 10.0,
    reasons: list[str] | None = None,
) -> dict[str, object]:
    return {
        "file_path": file_path,
        "symbol": symbol,
        "score": score,
        "match_reasons": reasons or [],
    }


if __name__ == "__main__":
    unittest.main()
