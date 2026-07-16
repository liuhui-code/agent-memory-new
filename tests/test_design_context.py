# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens


FORBIDDEN_DECISION_KEYS = {
    "candidate_template",
    "change_plan",
    "design_guidance",
    "pattern_candidates",
    "recommended_design",
    "selected_candidate",
}


class DesignContextTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "design-context"
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
  load(): string { console.info('profile.repository.load result=ok'); return 'Ada' }
}
""",
            "tests/ProfileServiceTest.ets": "export class ProfileServiceTest {}\n",
        }
        for relative, content in files.items():
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content.strip() + "\n", encoding="utf-8")

    def context(self, *args: str) -> dict[str, Any]:
        result = self.run_memory(
            self.project,
            "design-context",
            "--query", "为 ProfileRepository 增加缓存并保持 ProfileService API 兼容",
            *args,
            "--json",
        )
        return json.loads(result.stdout)

    def test_orientation_returns_context_without_runtime_design_decisions(self) -> None:
        payload = self.context()

        self.assertEqual("design-context/v1", payload["schema_version"])
        self.assertEqual("orientation", payload["request"]["query_stage"])
        self.assertTrue(payload["audit"]["decision_free"])
        self.assertIn("cache_aside", {item["id"] for item in payload["design_knowledge"]})
        self.assertIn("compatibility", {
            item["concern"] for item in payload["quality_context"]["routing_hints"]
        })
        self.assertFalse(FORBIDDEN_DECISION_KEYS & recursive_keys(payload))
        for item in payload["design_knowledge"]:
            self.assertTrue(item["preconditions"])
            self.assertTrue(item["tradeoffs"])
            self.assertTrue(item.get("questions") or item.get("question"))
            self.assertTrue(item.get("provenance") or item.get("source_ref"))

    def test_agent_directed_concern_and_anchor_refine_second_pass(self) -> None:
        payload = self.context(
            "--concern", "reliability",
            "--anchor", "data/ProfileRepository.ets",
        )

        self.assertEqual("agent_directed_expansion", payload["request"]["query_stage"])
        self.assertEqual(["reliability"], payload["request"]["explicit_concerns"])
        self.assertIn(
            "file:data/ProfileRepository.ets",
            payload["current_repository"]["entry_points"],
        )
        reliability = next(
            item for item in payload["quality_context"]["routing_hints"]
            if item["concern"] == "reliability"
        )
        self.assertEqual("agent_explicit", reliability["origin"])

    def test_explicit_constraint_has_highest_context_authority(self) -> None:
        payload = self.context(
            "--constraint", "logout must invalidate all profile cache entries",
            "--constraint", "timeout recovery must remain observable",
        )
        constraint = payload["project_context"]["task_constraints"][0]

        self.assertEqual("current_task_constraint", constraint["authority"])
        self.assertEqual("current_task_constraint", payload["authority_order"][0])
        self.assertEqual("general_advisory_knowledge", payload["design_knowledge"][0]["authority"])
        self.assertIn("Agent must inspect current source", payload["current_repository"]["applicability"])
        reliability = next(
            item for item in payload["quality_context"]["routing_hints"]
            if item["concern"] == "reliability"
        )
        self.assertEqual("lexical_routing_hint", reliability["origin"])

    def test_compact_context_is_bounded(self) -> None:
        payload = self.context("--compact")

        self.assertTrue(payload["audit"]["compact"])
        self.assertLessEqual(len(payload["current_repository"]["source_anchors"]), 12)
        self.assertLessEqual(len(payload["current_repository"]["relations"]), 16)
        self.assertLessEqual(len(payload["design_knowledge"]), 2)
        self.assertLessEqual(estimate_payload_tokens(payload), 1500)

    def test_semantic_correction_is_a_guardrail_not_a_design_decision(self) -> None:
        correction = {
            "experience_type": "correction_experience",
            "task": "Correct ProfileRepository cache ownership",
            "summary": "ProfileRepository owns profile data access in current source.",
            "lesson": "Do not move ProfileRepository cache state into ProfilePage.",
            "trigger_condition": "designing profile repository cache ownership",
            "repair_action": "inspect ProfileRepository and its current consumers",
            "anti_pattern": "letting the page own repository cache state",
            "verification_method": "inspected current ProfileRepository source",
            "source_cases": ["file:data/ProfileRepository.ets"],
            "does_not_apply_to": "view-local immutable formatting values",
            "confidence": 0.9,
        }
        self.run_memory(
            self.project,
            "reflect",
            "--payload", json.dumps(correction, ensure_ascii=False),
        )

        payload = self.context()
        guards = payload["project_context"]["semantic_corrections"]

        self.assertTrue(guards)
        self.assertEqual("project_semantic_correction", guards[0]["authority"])
        self.assertEqual("requires_current_source_confirmation", guards[0]["verification_state"])
        self.assertIn("guardrail only", guards[0]["applicability"])
        self.assertFalse(FORBIDDEN_DECISION_KEYS & recursive_keys(guards))

    def test_legacy_design_assist_remains_callable(self) -> None:
        result = self.run_memory(
            self.project,
            "design-assist",
            "--query", "rename a private helper",
            "--json",
        )
        self.assertEqual("design-assist/v1", json.loads(result.stdout)["schema_version"])


def recursive_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in recursive_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in recursive_keys(child)}
    return set()
