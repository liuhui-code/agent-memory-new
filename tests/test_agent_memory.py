import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"


class AgentMemoryRuntimeTests(unittest.TestCase):
    def run_memory(self, project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNTIME), *args, "--project", str(project)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

    def list_code_files(self, project: Path) -> set[str]:
        result = self.run_memory(
            project,
            "list",
            "--type",
            "code-file",
            "--json",
        )
        return {row["file_path"] for row in json.loads(result.stdout)}

    def test_learn_path_merges_index_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "a").mkdir()
            (project / "b").mkdir()
            (project / "a" / "one.py").write_text("def one():\n    return 1\n", encoding="utf-8")
            (project / "b" / "two.py").write_text("def two():\n    return 2\n", encoding="utf-8")

            self.run_memory(project, "learn-path", "--path", "a")
            self.run_memory(project, "learn-path", "--path", "b")

            self.assertEqual(self.list_code_files(project), {"a/one.py", "b/two.py"})

    def test_learn_path_replace_keeps_only_latest_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "a").mkdir()
            (project / "b").mkdir()
            (project / "a" / "one.py").write_text("def one():\n    return 1\n", encoding="utf-8")
            (project / "b" / "two.py").write_text("def two():\n    return 2\n", encoding="utf-8")

            self.run_memory(project, "learn-path", "--path", "a")
            self.run_memory(project, "learn-path", "--path", "b", "--replace")

            self.assertEqual(self.list_code_files(project), {"b/two.py"})


if __name__ == "__main__":
    unittest.main()
