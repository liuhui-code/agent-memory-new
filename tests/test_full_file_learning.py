# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.ecma_braces import block_end
from tools.agent_memory_runtime.storage import connect, resolve_project


FEATURE_SOURCE = """export class ParserFeature {
  parsePayload(): void {
    const payload = '{\"terminal\": \"}\"}'
    console.info(payload)
  }

  trailingOperation(): void {
    console.info('trailing operation')
  }
}
"""


class FullFileLearningTests(AgentMemoryTestBase):
    def test_block_end_ignores_braces_in_literals_and_comments(self) -> None:
        lines = [
            "export function inspect(): void {",
            "  const payload = '{\\\"terminal\\\": \\\"}\\\"}'",
            "  const apostrophe = 'it\\'s still literal }'",
            "  const label = `literal { and }`",
            "  /* comment { spans",
            "     more comment } */",
            "  // trailing } comment",
            "}",
            "export function after(): void {}",
        ]

        self.assertEqual(7, block_end(lines, 0))

    def test_learn_path_indexes_members_after_brace_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.create_project(Path(directory))

            self.run_memory(project, "learn-path", "--path", ".")

            self.assert_semantic_member_is_complete(project)

    def test_learn_entry_indexes_imported_members_after_brace_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.create_project(Path(directory))
            (project / "Entry.ets").write_text(
                "import { ParserFeature } from './ParserFeature';\n"
                "export function openFeature(): void {\n"
                "  new ParserFeature().trailingOperation()\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-entry", "--entry", "Entry.ets", "--depth", "1")

            self.assert_semantic_member_is_complete(project)

    def create_project(self, root: Path) -> Path:
        project = root / "source"
        project.mkdir()
        (project / "ParserFeature.ets").write_text(FEATURE_SOURCE, encoding="utf-8")
        return project

    def assert_semantic_member_is_complete(self, project: Path) -> None:
        runtime_project = resolve_project(str(project), str(self.memory_home(project)))
        with connect(runtime_project) as conn:
            row = conn.execute(
                "SELECT start_line, end_line, semantic_adapter FROM code_symbols "
                "WHERE project_id = ? AND file_path = 'ParserFeature.ets' "
                "AND symbol = 'trailingOperation'",
                (runtime_project.project_id,),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(7, row["start_line"])
        self.assertEqual(9, row["end_line"])
        self.assertEqual("arkts-static@1.1", row["semantic_adapter"])


if __name__ == "__main__":
    import unittest

    unittest.main()
