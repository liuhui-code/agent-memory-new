# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class DesignAssistTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "design-assist"
        self.project.mkdir()
        self._write_project()
        self.run_memory(self.project, "init")
        self.run_memory(self.project, "learn-path", "--path", ".", "--json")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_project(self) -> None:
        files = {
            "pages/ProfilePage.ets": """
import { ProfileService } from '../service/ProfileService'
@Entry
@Component
struct ProfilePage {
  private service: ProfileService = new ProfileService()
  build() { Button('Load').onClick(() => this.service.load()) }
}
""",
            "service/ProfileService.ets": """
import { ProfileRepository } from '../data/ProfileRepository'
export class ProfileService {
  private repository: ProfileRepository = new ProfileRepository()
  load(): string { return this.repository.load() }
}
""",
            "data/ProfileRepository.ets": """
export class ProfileRepository {
  load(): string { console.info('profile.repository.load result=ok'); return 'Ada' }
}
""",
            "tests/ProfileServiceTest.ets": "export class ProfileServiceTest {}\n",
        }
        for relative, content in files.items():
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content.strip() + "\n", encoding="utf-8")

    def _write_json(self, name: str, value: dict) -> Path:
        path = self.project / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_natural_language_entry_returns_compact_design_workbench(self) -> None:
        result = self.run_memory(
            self.project,
            "design-assist",
            "--query", "为 ProfileRepository 设计缓存并保持 ProfileService API 兼容",
            "--mode", "design-and-implement",
            "--scope", "data/ProfileRepository.ets",
            "--constraint", "logout clears profile cache",
            "--json",
        )
        payload = json.loads(result.stdout)
        guidance = payload["design_guidance"]

        self.assertEqual("design-assist/v1", payload["schema_version"])
        self.assertEqual("design-and-implement", payload["mode"])
        self.assertEqual(["data/ProfileRepository.ets"], payload["intent"]["scope"])
        self.assertTrue(payload["audit"]["natural_language_entry"])
        self.assertTrue(payload["audit"]["inferred_acceptance_criteria"])
        self.assertEqual("design-delta/v2", payload["candidate_template"]["schema_version"])
        self.assertGreaterEqual(payload["current_design"]["snapshot"]["graph_revision"], 1)
        self.assertIn(
            "file:data/ProfileRepository.ets",
            payload["current_design"]["baseline_entry_points"],
        )
        self.assertIn(
            "cache_aside",
            {item["id"] for item in guidance["pattern_candidates"]},
        )
        self.assertIn(
            "repository_boundary",
            {item["id"] for item in guidance["existing_patterns"]},
        )
        self.assertIn(
            "information_hiding",
            {item["id"] for item in guidance["principle_checks"]},
        )
        self.assertIn("cache owner", guidance["required_decisions"])
        self.assertIn(
            "run design-check before implementation and design-verify after tests",
            payload["interaction"]["next_steps"],
        )
        self.assertNotIn("repository_model", payload)
        self.assertNotIn("architecture_slice", payload)

    def test_prepare_exposes_same_guidance_without_forcing_a_pattern(self) -> None:
        neutral_intent = {
            "schema_version": "design-intent/v1",
            "id": "rename-helper",
            "goal": "Rename a private formatting helper",
            "scope": ["service/ProfileService.ets"],
            "exclusions": [],
            "acceptance_criteria": ["existing behavior remains unchanged"],
            "constraints": [],
            "open_questions": [],
        }
        result = self.run_memory(
            self.project,
            "design-prepare",
            "--intent", str(self._write_json("intent.json", neutral_intent)),
            "--json",
        )
        payload = json.loads(result.stdout)
        guidance = payload["design_guidance"]

        self.assertEqual("design-guidance/v1", guidance["schema_version"])
        self.assertEqual([], guidance["pattern_candidates"])
        self.assertTrue(guidance["pattern_policy"]["prefer_no_pattern_over_forced_pattern"])
        self.assertIn(
            "smallest_viable_design",
            {item["id"] for item in guidance["principle_checks"]},
        )

    def test_strong_consistency_marks_cache_pattern_as_caution(self) -> None:
        result = self.run_memory(
            self.project,
            "design-assist",
            "--query", "为资料读取增加缓存，但要求强一致",
            "--json",
        )
        payload = json.loads(result.stdout)
        cache = next(
            item for item in payload["design_guidance"]["pattern_candidates"]
            if item["id"] == "cache_aside"
        )

        self.assertEqual("caution", cache["status"])
        self.assertEqual(["strong consistency"], cache["contraindications"])
