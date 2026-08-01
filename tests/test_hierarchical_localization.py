# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_capability import summarize_context
from tools.agent_memory_runtime.context_hierarchical_metrics import (
    assess_hierarchical_localization,
)
from tools.agent_memory_runtime.query_hierarchical_localization import (
    file_rank_prior,
    select_graph_seeds,
)
from tools.agent_memory_runtime.query_localization_file_candidates import (
    MAX_FILES_PER_DIRECTORY,
    select_file_candidates,
)


SNAPSHOT_SOURCE = """
export class SnapshotCoordinator {
  private preferences: Preferences

  async restoreSnapshot(payload: string, maximumBytes: number): Promise<void> {
    if (payload.length > maximumBytes) {
      return
    }
    const saved = await this.preferences.get('snapshot_key')
    this.controller.restore(saved)
  }
}
"""


class HierarchicalLocalizationTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "localization-project"
        self.root.mkdir()
        self.write_file("src/services/SnapshotCoordinator.ets", SNAPSHOT_SOURCE)
        self.write_file(
            "src/pages/SnapshotPage.ets",
            """
import { SnapshotCoordinator } from '../services/SnapshotCoordinator'
@Component
struct SnapshotPage {
  private coordinator: SnapshotCoordinator = new SnapshotCoordinator()

  async refreshSnapshot(): Promise<void> {
    await this.coordinator.restoreSnapshot('', 1024)
  }

  build(): void {
    Button('Restore').onClick(() => this.refreshSnapshot())
  }
}
""",
        )
        self.write_file(
            "src/views/EventBubble.ets",
            """
@Component
struct EventBubble {
  @Prop showHeader: boolean = true

  build(): void {
    if (this.showHeader) {
      Text('Category')
    }
  }
}
""",
        )
        self.write_file(
            "src/views/TimelineRow.ets",
            """
import { EventBubble } from './EventBubble'
@Component
struct TimelineRow {
  @Prop showHeader: boolean = true

  build(): void {
    EventBubble({ showHeader: this.showHeader })
  }
}
""",
        )
        self.run_memory(self.root, "init")
        self.run_memory(self.root, "learn-path", "--path", ".", "--json")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_file(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")

    def full_context(self, query: str) -> dict[str, object]:
        result = self.run_memory(self.root, "context", "--query", query, "--json")
        return json.loads(result.stdout)

    def localization(self, query: str) -> dict[str, object]:
        payload = self.full_context(query)
        return payload["query_audit"]["hierarchical_localization"]

    def compact_context(self, query: str) -> dict[str, object]:
        result = self.run_memory(self.root, "context", "--query", query, "--compact", "--json")
        return json.loads(result.stdout)

    def test_mechanism_match_selects_bounded_expression_window(self) -> None:
        localization = self.localization(
            "resource bound maximum persistence restore snapshot"
        )

        self.assertEqual("serving", localization["mode"])
        contract = localization["projection_contract"]
        self.assertFalse(contract["candidate_recall_changed"])
        self.assertTrue(contract["affects_serving_projection"])
        source_range = next(
            item for item in localization["source_ranges"]
            if item["symbol"] == "restoreSnapshot"
        )
        self.assertEqual("semantic_mechanism_window", source_range["selection_reason"])
        self.assertEqual("resource_bound", source_range["mechanism_kind"])
        self.assertLess(
            source_range["end_line"] - source_range["start_line"],
            source_range["callable_end_line"] - source_range["callable_start_line"],
        )

    def test_one_hop_owner_can_expand_from_selected_callable(self) -> None:
        localization = self.localization("payload maximum bytes preference guard")

        owner = next(
            item for item in localization["graph_owner_candidates"]
            if item["symbol"] == "refreshSnapshot"
        )
        self.assertEqual(1, owner["graph_depth"])
        self.assertTrue({"calls", "awaits"} & set(owner["graph_relations"]))
        self.assertLessEqual(
            localization["stage_counts"]["graph_owner_pool"],
            localization["limits"]["graph_owners"],
        )

    def test_metrics_score_real_full_audit_not_compact_context(self) -> None:
        query = "payload maximum bytes preference guard"
        observation = summarize_context(
            "snapshot", self.compact_context(query), 1, 1, self.full_context(query), 1,
        )
        score = assess_hierarchical_localization(
            {"src/services/SnapshotCoordinator.ets"},
            {
                "hierarchical_callable_spans": [
                    {"file_path": "src/services/SnapshotCoordinator.ets", "symbol": "restoreSnapshot"}
                ],
                "hierarchical_owner_spans": [
                    {"file_path": "src/pages/SnapshotPage.ets", "symbol": "refreshSnapshot"}
                ],
                "hierarchical_range_spans": [
                    {"file_path": "src/services/SnapshotCoordinator.ets", "symbol": "restoreSnapshot"}
                ],
            },
            observation,
        )

        self.assertTrue(score["observed"])
        self.assertTrue(score["serving_observed"])
        self.assertEqual(1.0, score["file_recall"])
        self.assertEqual(1.0, score["callable_recall"])
        self.assertEqual(1.0, score["owner_recall"])
        self.assertEqual(1.0, score["range_recall"])

    def test_file_selection_preserves_directory_diversity_before_fallback(self) -> None:
        items = [
            candidate("src/pages/One.ets", 30.0),
            candidate("src/pages/Two.ets", 29.0),
            candidate("src/pages/Three.ets", 28.0),
            candidate("src/services/Owner.ets", 20.0),
        ]

        selected = select_file_candidates(items, 3, "")

        paths = [item["file_path"] for item in selected]
        self.assertEqual(MAX_FILES_PER_DIRECTORY, sum("src/pages/" in path for path in paths))
        self.assertIn("src/services/Owner.ets", paths)

    def test_file_selection_reserves_bounded_structural_evidence(self) -> None:
        items = [
            candidate(f"src/noise/Generic{index}.ets", 40.0 - index)
            for index in range(10)
        ]
        items.extend([
            candidate(
                "src/pages/BehaviorOwner.ets",
                4.0,
                reasons=["structural_behavior"],
                behavior_coverage=2,
            ),
            candidate(
                "src/services/PartialOwner.ets",
                3.0,
                reasons=["structural_behavior"],
                behavior_coverage=1,
            ),
        ])

        selected = select_file_candidates(
            items,
            8,
            "invalid update still submits validation dispatch",
        )

        paths = [item["file_path"] for item in selected]
        self.assertEqual(8, len(paths))
        self.assertIn("src/pages/BehaviorOwner.ets", paths)
        self.assertIn("src/services/PartialOwner.ets", paths)
        self.assertEqual(
            2,
            next(
                item["structural_coverage"]
                for item in selected
                if item["file_path"] == "src/pages/BehaviorOwner.ets"
            ),
        )

    def test_structural_reservation_cannot_displace_exact_identity(self) -> None:
        items = [
            candidate(
                "src/pages/ExactOwner.ets",
                60.0,
                reasons=["exact_symbol"],
            ),
            candidate(
                "src/pages/StructuralOne.ets",
                4.0,
                reasons=["structural_behavior"],
                behavior_coverage=2,
            ),
            candidate(
                "src/pages/StructuralTwo.ets",
                3.0,
                reasons=["structural_behavior"],
                behavior_coverage=2,
            ),
            *[
                candidate(f"src/noise/Generic{index}.ets", 40.0 - index)
                for index in range(8)
            ],
        ]

        selected = select_file_candidates(
            items,
            8,
            "refresh action unchanged state owner",
        )

        paths = {item["file_path"] for item in selected}
        self.assertIn("src/pages/ExactOwner.ets", paths)

    def test_deferred_lane_duplicates_do_not_reduce_file_budget(self) -> None:
        items = [
            candidate(
                f"src/pages/Owner{index}.ets",
                20.0 - index,
                reasons=["structural_behavior"],
                behavior_coverage=2,
            )
            for index in range(8)
        ]

        selected = select_file_candidates(
            items,
            8,
            "invalid update still submits validation dispatch",
        )

        paths = [item["file_path"] for item in selected]
        self.assertEqual(8, len(paths))
        self.assertEqual(8, len(set(paths)))

    def test_graph_seeds_preserve_direct_or_mechanism_callable_before_rank_fill(self) -> None:
        ranked = [
            {"id": 1, "localization_score": 10.0},
            {"id": 2, "localization_score": 9.0},
            {"id": 3, "localization_score": 8.0, "mechanism_hits": [{"kind": "guard"}]},
            {"id": 4, "localization_score": 7.0, "direct_score": 20.0},
        ]

        seeds = select_graph_seeds(ranked, 3)

        self.assertEqual([4, 3, 1], [item["id"] for item in seeds])

    def test_file_rank_prior_is_bounded_and_reciprocal(self) -> None:
        self.assertEqual(12.0, file_rank_prior(1))
        self.assertEqual(11.0, file_rank_prior(2))
        self.assertEqual(7.333, file_rank_prior(8))
        self.assertEqual(0.0, file_rank_prior(0))

    def test_component_property_flow_projects_parent_build_as_owner(self) -> None:
        localization = self.localization("event bubble show header property flow")

        owner = next(
            item for item in localization["graph_owner_candidates"]
            if item["file_path"] == "src/views/TimelineRow.ets" and item["symbol"] == "build"
        )
        self.assertIn("passes_property", owner["graph_relations"])

    def test_dense_earlier_file_cannot_replace_exact_callable_in_serving_handoff(self) -> None:
        methods = "\n".join(
            f"  processLedgerSegment{index}(): void {{ this.pendingCount = {index} }}"
            for index in range(130)
        )
        self.write_file(
            "src/a/DenseLedgerArchive.ets",
            f"export class DenseLedgerArchive {{\n  pendingCount: number = 0\n{methods}\n}}",
        )
        self.write_file(
            "src/z/LedgerCommitPage.ets",
            """
export class LedgerCommitPage {
  pendingCount: number = 3

  async commitSelectedLedgerBatch(): Promise<void> {
    await LedgerStore.validatePendingBatch()
    await LedgerStore.commitPendingBatch()
    this.pendingCount = 0
  }
}
""",
        )
        self.run_memory(self.root, "learn-path", "--path", ".", "--json")

        payload = self.compact_context(
            "commitSelectedLedgerBatch validates and commits pending ledger batch then clears pendingCount"
        )

        handoff = payload["query_handoff"]
        self.assertEqual(
            "src/z/LedgerCommitPage.ets",
            handoff["callable_evidence"]["primary"]["file_path"],
        )
        self.assertIn(
            "src/z/LedgerCommitPage.ets",
            {item["file_path"] for item in handoff["code_anchors"]},
        )

    def test_known_callable_after_scan_boundary_reaches_serving_excerpt(self) -> None:
        filler = "\n".join(
            f"  // unrelated audit history row {index}" for index in range(4100)
        )
        self.write_file(
            "src/pages/LateAuditPage.ets",
            f"""
export class LateAuditPage {{
{filler}
  async reconcileLateAuditCheckpoint(): Promise<void> {{
    await AuditStore.validateCheckpoint()
    await AuditStore.commitCheckpoint()
    this.pendingAuditCount = 0
  }}
}}
""",
        )
        self.run_memory(self.root, "learn-path", "--path", ".", "--json")

        payload = self.compact_context(
            "reconcileLateAuditCheckpoint validates commits and clears pending audit count"
        )

        anchor = next(
            item for item in payload["query_handoff"]["code_anchors"]
            if item["file_path"] == "src/pages/LateAuditPage.ets"
        )
        excerpt = anchor["source_excerpts"][0]
        self.assertGreater(excerpt["start_line"], 4000)
        self.assertIn("reconcileLateAuditCheckpoint", excerpt["content"])

    def test_inline_builder_reaches_public_compact_source_excerpt(self) -> None:
        self.write_file(
            "src/workspace/WorkspaceShell.ets",
            """
@Entry
@Component
struct WorkspaceShell {
  @State retainedDocument: string = ''

  @Builder renderActiveDocument() {
    Column() {
      Text(this.retainedDocument)
    }
  }

  build() {
    this.renderActiveDocument()
  }
}
""",
        )
        self.run_memory(self.root, "learn-path", "--path", ".", "--json")

        payload = self.compact_context(
            "WorkspaceShell builder renders the retained document state"
        )

        anchor = next(
            item for item in payload["query_handoff"]["code_anchors"]
            if item["file_path"] == "src/workspace/WorkspaceShell.ets"
        )
        excerpts = anchor.get("source_excerpts") or []
        self.assertTrue(excerpts)
        excerpt = excerpts[0]
        self.assertIn("@Builder renderActiveDocument", excerpt["content"])
        self.assertEqual("renderActiveDocument", anchor.get("symbol"))
        source_range = anchor["source_ranges"][0]
        self.assertLessEqual(source_range["start_line"], 6)
        self.assertGreaterEqual(source_range["end_line"], 10)

    def test_excluded_result_clause_does_not_rank_decoy_callable(self) -> None:
        self.write_file(
            "src/adapters/ObserverBoundary.ets",
            """
export class ObserverBoundary {
  attach(runtime: Runtime, listener: Listener): void {
    runtime.setObserver({
      onFailure: (code: number) => listener.onFailure(code)
    })
  }
}
""",
        )
        self.write_file(
            "src/recovery/ObserverRetryService.ets",
            """
export class ObserverRetryService {
  retryFailure(): void {
    this.queue.schedule('observer failure retry service')
  }
}
""",
        )
        self.run_memory(self.root, "learn-path", "--path", ".", "--json")

        payload = self.compact_context(
            "observer failure 回调没有传给 listener，请定位 adapter boundary，不要返回 retry service。"
        )

        handoff = payload["query_handoff"]
        self.assertEqual(
            "src/adapters/ObserverBoundary.ets",
            handoff["callable_evidence"]["primary"]["file_path"],
        )
        self.assertNotIn(
            "src/recovery/ObserverRetryService.ets",
            {item["file_path"] for item in handoff["code_anchors"]},
        )


def candidate(
    path: str,
    score: float,
    reasons: list[str] | None = None,
    behavior_coverage: int = 0,
) -> dict[str, object]:
    return {
        "id": len(path),
        "kind": "file",
        "file_path": path,
        "score": score,
        "match_reasons": reasons or ["semantic_match"],
        "recall_lanes": ["broad_fts"],
        "semantic_behavior_coverage": behavior_coverage,
    }
