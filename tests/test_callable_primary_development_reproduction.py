# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class CallablePrimaryDevelopmentReproductionTests(AgentMemoryTestBase):
    """Controlled reproduction for path-token false owner identity."""

    def test_path_token_cannot_override_exact_callable_in_public_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "callable-primary-development"
            root.mkdir()
            write_source(root / "src/classes/resource-provider.ts", """
export class DiagnosticProviderImpl {
  getArktsDiagnostics(resourceValue: string): string {
    if (resourceValue.startsWith('sys') || resourceValue.startsWith('app')) {
      return 'valid resource scope'
    }
    return 'Invalid resource scope'
  }
}
""")
            write_source(root / "src/interfaces/resource.ts", """
export class Resource {
  getProduct(): string {
    return 'resource metadata'
  }
}
""")
            self.run_memory(root, "learn-path", "--path", ".", "--json")
            full_payload = json.loads(self.run_memory(
                root,
                "context",
                "--query",
                "resource-provider getArktsDiagnostics Invalid resource scope sys app",
                "--json",
            ).stdout)
            payload = json.loads(self.run_memory(
                root,
                "context",
                "--compact",
                "--query",
                "resource-provider getArktsDiagnostics Invalid resource scope sys app",
                "--json",
            ).stdout)

        primary = payload["query_handoff"]["callable_evidence"]["primary"]
        self.assertEqual(
            "src/classes/resource-provider.ts",
            primary["file_path"],
            full_payload["query_audit"]["hierarchical_localization"]["callable_candidates"],
        )
        self.assertEqual("getArktsDiagnostics", primary["symbol"])


def write_source(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
