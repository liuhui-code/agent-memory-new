# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"
PROJECT_FINGERPRINT = "sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77"


class AgentMemoryTestBase(unittest.TestCase):
    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

    def project_memory_dir(self, project: Path) -> Path:
        project_id = self.project_id(project)
        return self.memory_home(project) / "projects" / project_id

    def project_id(self, project: Path) -> str:
        import hashlib

        return hashlib.sha256(str(project.resolve()).encode("utf-8")).hexdigest()[:16]

    def run_memory(
        self,
        project: Path,
        *args: str,
        memory_home: Optional[Path] = None,
        use_memory_home_arg: bool = True,
        env: Optional[dict[str, str]] = None,
        cwd: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(RUNTIME), *args, "--project", str(project)]
        if use_memory_home_arg:
            command.extend(["--memory-home", str(memory_home or self.memory_home(project))])
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        return subprocess.run(
            command,
            cwd=cwd or REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
            env=process_env,
        )

    def list_code_files(self, project: Path, memory_home: Optional[Path] = None) -> set[str]:
        result = self.run_memory(
            project,
            "list",
            "--type",
            "code-file",
            "--json",
            memory_home=memory_home,
        )
        return {row["file_path"] for row in json.loads(result.stdout)}

    def list_records(self, project: Path, kind: str, memory_home: Optional[Path] = None) -> list[dict]:
        result = self.run_memory(
            project,
            "list",
            "--type",
            kind,
            "--json",
            memory_home=memory_home,
        )
        return json.loads(result.stdout)

    def miss_list(self, project: Path, memory_home: Optional[Path] = None) -> list[dict]:
        result = self.run_memory(project, "miss-list", "--json", memory_home=memory_home)
        return json.loads(result.stdout)

    def usage_sample_path(self, project: Path) -> Path:
        return self.project_memory_dir(project) / "runtime" / "last_usage_sample.json"
