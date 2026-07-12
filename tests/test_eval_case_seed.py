# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"


class EvalCaseSeedTests(unittest.TestCase):
    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

    def run_memory(
        self,
        project: Path,
        *args: str,
        memory_home: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(RUNTIME), *args, "--project", str(project)]
        command.extend(["--memory-home", str(memory_home or self.memory_home(project))])
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
            env=os.environ.copy(),
        )

    def test_eval_seed_cases_writes_safe_example_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            target = Path(temp_dir) / "docs" / "eval" / "examples"
            project.mkdir()

            result = self.run_memory(project, "eval-seed-cases", "--target", str(target), "--json")
            data = json.loads(result.stdout)

            self.assertEqual(str(target), data["target"])
            self.assertEqual(8, len(data["written"]))
            self.assertTrue((target / "README.md").exists())
            for name in [
                "golden-retrieval.json",
                "golden-calibration.json",
                "golden-experience-evidence.json",
                "golden-governance.json",
                "golden-log-signal.json",
                "golden-graph-signal.json",
                "golden-evidence-attribution.json",
            ]:
                content = json.loads((target / name).read_text(encoding="utf-8"))
                self.assertIsInstance(content, list)
                self.assertGreaterEqual(len(content), 1)

    def test_eval_seed_cases_skips_existing_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            target = Path(temp_dir) / "examples"
            project.mkdir()
            target.mkdir()
            existing = target / "golden-retrieval.json"
            existing.write_text('[{"name":"custom"}]', encoding="utf-8")

            result = self.run_memory(project, "eval-seed-cases", "--target", str(target), "--json")
            data = json.loads(result.stdout)

            self.assertIn(str(existing), data["skipped"])
            self.assertEqual([{"name": "custom"}], json.loads(existing.read_text(encoding="utf-8")))

    def test_eval_seed_cases_force_overwrites_existing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            target = Path(temp_dir) / "examples"
            project.mkdir()
            target.mkdir()
            existing = target / "golden-retrieval.json"
            existing.write_text('[{"name":"custom"}]', encoding="utf-8")

            result = self.run_memory(project, "eval-seed-cases", "--target", str(target), "--force", "--json")
            data = json.loads(result.stdout)

            self.assertIn(str(existing), data["written"])
            content = json.loads(existing.read_text(encoding="utf-8"))
            self.assertNotEqual([{"name": "custom"}], content)


if __name__ == "__main__":
    unittest.main()
