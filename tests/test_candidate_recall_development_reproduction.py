from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class CandidateRecallDevelopmentReproductionTests(AgentMemoryTestBase):
    """Controlled Development baseline for an observed public candidate-loss class."""

    def test_cross_file_semantic_handoff_can_miss_candidate_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "candidate-recall-development"
            root.mkdir()
            write_source(root / "src/runtime/ZBridge.ets", """
export class ZBridge {
  move(payload: Payload): void {
    this.next.apply(payload)
  }
}
""")
            write_source(root / "src/ui/ZIndicator.ets", """
export class ZIndicator {
  apply(payload: Payload): void {
    this.banner.show(payload)
  }
}
""")
            for index in range(260):
                write_source(
                    root / f"src/noise/ConfirmationCatalog{index}.ets",
                    noisy_catalog(index),
                )
            self.run_memory(root, "learn-path", "--path", ".", "--json")
            indexed = json.loads(self.run_memory(
                root, "list", "--type", "code-file", "--limit", "300", "--json",
            ).stdout)

            full = json.loads(self.run_memory(
                root,
                "context",
                "--query",
                "A background verification succeeds but no global confirmation appears. "
                "Identify the components that transfer the pending signal into the interface.",
                "--json",
            ).stdout)
            compact = json.loads(self.run_memory(
                root,
                "context",
                "--compact",
                "--query",
                "A background verification succeeds but no global confirmation appears. "
                "Identify the components that transfer the pending signal into the interface.",
                "--json",
            ).stdout)

        candidate_refs = candidate_refs_by_table(full)
        candidates = {
            item["file_path"]
            for refs in candidate_refs.values()
            for item in refs
        }
        compact_paths = {
            item["file_path"] for item in compact["query_handoff"]["code_anchors"]
        }
        targets = {"src/runtime/ZBridge.ets", "src/ui/ZIndicator.ets"}
        self.assertTrue(targets <= {item["file_path"] for item in indexed})
        self.assertTrue(targets.isdisjoint(candidates), candidate_refs)
        self.assertTrue(targets.isdisjoint(compact_paths), compact_paths)


def write_source(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def noisy_catalog(index: int) -> str:
    return f"""
export class ConfirmationNoise{index} {{
  report(): void {{
    const state = 'background verification success global confirmation components transfer pending signal interface'
  }}
}}
"""


def candidate_refs_by_table(context: dict) -> dict[str, list[dict]]:
    tables = context["query_audit"]["candidate_recall"]["tables"]
    return {
        table_name: [
            item for item in table.get("candidate_refs", [])
            if item.get("file_path")
        ]
        for table_name, table in tables.items()
    }


if __name__ == "__main__":
    unittest.main()
