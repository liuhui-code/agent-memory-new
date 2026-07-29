# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_sufficiency import (
    diagnosis_sufficiency,
    impact_sufficiency,
)
from tools.agent_memory_runtime.context_sufficiency_metrics import sufficiency_profile


class ContextSufficiencyTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "sufficiency"
        self.project.mkdir()
        self.write_project()
        self.run_memory(self.project, "init")
        self.run_memory(self.project, "learn-path", "--path", ".", "--json")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_project(self) -> None:
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
  load(): string { console.error('profile.load.failed'); return '' }
}
""",
            "tests/ProfileServiceTest.ets": "export class ProfileServiceTest {}\n",
        }
        for relative, content in files.items():
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content.strip() + "\n", encoding="utf-8")

    def run_json(self, command: str, *args: str) -> dict[str, Any]:
        result = self.run_memory(self.project, command, *args, "--json")
        return json.loads(result.stdout)

    def test_context_reports_readiness_without_diagnosis(self) -> None:
        payload = self.run_json(
            "context", "--query", "profile.load.failed ProfileRepository", "--compact",
        )
        sufficiency = payload["sufficiency"]

        self.assertEqual("diagnosis", sufficiency["kind"])
        self.assertEqual("ready_for_agent_inspection", sufficiency["status"])
        self.assertTrue(sufficiency["coverage"]["source_locatable_code_anchor"])
        self.assertEqual("retrieval_readiness_only_not_agent_reasoning", sufficiency["scope"])
        self.assertNotIn("root_cause", json.dumps(sufficiency))

    def test_design_context_reports_orientation_readiness(self) -> None:
        payload = self.run_json(
            "design-context", "--query", "为 ProfileRepository 增加缓存并保持 API 兼容", "--compact",
        )
        sufficiency = payload["sufficiency"]

        self.assertEqual("design", sufficiency["kind"])
        self.assertEqual("ready_for_orientation", sufficiency["status"])
        self.assertGreater(sufficiency["coverage"]["repository_source_anchor_count"], 0)
        self.assertIn("Agent inspects source", sufficiency["agent_ownership"])

    def test_impact_scope_reports_verification_readiness(self) -> None:
        payload = self.run_json(
            "impact-scope", "--files", "service/ProfileService.ets", "--query", "profile loading change",
        )
        sufficiency = payload["sufficiency"]

        self.assertEqual("impact", sufficiency["kind"])
        self.assertEqual("ready_for_agent_verification", sufficiency["status"])
        self.assertEqual(1, sufficiency["coverage"]["learned_changed_file_count"])
        self.assertGreater(sufficiency["coverage"]["verification_check_count"], 0)

    def test_missing_or_stale_evidence_has_actionable_non_reasoning_status(self) -> None:
        missing = diagnosis_sufficiency({}, [], {})
        stale = diagnosis_sufficiency(
            {"code_anchors": [{"file_path": "service/ProfileService.ets"}]},
            [],
            {"status": "boundary_drift"},
        )

        self.assertEqual("insufficient_evidence", missing["status"])
        self.assertEqual("narrow_query_or_learn_relevant_scope", missing["next_action"])
        self.assertEqual("refresh_required", stale["status"])
        self.assertIn("source_freshness:boundary_drift", stale["reason_codes"])

    def test_impact_scope_requires_refresh_for_unlearned_change(self) -> None:
        result = impact_sufficiency({
            "impact_summary": {"unlearned_changed_files": ["new/Feature.ets"]},
            "evidence": {},
            "evidence_gaps": ["unlearned_changed_file"],
        })

        self.assertEqual("refresh_required", result["status"])
        self.assertEqual("learn_uncovered_changed_files", result["next_action"])
        self.assertIn("unlearned_changed_files", result["reason_codes"])

    def test_evaluation_profile_is_informational_not_a_context_gate(self) -> None:
        profile = sufficiency_profile([
            {"sufficiency": {"kind": "diagnosis", "status": "ready_for_agent_inspection"}},
            {"sufficiency": {"kind": "diagnosis", "status": "needs_focused_expansion", "reason_codes": ["no_source_locatable_code_anchor"]}},
            {},
        ])

        self.assertEqual("informational", profile["status"])
        self.assertEqual(2, profile["evaluated_case_count"])
        self.assertEqual(1, profile["missing_observation_count"])
        self.assertEqual(1, profile["readiness_status_counts"]["ready_for_agent_inspection"])
        self.assertEqual("shadow_observation_not_a_context_gate", profile["scope"])


if __name__ == "__main__":
    import unittest

    unittest.main()
