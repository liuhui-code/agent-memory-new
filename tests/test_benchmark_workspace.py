# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

        with patch(
            "tools.agent_memory_runtime.benchmark_workspace.git_archive",
            return_value=True,
        ):
            with self.assertRaisesRegex(SystemExit, "requires a working-tree source"):
                with materialized_workspace(self.root, case):
                    pass

    def test_revision_archive_failure_does_not_fall_back_to_working_tree(self) -> None:
        case = {"source": {"before_revision": "abc123"}}

        with patch(
            "tools.agent_memory_runtime.benchmark_workspace.git_archive",
            return_value=False,
        ), patch(
            "tools.agent_memory_runtime.benchmark_workspace.copy_working_tree"
        ) as copy:
            with self.assertRaisesRegex(
                SystemExit,
                "failed to materialize immutable benchmark revision: abc123",
            ):
                with materialized_workspace(self.root, case):
                    pass

        copy.assert_not_called()

    def test_revision_workspace_is_archived_from_frozen_source(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "src/Base.ets"], cwd=self.root, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Benchmark",
                "-c",
                "user.email=benchmark@example.invalid",
                "commit",
                "-qm",
                "freeze source",
            ],
            cwd=self.root,
            check=True,
        )
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        (self.root / "src" / "Base.ets").write_text("working tree", encoding="utf-8")

        with materialized_workspace(
            self.root,
            {"source": {"before_revision": revision}},
        ) as workspace:
            self.assertEqual(
                "base",
                (workspace / "src" / "Base.ets").read_text(encoding="utf-8"),
            )

    def test_revision_omits_external_symlink_and_audits_it(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        external = self.root / "src" / "External.ets"
        external.symlink_to("/private/unavailable/External.ets")
        subprocess.run(["git", "add", "src"], cwd=self.root, check=True)
        subprocess.run(
            [
                "git", "-c", "user.name=Benchmark",
                "-c", "user.email=benchmark@example.invalid",
                "commit", "-qm", "freeze external link",
            ],
            cwd=self.root,
            check=True,
        )
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True,
            capture_output=True, check=True,
        ).stdout.strip()

        with materialized_workspace(
            self.root, {"source": {"before_revision": revision}},
        ) as workspace:
            self.assertFalse((workspace / "src" / "External.ets").exists())
            report = json.loads(
                (workspace / ".agent-benchmark-sanitization.json").read_text()
            )
            self.assertEqual(["src/External.ets"], report["omitted_external_symlinks"])

    def test_working_tree_omits_external_but_preserves_internal_symlink(self) -> None:
        (self.root / "src" / "Internal.ets").symlink_to("Base.ets")
        (self.root / "src" / "External.ets").symlink_to("/private/unavailable/External.ets")

        with materialized_workspace(self.root, working_tree_case()) as workspace:
            self.assertTrue((workspace / "src" / "Internal.ets").is_symlink())
            self.assertFalse((workspace / "src" / "External.ets").exists())


def working_tree_case(group: str = "") -> dict:
    source = {"before_revision": "working-tree"}
    if group:
        source["fixture_group"] = group
    return {"source": source}


if __name__ == "__main__":
    unittest.main()
