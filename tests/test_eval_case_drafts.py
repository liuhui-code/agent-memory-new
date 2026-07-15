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


class EvalCaseDraftTests(unittest.TestCase):
    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

    def runtime_dir(self, project: Path) -> Path:
        matches = list((self.memory_home(project) / "projects").glob("*/runtime"))
        if not matches:
            raise AssertionError("runtime directory not found")
        return matches[0]

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

    def test_eval_draft_cases_writes_query_miss_retrieval_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            target = Path(temp_dir) / "drafts"
            project.mkdir()
            self.run_memory(project, "context", "--query", "missing profile anchor", "--json")

            result = self.run_memory(project, "eval-draft-cases", "--target", str(target), "--json")
            data = json.loads(result.stdout)
            retrieval = json.loads((target / "golden-retrieval.draft.json").read_text(encoding="utf-8"))
            readme_exists = (target / "README.md").exists()

        self.assertEqual(1, data["draft_counts"]["golden-retrieval.draft.json"])
        self.assertEqual("missing profile anchor", retrieval[0]["query"])
        self.assertEqual("query_miss", retrieval[0]["draft_source"]["kind"])
        self.assertTrue(readme_exists)

    def test_eval_draft_cases_writes_evidence_draft_without_runtime_log_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            target = Path(temp_dir) / "drafts"
            project.mkdir()
            self.run_memory(project, "context", "--query", "profile failed", "--json")
            runtime = self.runtime_dir(project)
            trace = {
                "sample_id": "trace-1",
                "queries": ["profile failed"],
                "auto_summary": "profile failed needs grounding",
                "auto_summary_quality": {"missing_fields": ["evidence", "verification_method"]},
                "reflection_payload_template": {
                    "problem": "profile failed",
                    "reasoning_summary": "profile failure claim needs evidence",
                },
            }
            (runtime / "last_task_trace.json").write_text(json.dumps(trace), encoding="utf-8")

            result = self.run_memory(project, "eval-draft-cases", "--target", str(target), "--json")
            data = json.loads(result.stdout)
            evidence_cases = json.loads((target / "golden-evidence-attribution.draft.json").read_text(encoding="utf-8"))
            log_draft_exists = (target / "golden-log-signal.draft.json").exists()

        self.assertNotIn("golden-log-signal.draft.json", data["draft_counts"])
        self.assertFalse(log_draft_exists)
        self.assertEqual(1, data["draft_counts"]["golden-evidence-attribution.draft.json"])
        self.assertEqual(["profile failure claim needs evidence"], evidence_cases[0]["claims"])


if __name__ == "__main__":
    unittest.main()
