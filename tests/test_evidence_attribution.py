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


class EvidenceAttributionTests(unittest.TestCase):
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

    def test_eval_evidence_attribution_reports_unsupported_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            (project / "pages").mkdir()
            (project / "pages" / "Profile.ets").write_text(
                "struct ProfilePage {\n"
                "  open() { router.pushUrl({ url: 'pages/Profile' }); }\n"
                "}\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", "pages")
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "ArkTS route blank screen diagnosis should compare router.pushUrl target with page registration.",
                "--source",
                "test",
                "--evidence",
                "pages/Profile.ets",
            )
            cases = Path(temp_dir) / "evidence-cases.json"
            cases.write_text(
                json.dumps(
                    [
                        {
                            "name": "route evidence",
                            "query": "ArkTS route blank screen router.pushUrl pages/Profile",
                            "claims": [
                                "router.pushUrl target pages/Profile should match page registration",
                                "payment timeout is the root cause",
                            ],
                            "min_grounded_rate": 0.5,
                            "max_unsupported_claims": 1,
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = self.run_memory(project, "eval-evidence-attribution", "--cases", str(cases), "--json")
            data = json.loads(result.stdout)

        self.assertEqual("pass", data["quality_gate"])
        self.assertEqual(0.5, data["summary"]["grounded_claim_rate"])
        self.assertEqual(1, data["summary"]["unsupported_claims"])
        self.assertEqual("grounded", data["cases"][0]["claims"][0]["support_band"])
        self.assertEqual("unsupported", data["cases"][0]["claims"][1]["support_band"])


if __name__ == "__main__":
    unittest.main()
