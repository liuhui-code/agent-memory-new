# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_results import diverse_code_matches
from tools.agent_memory_runtime.query_code_selection import protected_explicit_paths


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

    def test_structural_candidate_with_graph_provenance_remains_direct_evidence(self) -> None:
        candidate = code_item(
            "src/pages/AccountSettingsPage.ets",
            "AccountSettingsPage",
            6.0,
            [
                "structural_behavior",
                "graph_neighbor",
                "graph_relation:imports",
            ],
            "behavior: actiondispatch, validationguard",
        )

        selected = diverse_code_matches(
            [candidate],
            5,
            query="A required field error is shown but the update still submits.",
        )

        self.assertEqual([candidate], selected)

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

    def test_behavior_owner_query_suppresses_data_entity_candidates(self) -> None:
        candidates = [
            code_item("src/entities/ProductRecord.ets", "ProductRecord", 50.0),
            code_item("src/services/ProductSearchService.ets", "search", 45.0),
            code_item("src/pages/ProductSearchPage.ets", "ProductSearchPage", 40.0),
        ]

        selected = diverse_code_matches(
            candidates,
            3,
            query="Locate the SQL parameter owner and page that renders product search results.",
        )

        self.assertEqual(
            [
                "src/services/ProductSearchService.ets",
                "src/pages/ProductSearchPage.ets",
            ],
            [item["file_path"] for item in selected],
        )

    def test_explicit_record_definition_query_keeps_entity_candidate(self) -> None:
        entity = code_item("src/entities/ProductRecord.ets", "ProductRecord", 50.0)

        selected = diverse_code_matches(
            [entity],
            3,
            query="Locate the ProductRecord entity definition and fields.",
        )

        self.assertEqual([entity], selected)

    def test_multiple_named_code_identities_exclude_unnamed_same_role_noise(self) -> None:
        candidates = [
            code_item("src/services/ProductSearchService.ets", "ProductSearchService", 50.0),
            code_item("src/pages/ProductSearchPage.ets", "ProductSearchPage", 45.0),
            code_item("src/services/AttachmentService.ets", "AttachmentService", 40.0),
            code_item("src/services/CacheService.ets", "CacheService", 35.0),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query=(
                "Return ProductSearchService query binding and ProductSearchPage "
                "result consumption for the missing substring match."
            ),
        )

        self.assertEqual(
            [
                "src/services/ProductSearchService.ets",
                "src/pages/ProductSearchPage.ets",
            ],
            [item["file_path"] for item in selected],
        )

    def test_two_explicit_natural_path_identities_survive_similarity_filter(self) -> None:
        candidates = [
            code_item(
                "src/views/QuotedMessagePreview.ets", "text", 70.0
            ),
            code_item(
                "src/views/MessageRow.ets", "quotedText", 56.0
            ),
            code_item("src/views/InventoryList.ets", "rows", 32.5),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query=(
                "Message rows and quoted-message previews render inconsistent "
                "text sizes. Return both UI source contexts."
            ),
        )

        self.assertEqual(
            [
                "src/views/QuotedMessagePreview.ets",
                "src/views/MessageRow.ets",
                "src/views/InventoryList.ets",
            ],
            [item["file_path"] for item in selected],
        )

    def test_semantic_expansion_does_not_create_explicit_path_identity(self) -> None:
        candidates = [
            code_item("src/pages/AccountSettingsPage.ets", "build", 42.0),
            code_item("src/pages/ProfilePage.ets", "build", 40.0),
            code_item("src/services/ProfileService.ets", "loadProfile", 38.0),
        ]

        paths = protected_explicit_paths(
            candidates,
            "文件夹中的嵌套资源加载后列表仍为空，请定位数据查询和状态提交源码。",
        )

        self.assertEqual(set(), paths)

    def test_negative_named_paths_do_not_activate_explicit_protection(self) -> None:
        candidates = [
            code_item("src/entities/InventoryRecord.ets", "InventoryRecord", 42.0),
            code_item("src/views/InventoryItem.ets", "InventoryItem", 40.0),
        ]

        paths = protected_explicit_paths(
            candidates,
            "Locate the inventory divider; do not return InventoryRecord or InventoryItem.",
        )

        self.assertEqual(set(), paths)

    def test_dominant_single_shared_owner_suppresses_weak_context(self) -> None:
        candidates = [
            code_item(
                "src/views/ArticleMarkupView.ets",
                "ArticleMarkupView",
                80.0,
                ["query_focus_coverage", "multi_concept_coverage"],
            ),
            code_item("src/pages/ArticleDetail.ets", "ArticleDetail", 42.0),
            code_item("src/views/ArticleReply.ets", "ArticleReply", 38.0),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query=(
                "Formatted article links, code, quotes and underline have unreadable "
                "dark-theme colors. Locate the shared rich-text rendering owner."
            ),
        )

        self.assertEqual(
            ["src/views/ArticleMarkupView.ets"],
            [item["file_path"] for item in selected],
        )

    def test_structural_owner_drops_lexical_noise_and_weaker_marker_matches(self) -> None:
        candidates = [
            code_item(
                "src/views/InventoryOverlayPanel.ets",
                "InventoryOverlayPanel",
                22.0,
                ["structural_behavior"],
                "operations: backgroundColor, shadow",
            ),
            code_item(
                "src/views/InventoryItem.ets",
                "InventoryItem",
                30.0,
                ["structural_behavior"],
                "operations: backgroundColor",
            ),
            code_item("src/entities/InventoryRecord.ets", "InventoryRecord", 40.0),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="The inventory category chooser overlaps the numeric controls.",
        )

        self.assertEqual(
            ["src/views/InventoryOverlayPanel.ets"],
            [item["file_path"] for item in selected],
        )

    def test_structural_owner_beats_higher_scored_non_structural_noise(self) -> None:
        candidates = [
            code_item("src/network/NetworkClient.ets", "NetworkClient", 44.0),
            code_item("src/pages/DownloadsPage.ets", "DownloadsPage", 38.0),
            code_item(
                "src/pages/QuarterLedger.ets",
                "QuarterLedger",
                12.0,
                ["structural_behavior"],
                "operations: forEach",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="Changing the quarter leaves financial totals unchanged.",
        )

        self.assertEqual(
            ["src/pages/QuarterLedger.ets"],
            [item["file_path"] for item in selected],
        )

    def test_structural_focus_keeps_minimal_complementary_owner_cover(self) -> None:
        candidates = [
            code_item(
                "src/state/DeviceSyncStore.ets",
                "DeviceSyncStore",
                34.0,
                ["structural_behavior"],
                "behavior: lifecyclesync, repositoryboundary, statewrite",
            ),
            code_item(
                "src/runtime/TransportRegistry.ets",
                "TransportRegistry",
                30.0,
                ["structural_behavior"],
                "behavior: fallbackbranch, repositoryboundary, statewrite",
            ),
            code_item(
                "src/data/ArchiveRepository.ets",
                "ArchiveRepository",
                40.0,
                ["structural_behavior"],
                "behavior: repositoryboundary",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query=(
                "Offline startup uses fallback cards and never upgrades after reconnect. "
                "Locate repository selection and synchronization."
            ),
        )

        self.assertEqual(
            [
                "src/state/DeviceSyncStore.ets",
                "src/runtime/TransportRegistry.ets",
            ],
            [item["file_path"] for item in selected],
        )

    def test_reusable_spacing_prefers_widget_owner_over_page_consumers(self) -> None:
        candidates = [
            code_item(
                "src/widgets/NotificationRow.ets",
                "NotificationRow",
                26.0,
                ["structural_behavior"],
                "operations: margin, padding",
            ),
            code_item(
                "src/pages/NotificationDetails.ets",
                "NotificationDetails",
                38.0,
                ["structural_behavior"],
                "operations: margin",
            ),
            code_item(
                "src/pages/NotificationList.ets",
                "NotificationList",
                36.0,
                ["structural_behavior"],
                "operations: padding",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="Locate the reusable row spacing owner with no right breathing room.",
        )

        self.assertEqual(
            ["src/widgets/NotificationRow.ets"],
            [item["file_path"] for item in selected],
        )

    def test_unmatched_opaque_marker_abstains_from_topic_only_code(self) -> None:
        candidate = code_item(
            "src/gateways/TelemetrySocketGateway.ets",
            "TelemetrySocketGateway",
            32.0,
            ["query_focus_coverage"],
            "telemetry callback and deserialization boundary",
        )

        selected = diverse_code_matches(
            [candidate],
            5,
            query="Locate source for unknown telemetry nonce ZXQ991_UNMAPPED.",
        )

        self.assertEqual([], selected)

    def test_exact_opaque_marker_keeps_its_declared_owner(self) -> None:
        candidate = code_item(
            "src/telemetry/ZxqEvent.ets",
            "ZXQ991_UNMAPPED",
            32.0,
            ["exact_symbol"],
            "declares ZXQ991_UNMAPPED telemetry event",
        )

        selected = diverse_code_matches(
            [candidate],
            5,
            query="Locate source for unknown telemetry nonce ZXQ991_UNMAPPED.",
        )

        self.assertEqual([candidate], selected)

    def test_multi_mechanism_owner_suppresses_single_mechanism_neighbors(self) -> None:
        candidates = [
            code_item(
                "src/coordinators/OrderCommitCoordinator.ets",
                "OrderCommitCoordinator",
                28.0,
                ["structural_behavior"],
                "behavior: validationguard, actiondispatch, persistencewrite",
            ),
            code_item(
                "src/validation/OrderValidator.ets",
                "OrderValidator",
                42.0,
                ["structural_behavior"],
                "behavior: validationguard",
            ),
            code_item(
                "src/actions/OrderActionButton.ets",
                "OrderActionButton",
                40.0,
                ["structural_behavior"],
                "behavior: actiondispatch",
            ),
            code_item(
                "src/storage/OrderStore.ets",
                "OrderStore",
                38.0,
                ["structural_behavior"],
                "behavior: persistencewrite",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query=(
                "Validation reports an error but order dispatch and persistence still happen. "
                "Locate the guarded commit owner."
            ),
        )

        self.assertEqual(
            ["src/coordinators/OrderCommitCoordinator.ets"],
            [item["file_path"] for item in selected],
        )


def code_item(
    file_path: str,
    symbol: str,
    score: float = 10.0,
    reasons: list[str] | None = None,
    summary: str = "",
) -> dict[str, object]:
    return {
        "file_path": file_path,
        "symbol": symbol,
        "score": score,
        "summary": summary,
        "match_reasons": reasons or [],
    }


if __name__ == "__main__":
    unittest.main()
