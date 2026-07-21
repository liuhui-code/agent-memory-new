# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_behavior_concepts import behavior_marker_terms
from tools.agent_memory_runtime.query_candidate_recall import (
    SQLiteCandidateRecall,
    recall_candidate_ids_with_lanes,
    recall_focus_terms,
)
from tools.agent_memory_runtime.query_results import limited_context
from tools.agent_memory_runtime.storage import connect, ensure_initialized, resolve_project


class QueryCandidateRecallTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "large-arkts-app"
        self.source.mkdir()
        self.runtime_project = resolve_project(
            str(self.source), str(self.memory_home(self.source))
        )
        ensure_initialized(self.runtime_project)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_focus_terms_remove_request_boilerplate(self) -> None:
        terms = recall_focus_terms(
            "Locate the application code owner for privacy policy content rendering"
        )

        self.assertEqual(["privacy", "policy", "rendering"], terms)

    def test_focus_terms_cover_late_owner_clause_in_long_problem(self) -> None:
        terms = recall_focus_terms(
            "Refreshing inventory updates can leave loading stuck while concurrent "
            "additions reorder records. Locate the dashboard loading owner and the "
            "warehouse record data source mutation owner."
        )

        self.assertIn("inventory", terms)
        self.assertIn("mutation", terms)
        self.assertTrue({"warehouse", "data"} & set(terms))

    def test_abstract_symptoms_map_to_bounded_behavior_markers(self) -> None:
        self.assertTrue(
            {"listdirection", "height"}
            <= set(behavior_marker_terms("Records cannot scroll when content fills the viewport"))
        )
        self.assertIn(
            "foreach",
            behavior_marker_terms("Changing the quarter leaves revenue totals unchanged"),
        )
        self.assertIn(
            "backgroundcolor",
            behavior_marker_terms("The filter chooser overlaps the numeric keypad"),
        )
        self.assertIn(
            "fallbackbranch",
            behavior_marker_terms(
                "Offline startup uses fallback data and never upgrades after reconnect"
            ),
        )
        self.assertIn(
            "callbackboundary",
            behavior_marker_terms(
                "A malformed payload throws in the callback and later responses stop"
            ),
        )
        self.assertIn(
            "actiondispatch",
            behavior_marker_terms(
                "The action completes but the details screen remains unchanged"
            ),
        )
        self.assertTrue(
            {"margin", "padding"}
            <= set(behavior_marker_terms(
                "Locate the reusable row spacing owner with no right breathing room"
            )),
        )
        self.assertIn(
            "statehandoff",
            behavior_marker_terms(
                "Editing a second row opens the panel with the previously selected item"
            ),
        )
        self.assertIn(
            "validationguard",
            behavior_marker_terms(
                "A required field error is shown but the invalid update still submits"
            ),
        )
        self.assertIn(
            "persistencewrite",
            behavior_marker_terms(
                "The usage counter and last-used time disappear after restart"
            ),
        )
        self.assertIn(
            "countertimestampwrite",
            behavior_marker_terms(
                "The usage counter and last-used time disappear after restart"
            ),
        )
        self.assertIn(
            "persistencewrite",
            behavior_marker_terms(
                "An invalid order still reaches action dispatch and storage"
            ),
        )
        self.assertIn(
            "persistencewrite",
            behavior_marker_terms("校验后仍执行动作并写入存储"),
        )
        self.assertNotIn(
            "countertimestampwrite",
            behavior_marker_terms("校验后仍执行动作并写入存储"),
        )
        self.assertIn(
            "gestureboundary",
            behavior_marker_terms(
                "Dragging the board moves cells but points and completion stay unchanged"
            ),
        )
        self.assertNotIn(
            "actiondispatch",
            behavior_marker_terms(
                "Locate the gesture interaction owner after dragging the board"
            ),
        )
        self.assertIn(
            "collectionwrite",
            behavior_marker_terms(
                "Tapping a seat should propagate selection to adjacent seats"
            ),
        )
        self.assertTrue(
            {"lifecyclesync", "statewrite", "persistencewrite"}
            <= set(behavior_marker_terms(
                "A saved draft resets after relaunch; locate lifecycle restore ownership"
            )),
        )
        self.assertTrue(
            {"asyncboundary", "orderingguard", "statewrite"}
            <= set(behavior_marker_terms(
                "Rapid document navigation renders a stale entry after repeated taps"
            )),
        )
        self.assertTrue(
            {"gestureboundary", "statewrite"}
            <= set(behavior_marker_terms(
                "Two touch handlers conflict while resizing a canvas selection"
            )),
        )
        self.assertTrue(
            {"touchboundary", "indexedread"}
            <= set(behavior_marker_terms(
                "The first finger is missing from an empty touch event"
            )),
        )
        self.assertTrue(
            {"conditionalbranch", "datasourceboundary"}
            <= set(behavior_marker_terms(
                "A folder-backed collection stays empty when nested items are loaded"
            )),
        )
        self.assertTrue(
            {"lifecycleboundary", "callbackcleanup"}
            <= set(behavior_marker_terms(
                "Unregister the listener before the window context is destroyed"
            )),
        )
        self.assertIn(
            "listdirection",
            behavior_marker_terms("A horizontal list clips cards in its viewport"),
        )
        self.assertIn(
            "horizontalaxis",
            behavior_marker_terms("A horizontal list clips cards in its viewport"),
        )
        self.assertIn(
            "toolbarrole",
            behavior_marker_terms(
                "Keyboard resize pushes the shared navigation toolbar off screen"
            ),
        )
        self.assertIn(
            "resourcerelease",
            behavior_marker_terms(
                "Voice recording intermittently stops after repeated capture sessions"
            ),
        )
        self.assertIn(
            "resourcerelease",
            behavior_marker_terms("资源被重复释放时只应销毁一次"),
        )
        self.assertTrue(
            {"keyboundary", "backkeyguard"}
            <= set(behavior_marker_terms(
                "The physical keyboard back key conflicts with search input"
            )),
        )
        self.assertIn(
            "archiveioboundary",
            behavior_marker_terms(
                "An existing temporary archive is reused during asset extraction"
            ),
        )
        self.assertIn(
            "collectionfold",
            behavior_marker_terms(
                "Combining multiple shared records preserves only the final item"
            ),
        )
        self.assertTrue(
            {"keyboardvisibility", "focusstate"}
            <= set(behavior_marker_terms(
                "Dismissing the software keyboard prevents the editor regaining focus"
            )),
        )
        self.assertIn(
            "colorparser",
            behavior_marker_terms(
                "Status bar color conversion returns an invalid opaque value"
            ),
        )
        self.assertIn(
            "clipboardread",
            behavior_marker_terms(
                "Pasting plain text returns empty despite clipboard content"
            ),
        )
        self.assertNotIn(
            "permissionrequest",
            behavior_marker_terms(
                "剪贴板文本为空，请返回读取实现，不要返回权限配置。"
            ),
        )
        self.assertTrue(
            {"permissionrequest", "permissionguard"}
            <= set(behavior_marker_terms(
                "Startup begins before the permission request result is checked"
            )),
        )
        self.assertIn(
            "outputreadloop",
            behavior_marker_terms(
                "Command output is empty although the line reader has data"
            ),
        )
        self.assertIn(
            "runtimecapability",
            behavior_marker_terms(
                "Manifest declares the capability but the runtime probe rejects it"
            ),
        )

    def test_structural_lane_recalls_complementary_lifecycle_owners(self) -> None:
        query = (
            "Offline startup uses fallback cards and never upgrades after reconnect. "
            "Locate repository selection and the synchronization trigger."
        )
        with connect(self.runtime_project) as conn:
            registry_id = self.insert_file(
                conn,
                "features/runtime/TransportRegistry.ets",
                "behavior: fallbackbranch, repositoryboundary, statewrite",
            )
            store_id = self.insert_file(
                conn,
                "features/state/DeviceSyncStore.ets",
                "behavior: lifecyclesync, repositoryboundary, statewrite",
            )
            self.insert_file(
                conn,
                "features/data/ArchiveRepository.ets",
                "behavior: repositoryboundary",
            )
            conn.commit()

            ids, lanes, audit = recall_candidate_ids_with_lanes(
                conn, self.runtime_project, "code_files", query, 20
            )

        self.assertTrue({registry_id, store_id} <= set(ids))
        self.assertIn("structural_fts", lanes[registry_id])
        self.assertIn("structural_fts", lanes[store_id])
        self.assertGreaterEqual(audit["structural_term_count"], 3)

        selected = limited_context(self.runtime_project, query)["wiki_matches"]
        self.assertEqual(
            {
                "features/runtime/TransportRegistry.ets",
                "features/state/DeviceSyncStore.ets",
            },
            {item["file_path"] for item in selected},
        )

    def test_structural_lane_recalls_owners_without_literal_query_terms(self) -> None:
        cases = [
            (
                "features/shipping/ShipmentColumn.ets",
                "ArkTS component; operations: listDirection, height, padding",
                "Records cannot scroll when content fills the viewport",
            ),
            (
                "features/finance/QuarterLedger.ets",
                "ArkTS component; operations: forEach, getFullYear",
                "Changing the quarter leaves revenue and cost totals unchanged",
            ),
            (
                "features/inventory/FilterSurface.ets",
                "ArkTS component; operations: backgroundColor, shadow",
                "The filter chooser overlaps the numeric keypad",
            ),
        ]
        with connect(self.runtime_project) as conn:
            expected = {
                query: self.insert_file(conn, path, summary)
                for path, summary, query in cases
            }
            conn.commit()
            observations = {}
            for _path, _summary, query in cases:
                ids, lanes, audit = recall_candidate_ids_with_lanes(
                    conn, self.runtime_project, "code_files", query, 20
                )
                observations[query] = (ids, lanes, audit)

        for query, expected_id in expected.items():
            ids, lanes, audit = observations[query]
            self.assertIn(expected_id, ids)
            self.assertIn("structural_fts", lanes[expected_id])
            self.assertGreater(audit["structural_term_count"], 0)
            selected = limited_context(self.runtime_project, query)["wiki_matches"]
            self.assertEqual(expected_id, selected[0]["id"])
            self.assertIn("structural_behavior", selected[0]["match_reasons"])

    def test_structural_lane_keeps_reserved_recall_when_broad_fts_saturates(self) -> None:
        query = (
            "A reusable toolbar disappears when the input viewport changes; "
            "return the toolbar component rather than its page or action bar."
        )
        with connect(self.runtime_project) as conn:
            expected_id = self.insert_file(
                conn,
                "features/navigation/NavigationToolbar.ets",
                "ArkTS component; behavior: toolbarrole; operations: height, width",
            )
            for index in range(80):
                self.insert_file(
                    conn,
                    f"features/messages/MessageActionBar{index}.ets",
                    "Reusable page action bar for input viewport changes",
                )
            conn.commit()

            ids, lanes, audit = recall_candidate_ids_with_lanes(
                conn, self.runtime_project, "code_files", query, 20
            )

        self.assertTrue(audit["broad_saturated"])
        self.assertIn(expected_id, ids)
        self.assertIn("structural_fts", lanes[expected_id])

    def test_term_lanes_recall_complementary_owners_under_broad_noise(self) -> None:
        query = (
            "Privacy policy and terms Web content remain bright in dark mode. "
            "Locate both embedded content owners."
        )
        with connect(self.runtime_project) as conn:
            privacy_id = self.insert_file(
                conn,
                "features/legal/PrivacySurface.ets",
                "Privacy policy embedded browser surface",
            )
            terms_id = self.insert_file(
                conn,
                "features/legal/AgreementSurface.ets",
                "Terms of service Web embedded browser surface",
            )
            for index in range(80):
                self.insert_file(
                    conn,
                    f"features/feed/ContentCard{index}.ets",
                    "Web content dark mode component owner",
                )
            conn.commit()

            ids, lanes, audit = recall_candidate_ids_with_lanes(
                conn,
                self.runtime_project,
                "code_files",
                query,
                20,
            )

        self.assertTrue({privacy_id, terms_id} <= set(ids))
        self.assertTrue(any(lane.startswith("term_fts:") for lane in lanes[privacy_id]))
        self.assertTrue(any(lane.startswith("term_fts:") for lane in lanes[terms_id]))
        self.assertGreater(audit["lane_counts"]["broad_fts"], 0)
        self.assertLessEqual(audit["candidate_count"], 20)

        context = limited_context(self.runtime_project, query)
        selected_paths = {item["file_path"] for item in context["wiki_matches"]}
        self.assertTrue({
            "features/legal/PrivacySurface.ets",
            "features/legal/AgreementSurface.ets",
        } <= selected_paths, [
            (item["file_path"], item.get("score"), item.get("match_reasons"))
            for item in context["wiki_matches"]
        ])

    def test_context_audit_exposes_retrieval_stage_boundaries(self) -> None:
        with connect(self.runtime_project) as conn:
            self.insert_file(
                conn,
                "features/storage/StoreConfiguration.ets",
                "Relational store tokenizer and security configuration",
            )
            conn.commit()

        context = limited_context(
            self.runtime_project,
            "Locate the relational store tokenizer configuration owner source file",
        )

        audit = context["query_audit"]
        self.assertEqual(
            "sqlite_fts5_passage_rrf/v4",
            audit["candidate_recall"]["provider"],
        )
        self.assertEqual(
            "reciprocal_rank_fusion/v1",
            audit["candidate_recall"]["rank_fusion_provider"],
        )
        self.assertEqual(
            {"scored", "after_intent_gate", "selected"},
            set(audit["retrieval_stages"]),
        )
        self.assertGreater(
            audit["candidate_recall"]["tables"]["code_files"]["candidate_count"],
            0,
        )
        self.assertTrue(
            audit["top_explanations"]["wiki_matches"][0]["recall_lanes"]
        )
        self.assertEqual(
            "reciprocal_rank_fusion/v1",
            audit["top_explanations"]["wiki_matches"][0]["recall_fusion"]["provider"],
        )
        self.assertEqual(
            {"broad_fts"},
            set(audit["candidate_recall"]["tables"]["code_files"]["lane_counts"]),
        )

    def test_recall_port_can_be_replaced_without_changing_collection_contract(self) -> None:
        port = SQLiteCandidateRecall()
        with connect(self.runtime_project) as conn:
            batch = port.recall(conn, self.runtime_project, "no matching evidence")

        self.assertEqual(
            {
                "semantic_facts", "reflections", "episodes", "code_files",
                "code_symbols", "code_log_statements",
            },
            set(batch.rows),
        )
        self.assertEqual("agent-candidate-recall-audit/v1", batch.audit["schema_version"])

    def insert_file(self, conn: object, file_path: str, summary: str) -> int:
        cursor = conn.execute(
            """
            INSERT INTO code_files(
              project_id, file_path, summary, language, business_summary,
              business_terms, updated_at
            ) VALUES (?, ?, ?, 'ArkTS', ?, '[]', '2026-07-18T00:00:00Z')
            """,
            (self.runtime_project.project_id, file_path, summary, summary),
        )
        return int(cursor.lastrowid)


if __name__ == "__main__":
    import unittest

    unittest.main()
