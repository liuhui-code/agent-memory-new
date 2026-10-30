# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Actual isolated installed Runtime/Skill file updates and code rollback."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests import test_system_evolution_lifecycle as lifecycle


class SystemEvolutionDeliveryTests(AgentMemoryTestBase):
    git = lifecycle.SystemEvolutionLifecycleTests.git
    command = lifecycle.SystemEvolutionLifecycleTests.command
    failed = lifecycle.SystemEvolutionLifecycleTests.failed
    candidate = lifecycle.SystemEvolutionLifecycleTests.candidate
    base_fixture = lifecycle.SystemEvolutionLifecycleTests.base_fixture
    fixture = lifecycle.SystemEvolutionLifecycleTests.fixture
    accept = lifecycle.SystemEvolutionLifecycleTests.accept

    def test_installed_layout_updates_real_runtime_and_skill_then_restores_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(__file__).resolve().parents[1]
            names = ["skills/agent-memory-query/SKILL.md", "tools/agent_memory_runtime/system_evolution_contract.py"]
            self.baseline_files = {name: (repository / name).read_text(encoding="utf-8") for name in names}
            self.candidate_files = {name: contents + ("\n<!-- synthetic delivery marker -->\n" if name.endswith(".md") else "\n# synthetic delivery marker\n")
                                    for name, contents in self.baseline_files.items()}
            root, recovery, change, candidate = self.fixture(directory)
            self.accept(root, change)
            target = Path(directory) / "installed-project"
            target.mkdir()
            memory_home = target / ".agent-memory"
            subprocess.run([sys.executable, str(repository / "install.py"), "--project", str(target), "--memory-home", str(memory_home)],
                           check=True, capture_output=True)
            runtime = target / "tools/agent_memory.py"
            def installed(*args):
                return subprocess.run([sys.executable, str(runtime), *args, "--project", str(target), "--memory-home", str(memory_home)],
                                      check=True, text=True, capture_output=True)
            installed("update", "--type", "semantic", "--fact", "Synthetic installed compatibility fact before delivery.")
            (target / "value.txt").write_text("Unrelated user file; do not replace.\n", encoding="utf-8")
            result = self.command(root, "maintain-system-apply", "--id", str(change["id"]), "--expected-revision", "4",
                                  "--operation-key", "deliver-installed", "--target-root", str(target), "--recovery-home", str(recovery),
                                  "--layout", "installed", "--execute")
            self.assertTrue(result["application_performed"])
            self.assertEqual(3, len(result["operation"]["request"]["skipped_delivery_paths"]))
            for name in names:
                mapped = ".agents/" + name if name.startswith("skills/") else name
                self.assertEqual(self.candidate_files[name], (target / mapped).read_text(encoding="utf-8"))
            installed("update", "--type", "semantic", "--fact", "Synthetic installed compatibility fact after delivery.")
            output = json.loads(installed("context", "--query", "installed compatibility", "--compact", "--json").stdout)
            self.assertTrue(output["query_handoff"]["semantic_refs"])
            self.command(root, "maintain-system-rollback", "--id", str(change["id"]), "--expected-revision", "5",
                         "--operation-key", "restore-installed", "--application-key", "deliver-installed", "--execute")
            for name in names:
                mapped = ".agents/" + name if name.startswith("skills/") else name
                self.assertEqual(self.baseline_files[name], (target / mapped).read_text(encoding="utf-8"))
            self.assertEqual(2, len(json.loads(installed("list", "--type", "semantic", "--json").stdout)))
            self.assertEqual("Unrelated user file; do not replace.\n", (target / "value.txt").read_text())
