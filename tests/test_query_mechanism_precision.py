# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_code_selection import diverse_code_matches


class QueryMechanismPrecisionTests(unittest.TestCase):
    def test_async_state_owner_suppresses_partial_neighbors(self) -> None:
        candidates = [
            code_item(
                "src/coordinators/DocumentNavigationCoordinator.ets",
                30.0,
                "behavior: asyncboundary, orderingguard, statewrite",
            ),
            code_item(
                "src/services/DocumentLoader.ets",
                45.0,
                "behavior: asyncboundary",
            ),
            code_item(
                "src/stores/DocumentSelectionStore.ets",
                43.0,
                "behavior: statewrite",
            ),
        ]
        for item in candidates:
            item["match_reasons"].append("exact_behavior_operation")

        selected = diverse_code_matches(
            candidates,
            5,
            query="Rapid document navigation renders stale content after repeated taps.",
        )

        self.assertEqual(
            ["src/coordinators/DocumentNavigationCoordinator.ets"],
            [item["file_path"] for item in selected],
        )

    def test_touch_arbitration_owner_suppresses_partial_neighbors(self) -> None:
        candidates = [
            code_item(
                "src/views/CanvasInteractionSurface.ets",
                28.0,
                "behavior: gestureboundary, statewrite",
            ),
            code_item(
                "src/widgets/ResizeHandle.ets",
                46.0,
                "behavior: gestureboundary",
            ),
            code_item(
                "src/models/CanvasSelection.ets",
                42.0,
                "behavior: statewrite",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="Two touch handlers conflict while resizing a canvas selection.",
        )

        self.assertEqual(
            ["src/views/CanvasInteractionSurface.ets"],
            [item["file_path"] for item in selected],
        )

    def test_collection_mutation_owner_suppresses_single_mechanism_neighbors(self) -> None:
        candidates = [
            code_item(
                "src/controllers/SeatMapController.ets",
                30.0,
                "behavior: eventboundary, collectionwrite",
            ),
            code_item(
                "src/widgets/SeatCell.ets",
                44.0,
                "behavior: eventboundary",
            ),
            code_item(
                "src/stores/SeatStore.ets",
                42.0,
                "behavior: collectionwrite",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="Tapping a seat should propagate selection to adjacent seats.",
        )

        self.assertEqual(
            ["src/controllers/SeatMapController.ets"],
            [item["file_path"] for item in selected],
        )

    def test_lifecycle_persistence_owner_suppresses_partial_neighbors(self) -> None:
        candidates = [
            code_item(
                "src/coordinators/DraftSessionCoordinator.ets",
                28.0,
                "behavior: lifecyclesync, statewrite, persistencewrite",
            ),
            code_item(
                "src/pages/DraftPage.ets",
                48.0,
                "behavior: lifecyclesync, statewrite",
            ),
            code_item(
                "src/storage/DraftPreferences.ets",
                46.0,
                "behavior: persistencewrite",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query=(
                "A saved draft resets after relaunch; locate lifecycle restore "
                "and persistence ownership."
            ),
        )

        self.assertEqual(
            ["src/coordinators/DraftSessionCoordinator.ets"],
            [item["file_path"] for item in selected],
        )

    def test_conditional_data_owner_suppresses_branch_and_source_helpers(self) -> None:
        candidates = [
            code_item(
                "src/viewmodels/CollectionLoader.ets",
                28.0,
                "behavior: conditionalbranch, datasourceboundary, statewrite",
            ),
            code_item(
                "src/pages/CollectionPage.ets",
                46.0,
                "behavior: conditionalbranch, statewrite",
            ),
            code_item(
                "src/services/AssetSource.ets",
                44.0,
                "behavior: datasourceboundary",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="A folder-backed collection stays empty when nested items are loaded.",
        )

        self.assertEqual(
            ["src/viewmodels/CollectionLoader.ets"],
            [item["file_path"] for item in selected],
        )

    def test_lifecycle_cleanup_owner_suppresses_partial_callback_neighbors(self) -> None:
        candidates = [
            code_item(
                "src/abilities/WorkspaceAbility.ets",
                30.0,
                "behavior: lifecycleboundary, callbackcleanup",
            ),
            code_item(
                "src/pages/WorkspacePage.ets",
                48.0,
                "behavior: lifecycleboundary",
            ),
            code_item(
                "src/runtime/WindowRegistry.ets",
                45.0,
                "behavior: callbackcleanup",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="Unregister the listener before the window context is destroyed.",
        )

        self.assertEqual(
            ["src/abilities/WorkspaceAbility.ets"],
            [item["file_path"] for item in selected],
        )

    def test_resource_lifecycle_owner_suppresses_async_page_noise(self) -> None:
        candidates = [
            code_item(
                "src/media/VoiceCaptureCoordinator.ets",
                29.0,
                "behavior: resourceacquire, resourcerelease, asyncboundary",
            ),
            code_item(
                "src/pages/VoiceMessagePage.ets",
                47.0,
                "behavior: asyncboundary, statewrite",
            ),
            code_item(
                "src/services/AudioPermissionService.ets",
                44.0,
                "behavior: asyncboundary",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query=(
                "Voice recording intermittently stops after repeated capture sessions; "
                "locate media resource shutdown ownership."
            ),
        )

        self.assertEqual(
            ["src/media/VoiceCaptureCoordinator.ets"],
            [item["file_path"] for item in selected],
        )

    def test_back_key_owner_suppresses_partial_keyboard_neighbors(self) -> None:
        candidates = [
            code_item(
                "src/pages/ShortcutSearchPage.ets",
                28.0,
                "behavior: keyboundary, backkeyguard, conditionalbranch",
            ),
            code_item(
                "src/components/KeyboardHint.ets",
                46.0,
                "behavior: keyboundary",
            ),
            code_item(
                "src/pages/ConversationPage.ets",
                43.0,
                "behavior: conditionalbranch",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="The physical keyboard back key conflicts with search input.",
        )

        self.assertEqual(
            ["src/pages/ShortcutSearchPage.ets"],
            [item["file_path"] for item in selected],
        )

    def test_two_strong_identity_paths_suppress_expansion_only_tail(self) -> None:
        candidates = [
            identity_item(
                "src/pages/ProductSearchPage.ets", 61.0, "exact_symbol"
            ),
            identity_item(
                "src/services/ProductSearchService.ets", 55.0, "exact_path_segment"
            ),
            identity_item(
                "src/coordinators/SessionUsageCoordinator.ets",
                10.0,
                "expanded_query:symbol",
            ),
            identity_item(
                "src/pages/VoiceMessagePage.ets",
                10.0,
                "expanded_query:symbol",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="Locate search result state and the query service owner.",
        )

        self.assertEqual(
            {
                "src/pages/ProductSearchPage.ets",
                "src/services/ProductSearchService.ets",
            },
            {item["file_path"] for item in selected},
        )

    def test_archive_io_owner_suppresses_package_metadata(self) -> None:
        candidates = [
            code_item(
                "src/io/AssetArchiveInstaller.ets", 29.0,
                "behavior: archiveioboundary, asyncboundary",
            ),
            code_item(
                "src/config/ArchivePackageProfile.ets", 48.0,
                "archive package and upgrade metadata",
            ),
            code_item(
                "src/pages/UpgradeStatusPage.ets", 44.0,
                "upgrade archive status page",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="An existing temporary archive is reused during asset extraction.",
        )

        self.assertEqual(
            ["src/io/AssetArchiveInstaller.ets"],
            [item["file_path"] for item in selected],
        )

    def test_collection_fold_owner_suppresses_consumer_page(self) -> None:
        candidates = [
            code_item(
                "src/sharing/SharedRecordCollector.ets", 27.0,
                "behavior: collectionfold, conditionalbranch",
            ),
            code_item(
                "src/pages/ShareComposerPage.ets", 47.0,
                "shared records composer page",
            ),
            code_item(
                "src/components/RecordPreview.ets", 43.0,
                "shared record preview component",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="Combining multiple shared records preserves only the final item.",
        )

        self.assertEqual(
            ["src/sharing/SharedRecordCollector.ets"],
            [item["file_path"] for item in selected],
        )

    def test_keyboard_focus_owner_requires_both_mechanisms(self) -> None:
        candidates = [
            code_item(
                "src/web/DesktopEditorFocusController.ets", 28.0,
                "behavior: keyboardvisibility, focusstate, callbackboundary",
            ),
            code_item(
                "src/components/KeyboardFocusHint.ets", 46.0,
                "behavior: focusstate",
            ),
            code_item(
                "src/pages/EditorKeyboardPage.ets", 45.0,
                "behavior: keyboardvisibility",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="Dismissing the software keyboard prevents the editor regaining focus.",
        )

        self.assertEqual(
            ["src/web/DesktopEditorFocusController.ets"],
            [item["file_path"] for item in selected],
        )

    def test_color_parser_owner_suppresses_status_page(self) -> None:
        candidates = [
            code_item(
                "src/theme/SystemBarColorAdapter.ets", 30.0,
                "behavior: colorparser",
            ),
            code_item(
                "src/pages/AppearanceSettingsPage.ets", 49.0,
                "status bar color settings page",
            ),
        ]

        selected = diverse_code_matches(
            candidates,
            5,
            query="Status bar color conversion returns an invalid opaque value.",
        )

        self.assertEqual(
            ["src/theme/SystemBarColorAdapter.ets"],
            [item["file_path"] for item in selected],
        )

    def test_runtime_owners_suppress_metadata_and_partial_neighbors(self) -> None:
        scenarios = [
            (
                "Pasting plain text returns empty despite clipboard content.",
                "src/io/ClipboardContentReader.ets",
                "behavior: clipboardread, asyncboundary",
            ),
            (
                "Startup begins before the permission request result is checked.",
                "src/runtime/PermissionStartupCoordinator.ets",
                "behavior: permissionrequest, permissionguard, asyncboundary",
            ),
            (
                "Manifest declares the capability but the runtime probe rejects it.",
                "src/runtime/FeatureCapabilityProbe.ets",
                "behavior: runtimecapability, asyncboundary",
            ),
        ]
        for query, expected, summary in scenarios:
            candidates = [
                code_item(expected, 28.0, summary),
                code_item(
                    "src/config/RuntimeFeatureManifest.ets", 52.0,
                    "manifest permission and capability metadata",
                ),
                code_item(
                    "src/pages/CapabilitySettingsPage.ets", 45.0,
                    "capability settings page",
                ),
            ]

            selected = diverse_code_matches(candidates, 5, query=query)

            self.assertEqual([expected], [item["file_path"] for item in selected])


def code_item(file_path: str, score: float, summary: str) -> dict[str, object]:
    return {
        "file_path": file_path,
        "symbol": file_path.rsplit("/", 1)[-1].removesuffix(".ets"),
        "score": score,
        "summary": summary,
        "match_reasons": ["structural_behavior"],
    }


def identity_item(file_path: str, score: float, reason: str) -> dict[str, object]:
    item = code_item(file_path, score, "ArkTS source anchor")
    item["match_reasons"] = [reason]
    return item


if __name__ == "__main__":
    unittest.main()
