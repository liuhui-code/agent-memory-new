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
    MAX_FILES_PER_DIRECTORY,
    select_file_candidates,
    select_graph_seeds,
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

        self.assertEqual("shadow", localization["mode"])
        self.assertFalse(localization["serving_candidates_changed"])
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

        selected = select_file_candidates(items, 3)

        paths = [item["file_path"] for item in selected]
        self.assertEqual(MAX_FILES_PER_DIRECTORY, sum("src/pages/" in path for path in paths))
        self.assertIn("src/services/Owner.ets", paths)

    def test_graph_seeds_preserve_direct_or_mechanism_callable_before_rank_fill(self) -> None:
        ranked = [
            {"id": 1, "localization_score": 10.0},
            {"id": 2, "localization_score": 9.0},
            {"id": 3, "localization_score": 8.0, "mechanism_hits": [{"kind": "guard"}]},
            {"id": 4, "localization_score": 7.0, "direct_score": 20.0},
        ]

        seeds = select_graph_seeds(ranked, 3)

        self.assertEqual([4, 3, 1], [item["id"] for item in seeds])

    def test_component_property_flow_projects_parent_build_as_owner(self) -> None:
        localization = self.localization("event bubble show header property flow")

        owner = next(
            item for item in localization["graph_owner_candidates"]
            if item["file_path"] == "src/views/TimelineRow.ets" and item["symbol"] == "build"
        )
        self.assertIn("passes_property", owner["graph_relations"])


def candidate(path: str, score: float) -> dict[str, object]:
    return {
        "id": len(path),
        "kind": "file",
        "file_path": path,
        "score": score,
        "match_reasons": ["semantic_match"],
        "recall_lanes": ["broad_fts"],
    }
