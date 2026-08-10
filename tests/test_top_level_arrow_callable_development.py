# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class TopLevelArrowCallableDevelopmentTests(AgentMemoryTestBase):
    """Controlled reproduction for exported ArkTS arrow callable extraction."""

    def test_exported_arrow_callable_is_indexed_and_selected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "top-level-arrow-development"
            root.mkdir()
            write_source(root / "src/proto_guard.ets", """
export const hasOwnKey = (obj: Object, key: string): boolean => {
  return Object.keys(obj).indexOf(key) !== -1
}
""")
            write_source(root / "src/side_channel.ets", """
export class SideChannel {
  has(key: Object): boolean {
    return key !== undefined
  }
}
""")
            self.run_memory(root, "learn-path", "--path", ".", "--json")
            symbols = self.list_records(root, "code-symbol")
            payload = json.loads(self.run_memory(
                root,
                "context",
                "--compact",
                "--query",
                "hasOwnKey Object.keys query string performance",
                "--json",
            ).stdout)

        indexed = [
            row for row in symbols
            if row["file_path"] == "src/proto_guard.ets" and row["symbol"] == "hasOwnKey"
        ]
        self.assertEqual(1, len(indexed))
        self.assertEqual("function", indexed[0]["symbol_type"])
        primary = payload["query_handoff"]["callable_evidence"]["primary"]
        self.assertEqual("src/proto_guard.ets", primary["file_path"])
        self.assertEqual("hasOwnKey", primary["symbol"])


def write_source(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
