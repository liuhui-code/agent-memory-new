from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class LocalizerProjectionDevelopmentReproductionTests(AgentMemoryTestBase):
    """Controlled baseline: a recalled file can be excluded by serving localization."""

    def test_recalled_status_surface_is_dropped_before_callable_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "localizer-projection-development"
            root.mkdir()
            target = "src/surface/ZStatusProjection.ets"
            write_source(root / target, """
export class ZStatusProjection {
  apply(signal: Signal): void {
    this.banner.show(signal)
  }
}
""")
            for index in range(4):
                write_source(root / f"src/surface/ConfirmationPanel{index}.ets", noisy_owner(index))
            for index in range(7):
                write_source(root / f"src/noise{index}/ConfirmationCatalog.ets", noisy_owner(index))
            self.run_memory(root, "learn-path", "--path", ".", "--json")
            indexed = json.loads(self.run_memory(
                root, "list", "--type", "code-file", "--limit", "300", "--json",
            ).stdout)
            context = json.loads(self.run_memory(
                root,
                "context",
                "--query",
                "An asynchronous result reaches the application but no global confirmation "
                "status appears. Locate the status surface owner.",
                "--json",
            ).stdout)
            compact = json.loads(self.run_memory(
                root,
                "context",
                "--compact",
                "--query",
                "An asynchronous result reaches the application but no global confirmation "
                "status appears. Locate the status surface owner.",
                "--json",
            ).stdout)

        audit = context["query_audit"]
        candidates = candidate_paths(audit)
        localized = {
            item["file_path"] for item in audit["hierarchical_localization"]["file_candidates"]
        }
        compact_paths = {item["file_path"] for item in compact["query_handoff"]["code_anchors"]}
        self.assertIn(target, {item["file_path"] for item in indexed})
        self.assertIn(target, candidates)
        self.assertNotIn(target, localized)
        self.assertNotIn(target, compact_paths)


def write_source(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def noisy_owner(index: int) -> str:
    return f"""
export class ConfirmationSurface{index} {{
  reportConfirmationStatus(): void {{
    const message = 'asynchronous result global confirmation status surface owner'
  }}
}}
"""


def candidate_paths(audit: dict) -> set[str]:
    tables = audit["candidate_recall"]["tables"]
    return {
        item["file_path"]
        for table in tables.values()
        for item in table.get("candidate_refs", [])
        if item.get("file_path")
    }


if __name__ == "__main__":
    unittest.main()
