# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_fielded_retrieval import fielded_passage_rankings
from tools.agent_memory_runtime.semantic_adapters import ArkTSSemanticAdapter
from tools.agent_memory_runtime.semantic_models import SemanticBatch, SemanticMechanism
from tools.agent_memory_runtime.storage import connect, resolve_project


SOURCE = """
export class SnapshotCoordinator {
  private preferences: Preferences

  async restoreSnapshot(payload: string, maximumBytes: number): Promise<void> {
    if (payload.length > maximumBytes) {
      return
    }
    if (!canIUse('SystemCapability.Web.Webview')) {
      return
    }
    const saved = await this.preferences.get('snapshot_key')
    this.preferences.put('snapshot_key', payload)
    this.controller.restore(saved)
  }

  build(): void {
    Button('Restore').onClick(() => this.restoreSnapshot('', 100))
  }
}
"""


class SemanticMechanismTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "mechanism-project"
        self.root.mkdir()
        self.source = self.root / "src" / "SnapshotCoordinator.ets"
        self.source.parent.mkdir(parents=True)
        self.source.write_text(SOURCE.strip() + "\n", encoding="utf-8")
        self.project = resolve_project(str(self.root), str(self.memory_home(self.root)))
        self.run_memory(self.root, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_static_adapter_emits_language_neutral_mechanisms(self) -> None:
        batch = ArkTSSemanticAdapter().index(self.project, [self.source.resolve()])
        kinds = {item.kind for item in batch.mechanisms}

        self.assertTrue({
            "operation", "guard", "resource_bound", "callback_binding",
            "platform_predicate", "persistence_read", "persistence_write",
        }.issubset(kinds))
        self.assertTrue(all(item.source_key.startswith("symbol:") for item in batch.mechanisms))
        self.assertTrue(all(1 <= len(item.terms) <= 16 for item in batch.mechanisms))

    def test_ir_round_trip_accepts_optional_mechanisms(self) -> None:
        batch = ArkTSSemanticAdapter().index(self.project, [self.source.resolve()])
        restored = SemanticBatch.from_dict(batch.to_dict())
        legacy = batch.to_dict()
        legacy.pop("mechanisms")

        self.assertEqual(batch.mechanisms, restored.mechanisms)
        self.assertEqual([], SemanticBatch.from_dict(legacy).mechanisms)
        with self.assertRaises(ValueError):
            SemanticBatch(
                adapter_id="bad", adapter_version="1", language="ArkTS",
                capabilities=[], source_digests={}, mechanisms=[SemanticMechanism(
                    source_key="missing", kind="unknown", terms=["bad"], line=1,
                )],
            ).validate()

    def test_learning_persists_bounded_evidence_and_passage_terms(self) -> None:
        payload = json.loads(
            self.run_memory(self.root, "learn-path", "--path", ".", "--json").stdout
        )
        with connect(self.project) as conn:
            symbol = conn.execute(
                "SELECT id, mechanism_evidence FROM code_symbols "
                "WHERE project_id = ? AND symbol = 'restoreSnapshot'",
                (self.project.project_id,),
            ).fetchone()
            passage = conn.execute(
                "SELECT mechanism_terms FROM code_passages "
                "WHERE project_id = ? AND source_type = 'code_symbol' AND source_id = ?",
                (self.project.project_id, int(symbol["id"])),
            ).fetchone()
            rankings = fielded_passage_rankings(
                conn, self.project, "resource bound maximum persistence restore", 20,
            )

        evidence = json.loads(symbol["mechanism_evidence"])
        self.assertGreater(payload["parse_stats"]["semantic_index"]["mechanisms_extracted"], 0)
        self.assertLessEqual(len(symbol["mechanism_evidence"].encode("utf-8")), 4096)
        self.assertIn("resource_bound", {item["kind"] for item in evidence})
        self.assertIn("resourcebound", passage["mechanism_terms"].split())
        self.assertIn(int(symbol["id"]), rankings.rankings["semantic_mechanism_fts"])


if __name__ == "__main__":
    unittest.main()
