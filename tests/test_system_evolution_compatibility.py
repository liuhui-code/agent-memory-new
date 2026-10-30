# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Actual Git-baseline ordinary reader/writer against a governance-v2 archive."""

import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_system_evolution import synthetic_report


BASELINE_REVISION = "2ade686f12373c214d7b9c3809f0e8821d770944"


class SystemEvolutionCompatibilityTests(AgentMemoryTestBase):
    def test_git_baseline_query_and_writer_work_after_governance_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(__file__).resolve().parents[1]
            old = Path(directory) / "git-baseline"
            old.mkdir()
            env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_LAZY_FETCH="1")
            # Keep the pre-meta reader after delivery advances the repository HEAD.
            archive = subprocess.check_output(["git", "-c", "protocol.allow=never", "archive", "--format=tar", BASELINE_REVISION, "tools"], cwd=repository, env=env)
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as package:
                for member in package.getmembers():
                    path = old / member.name
                    path.resolve().relative_to(old.resolve())
                    if member.isdir():
                        path.mkdir(parents=True, exist_ok=True)
                    else:
                        self.assertTrue(member.isfile(), "Baseline package contains an unsupported link/special file.")
                        path.parent.mkdir(parents=True, exist_ok=True)
                        with package.extractfile(member) as source:
                            path.write_bytes(source.read())
            root = Path(directory) / "project"
            root.mkdir()
            self.run_memory(root, "init")
            self.run_memory(root, "update", "--type", "semantic", "--fact", "Synthetic cross-version compatibility fact before upgrade.")
            before = json.loads(self.run_memory(root, "context", "--query", "cross-version compatibility", "--compact", "--json").stdout)
            self.run_memory(root, "reflect-system", "--review-key", "cross-version-review", "--payload", json.dumps(synthetic_report()), "--json")
            self.run_memory(root, "maintain-system-migrate", "--target-version", "system-evolution-v2", "--backup-file",
                            str(Path(directory) / "before-v2.db"), "--execute", "--json")
            old_runtime = old / "tools/agent_memory.py"
            def baseline(*args):
                return subprocess.run([sys.executable, str(old_runtime), *args, "--project", str(root), "--memory-home", str(self.memory_home(root))],
                                      text=True, capture_output=True, check=True)
            old_output = json.loads(baseline("context", "--query", "cross-version compatibility", "--compact", "--json").stdout)
            current = json.loads(self.run_memory(root, "context", "--query", "cross-version compatibility", "--compact", "--json").stdout)
            self.assertTrue(current["query_handoff"]["semantic_refs"])
            self.assertEqual(before["query_handoff"], current["query_handoff"])
            self.assertEqual(old_output["query_handoff"], current["query_handoff"])
            self.assertEqual(set(old_output), set(current))
            baseline("update", "--type", "semantic", "--fact", "Synthetic cross-version compatibility fact written by the Git baseline after upgrade.")
            self.assertEqual(2, len(self.list_records(root, "semantic")))
            old_after = json.loads(baseline("context", "--query", "cross-version compatibility", "--compact", "--json").stdout)
            current_after = json.loads(self.run_memory(root, "context", "--query", "cross-version compatibility", "--compact", "--json").stdout)
            self.assertEqual(old_after["query_handoff"], current_after["query_handoff"])
