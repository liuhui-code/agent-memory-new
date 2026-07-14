# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase, REPO_ROOT


PROVIDER = REPO_ROOT / "tests" / "fixtures" / "exact_semantic_provider.py"


class SemanticEvaluationTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "eval-project"
        self.project.mkdir()
        PROVIDER.chmod(0o755)
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_pack(self, value: dict) -> Path:
        path = self.project / "semantic-cases.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_checked_in_static_golden_pack_passes(self) -> None:
        result = self.run_memory(
            self.project, "eval-semantic", "--mode", "static",
            "--cases", str(REPO_ROOT / "docs" / "eval" / "semantic-cases.json"), "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual("semantic-eval-result/v1", payload["schema_version"])
        self.assertEqual("pass", payload["status"])
        self.assertEqual(1.0, payload["metrics"]["expected_relation_recall"])
        self.assertEqual(0.0, payload["metrics"]["forbidden_edge_rate"])
        self.assertFalse(payload["audit"]["persisted"])

    def test_external_evaluation_compares_with_static_baseline(self) -> None:
        pack = {
            "schema_version": "semantic-eval-cases/v1",
            "cases": [{
                "id": "external-local-call",
                "language": "ArkTS",
                "minimum_evidence_class": "exact",
                "files": {"src/Demo.ets": "export class Demo {\n  helper(): void {}\n  run(): void { this.helper() }\n}"},
                "expected": [{"source": "Demo.run", "relation": "calls", "target": "Demo.helper"}],
                "forbidden": [],
            }],
        }
        result = self.run_memory(
            self.project, "eval-semantic", "--mode", "external",
            "--cases", str(self.write_pack(pack)), "--json",
            env={"AGENT_MEMORY_SEMANTIC_PROVIDER_ARKTS": str(PROVIDER)},
        )
        payload = json.loads(result.stdout)

        self.assertEqual("pass", payload["status"])
        self.assertEqual("external", payload["cases"][0]["provider"]["selected"])
        self.assertGreaterEqual(payload["metrics"]["common_relations"], 1)

    def test_invalid_case_schema_fails(self) -> None:
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_memory(
                self.project, "eval-semantic", "--cases",
                str(self.write_pack({"schema_version": "semantic-eval-cases/v2", "cases": []})),
                "--json",
            )


if __name__ == "__main__":
    import unittest

    unittest.main()
