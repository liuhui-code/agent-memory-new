# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase, REPO_ROOT, RUNTIME


class CausalDiagnosisTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "demo"
        self.project.mkdir()
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_context_handoff_assigns_causal_reasoning_to_agent(self) -> None:
        payload = json.loads(self.run_memory(
            self.project,
            "context",
            "--query",
            "why does profile load fail",
            "--json",
        ).stdout)

        boundary = payload["query_handoff"]["role_boundary"]
        self.assertFalse(boundary["runtime_reads_temporary_logs"])
        self.assertFalse(boundary["runtime_builds_causal_chains"])
        self.assertIn("infer call/causal chains", boundary["agent_cli"])
        self.assertNotIn("evidence_chains", payload)

    def test_removed_reasoning_heavy_commands_are_not_public(self) -> None:
        for command in ("evidence-context", "analyze-runtime-log"):
            process = subprocess.run(
                [sys.executable, str(RUNTIME), command, "--project", str(self.project)],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, process.returncode)
            self.assertIn("invalid choice", process.stderr)
