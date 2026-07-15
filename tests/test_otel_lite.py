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


class OtelLiteTests(unittest.TestCase):
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

    def test_runtime_event_to_otel_lite_maps_core_fields(self) -> None:
        from tools.agent_memory_runtime.otel_lite import runtime_event_to_otel_lite
        from tools.agent_memory_runtime.runtime_log_parsing import normalize_runtime_log_line

        event = normalize_runtime_log_line(
            "07-11 12:00:00.100 EntryAbility E ProfilePage: [ProfileLoad] stage=failed route=pages/Profile request_id=req-1 session_id=sess-1 reason=session_invalid code=401 result=failed",
            1,
        )
        otel = runtime_event_to_otel_lite(event)

        self.assertEqual("ERROR", otel["severity_text"])
        self.assertEqual("EntryAbility", otel["resource"]["process.name"])
        self.assertEqual("ProfilePage", otel["attributes"]["logger.name"])
        self.assertEqual("req-1", otel["attributes"]["request.id"])
        self.assertEqual("sess-1", otel["attributes"]["session.id"])
        self.assertEqual("401", otel["attributes"]["error.code"])
        self.assertEqual("session_invalid", otel["attributes"]["error.reason"])

if __name__ == "__main__":
    unittest.main()
