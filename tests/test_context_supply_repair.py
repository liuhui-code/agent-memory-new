# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class ContextSupplyRepairTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "context-supply-project"
        self.root.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_source(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")

    def learn(self) -> None:
        self.run_memory(self.root, "init")
        self.run_memory(self.root, "learn-path", "--path", ".", "--json")

    def context(self, query: str, compact: bool) -> dict[str, object]:
        arguments = ["context", "--query", query, "--json"]
        if compact:
            arguments.insert(1, "--compact")
        result = self.run_memory(self.root, *arguments)
        return json.loads(result.stdout)

    def test_fielded_string_key_candidate_reaches_compact_handoff(self) -> None:
        self.write_source(
            "src/storage/ArchiveService.ets",
            """
export class ArchiveService {
  async apply(): Promise<void> {
    const value = await this.preferences.get('theme_font_payload_v7')
    await this.archive.write(value)
  }
}
""",
        )
        self.learn()
        query = "Locate the callable that owns theme_font_payload_v7."

        full = self.context(query, compact=False)
        fielded = full["query_audit"]["candidate_recall"]["tables"][
            "code_symbols"
        ]["fielded_retrieval"]
        self.assertIn(
            "src/storage/ArchiveService.ets",
            {item["file_path"] for item in fielded["candidate_refs"]},
        )

        compact = self.context(query, compact=True)
        handoff = compact["query_handoff"]
        anchor = next((
            item for item in handoff["code_anchors"]
            if item["file_path"] == "src/storage/ArchiveService.ets"
        ), None)
        audit = full["query_audit"]
        self.assertIsNotNone(anchor, {
            "handoff": handoff,
            "candidate_refs": audit["candidate_recall"]["tables"][
                "code_symbols"
            ]["candidate_refs"],
            "localization": audit["hierarchical_localization"],
        })
        assert anchor is not None
        self.assertEqual("apply", anchor["symbol"])
        self.assertIn("theme_font_payload_v7", anchor["source_excerpts"][0]["content"])

    def test_fielded_mechanism_candidate_reaches_compact_handoff(self) -> None:
        self.write_source(
            "src/runtime/DecisionUnit.ets",
            """
export class DecisionUnit {
  evaluate(): boolean {
    return canIUse('SystemCapability.Multimedia.Audio')
  }
}
""",
        )
        self.learn()
        query = "Locate the callable that applies a platform predicate."

        full = self.context(query, compact=False)
        fielded = full["query_audit"]["candidate_recall"]["tables"][
            "code_symbols"
        ]["fielded_retrieval"]
        target_refs = [
            item for item in fielded["candidate_refs"]
            if item["file_path"] == "src/runtime/DecisionUnit.ets"
        ]
        self.assertTrue(target_refs)
        self.assertIn("semantic_mechanism_fts", target_refs[0]["channels"])

        compact = self.context(query, compact=True)
        anchor = next((
            item for item in compact["query_handoff"]["code_anchors"]
            if item["file_path"] == "src/runtime/DecisionUnit.ets"
        ), None)
        self.assertIsNotNone(anchor, compact["query_handoff"])
        assert anchor is not None
        self.assertEqual("evaluate", anchor["symbol"])
        self.assertIn("canIUse", anchor["source_excerpts"][0]["content"])

    def test_late_callable_excerpt_scans_inside_selected_range(self) -> None:
        file_filler = "\n".join(
            f"// unrelated package audit row {index}" for index in range(4050)
        )
        method_filler = "\n".join(
            f"    const ignoredRow{index}: number = {index}" for index in range(55)
        )
        self.write_source(
            "src/packages/LatePackageUnit.ets",
            f"""
export class LatePackageUnit {{
{file_filler}
  async reconcileLatePackage(): Promise<void> {{
{method_filler}
    await this.archive.commitRecoveredManifest()
  }}
}}
""",
        )
        self.learn()

        compact = self.context(
            "reconcileLatePackage must commitRecoveredManifest after recovery",
            compact=True,
        )
        anchor = next(
            item for item in compact["query_handoff"]["code_anchors"]
            if item["file_path"] == "src/packages/LatePackageUnit.ets"
        )
        self.assertEqual("reconcileLatePackage", anchor["symbol"])
        excerpts = anchor.get("source_excerpts") or []
        self.assertTrue(excerpts)
        self.assertIn("commitRecoveredManifest", excerpts[0]["content"])
