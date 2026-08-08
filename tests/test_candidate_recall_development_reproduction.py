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
            write_source(root / "src/runtime/ZResultRelay.ets", """
export class ZResultRelay {
  forward(signal: Signal): void {
    this.sink.accept(signal)
  }
}
""")
            write_source(root / "src/ui/ZStatusSurface.ets", """
export class ZStatusSurface {
  accept(signal: Signal): void {
    this.banner.show(signal)
  }
}
""")
            write_source(root / "src/noise/ConfirmationCatalog.ets", noisy_catalog())
            self.run_memory(root, "learn-path", "--path", ".", "--json")
            indexed = json.loads(self.run_memory(
                root, "list", "--type", "code-file", "--limit", "300", "--json",
            ).stdout)

            full = json.loads(self.run_memory(
                root,
                "context",
                "--query",
                "A background verification succeeds but no global confirmation appears. "
                "Locate the result handoff and status display owners.",
                "--json",
            ).stdout)
            compact = json.loads(self.run_memory(
                root,
                "context",
                "--compact",
                "--query",
                "A background verification succeeds but no global confirmation appears. "
                "Locate the result handoff and status display owners.",
                "--json",
            ).stdout)

        candidates = candidate_paths(full)
        compact_paths = {
            item["file_path"] for item in compact["query_handoff"]["code_anchors"]
        }
        targets = {"src/runtime/ZResultRelay.ets", "src/ui/ZStatusSurface.ets"}
        self.assertTrue(targets <= {item["file_path"] for item in indexed})
        self.assertTrue(targets.isdisjoint(candidates), candidates)
        self.assertTrue(targets.isdisjoint(compact_paths), compact_paths)


def write_source(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def noisy_catalog() -> str:
    return "\n".join(
        "export class ConfirmationNoise" + str(index) + " {\n"
        "  report(): void {\n"
        "    const state = 'background verification success global confirmation status display'\n"
        "  }\n"
        "}\n"
        for index in range(260)
    )


def candidate_paths(context: dict) -> set[str]:
    tables = context["query_audit"]["candidate_recall"]["tables"]
    return {
        item["file_path"]
        for table in tables.values()
        for item in table.get("candidate_refs", [])
        if item.get("file_path")
    }


if __name__ == "__main__":
    unittest.main()
