# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class DesignProgressTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "design-progress"
        self.project.mkdir()
        source = self.project / "data/ProfileRepository.ets"
        source.parent.mkdir()
        source.write_text(
            "export class ProfileRepository {\n"
            "  load(): string { return 'Ada' }\n"
            "}\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=self.project, check=True)
        subprocess.run(["git", "add", "."], cwd=self.project, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Agent Memory Tests", "-c", "user.email=tests@example.invalid",
             "commit", "-qm", "baseline"],
            cwd=self.project,
            check=True,
        )
        self.run_memory(self.project, "init")
        self.run_memory(self.project, "learn-path", "--path", ".", "--json")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_json(self, name: str, value: dict) -> Path:
        path = self.project / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def proposal(self) -> dict:
        return {
            "schema_version": "design-delta/v1",
            "id": "profile-cache",
            "goal": "Add profile cache",
            "anchors": ["file:data/ProfileRepository.ets"],
            "add_nodes": [{"id": "new:ProfileCache", "kind": "service", "file_path": "data/ProfileCache.ets"}],
            "modify_nodes": ["symbol:data/ProfileRepository.ets::ProfileRepository.load"],
            "add_edges": [],
            "remove_edges": [],
            "assumptions": [],
            "invariants": ["load returns a profile"],
            "verification": {
                "tests": ["profile cache test"],
                "observability": ["cache result signal"],
            },
        }

    def test_progress_reconstructs_steps_and_accepts_explicit_review_completion(self) -> None:
        (self.project / "data/ProfileCache.ets").write_text(
            "export class ProfileCache { get(): string { return 'Ada' } }\n",
            encoding="utf-8",
        )
        (self.project / "data/ProfileRepository.ets").write_text(
            "import { ProfileCache } from './ProfileCache'\n"
            "export class ProfileRepository {\n"
            "  private cache: ProfileCache = new ProfileCache()\n"
            "  load(): string { return this.cache.get() }\n"
            "}\n",
            encoding="utf-8",
        )
        proposal = self.write_json("proposal.json", self.proposal())
        result = self.run_memory(
            self.project, "design-progress", "--proposal", str(proposal),
            "--base", "HEAD", "--executed-tests", "profile cache test", "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual("design-progress/v1", payload["schema_version"])
        self.assertEqual("active", payload["status"])
        self.assertEqual(3, payload["counts"]["completed"], payload["steps"])
        self.assertEqual("observe:cache result signal", payload["next_steps"][0]["target"])
        self.assertFalse(payload["audit"]["persisted"])

        completed = self.run_memory(
            self.project, "design-progress", "--proposal", str(proposal),
            "--base", "HEAD", "--executed-tests", "profile cache test",
            "--completed-step", payload["next_steps"][0]["id"], "--json",
        )
        completed_payload = json.loads(completed.stdout)
        self.assertEqual("complete", completed_payload["status"])
        self.assertEqual([], completed_payload["next_steps"])

        with self.assertRaises(subprocess.CalledProcessError):
            self.run_memory(
                self.project, "design-progress", "--proposal", str(proposal),
                "--base", "HEAD", "--completed-step", "step-001", "--json",
            )

    def test_stale_revision_and_failed_report_block_incomplete_steps(self) -> None:
        proposal = self.proposal()
        proposal["schema_version"] = "design-delta/v2"
        proposal["baseline_revision"] = 999_999
        report = self.write_json("failed-report.json", {
            "tests": [{"nodeid": "tests/test_profile.py::test_cache", "outcome": "failed"}],
        })
        result = self.run_memory(
            self.project, "design-progress",
            "--proposal", str(self.write_json("stale-proposal.json", proposal)),
            "--base", "HEAD", "--test-report", str(report), "--json",
        )
        payload = json.loads(result.stdout)
        codes = {item["code"] for item in payload["blockers"]}

        self.assertEqual("blocked", payload["status"])
        self.assertIn("baseline_revision_mismatch", codes)
        self.assertIn("test_failure", codes)
        self.assertGreater(payload["counts"]["blocked"], 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
