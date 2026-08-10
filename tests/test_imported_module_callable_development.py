# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.storage import connect, resolve_project


class ImportedModuleCallableDevelopmentTests(AgentMemoryTestBase):
    def test_imported_arrow_callable_creates_a_cross_file_call_edge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "module-call-development"
            root.mkdir()
            write_source(root / "src/proto_guard.ets", """
export const hasOwnKey = (obj: Object, key: string): boolean => {
  return Object.keys(obj).indexOf(key) !== -1
}
""")
            write_source(root / "src/parser.ets", """
import { hasOwnKey } from './proto_guard'
export const parseQuery = (obj: Object): boolean => {
  return hasOwnKey(obj, 'profile')
}
""")
            self.run_memory(root, "learn-path", "--path", ".", "--json")
            project = resolve_project(str(root), str(self.memory_home(root)))
            with connect(project) as conn:
                edge = conn.execute(
                    """
                    SELECT source.qualified_name AS source_name, target.qualified_name AS target_name
                    FROM memory_edges edge
                    JOIN code_symbols source ON source.id = edge.source_id
                    JOIN code_symbols target ON target.id = edge.target_id
                    WHERE edge.project_id = ? AND edge.valid_to IS NULL AND edge.relation = 'calls'
                    """,
                    (project.project_id,),
                ).fetchone()

        self.assertIsNotNone(edge)
        assert edge is not None
        self.assertEqual("parseQuery", edge["source_name"])
        self.assertEqual("hasOwnKey", edge["target_name"])


def write_source(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
