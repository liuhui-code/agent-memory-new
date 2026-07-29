from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.benchmark_workspace import materialized_workspace


class BenchmarkWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="benchmark-workspace-test-")
        self.root = Path(self.temp.name) / "source"
        (self.root / "src").mkdir(parents=True)
        (self.root / "src" / "Base.ets").write_text("base", encoding="utf-8")
        group = self.root / ".benchmark-fixtures" / "event-identity" / "src"
        group.mkdir(parents=True)
        (group / "Event.ets").write_text("event", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_default_workspace_excludes_case_fixture_sources(self) -> None:
        with materialized_workspace(self.root, working_tree_case()) as workspace:
            self.assertTrue((workspace / "src" / "Base.ets").is_file())
            self.assertFalse((workspace / ".benchmark-fixtures").exists())
            self.assertFalse((workspace / "src" / "Event.ets").exists())

    def test_declared_fixture_group_is_overlaid_at_project_paths(self) -> None:
        case = working_tree_case("event-identity")

        with materialized_workspace(self.root, case) as workspace:
            self.assertEqual(
                "event",
                (workspace / "src" / "Event.ets").read_text(encoding="utf-8"),
            )
            self.assertFalse((workspace / ".benchmark-fixtures").exists())

    def test_fixture_group_cannot_overwrite_common_source(self) -> None:
        group = self.root / ".benchmark-fixtures" / "conflict" / "src"
        group.mkdir(parents=True)
        (group / "Base.ets").write_text("replacement", encoding="utf-8")

        with self.assertRaisesRegex(SystemExit, "cannot overwrite source"):
            with materialized_workspace(self.root, working_tree_case("conflict")):
                pass

    def test_fixture_group_rejects_revision_source(self) -> None:
        case = {"source": {"before_revision": "abc123", "fixture_group": "event-identity"}}

        with self.assertRaisesRegex(SystemExit, "requires a working-tree source"):
            with materialized_workspace(self.root, case):
                pass


def working_tree_case(group: str = "") -> dict:
    source = {"before_revision": "working-tree"}
    if group:
        source["fixture_group"] = group
    return {"source": source}


if __name__ == "__main__":
    unittest.main()
