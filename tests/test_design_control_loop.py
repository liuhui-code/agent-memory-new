# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class DesignControlLoopTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "design-loop"
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
  @State name: string = ''
  private service: ProfileService = new ProfileService()
  refresh(): void { this.name = this.service.load() }
  build() { Button('Refresh').onClick(() => this.refresh()) }
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

    def _contract(self) -> dict:
        return {
            "schema_version": "design-contract/v2",
            "id": "profile-cache",
            "intent_id": "profile-cache-intent",
            "goal": "Add a profile repository cache",
            "constraints": ["preserve ProfileService.load API"],
            "quality_scenarios": [{
                "id": "cache-observable",
                "attribute": "observability",
                "stimulus": "cache lookup completes",
                "environment": "normal runtime",
                "artifact": "profile repository",
                "response": "emit cache result",
                "measure": "one result signal per lookup",
                "priority": "high",
                "evidence_requirements": ["delta", "verification"],
            }],
        }

    def _proposal(self, candidate_id: str, supported: bool = True) -> dict:
        proposal = {
            "schema_version": "design-delta/v2",
            "id": candidate_id,
            "contract_id": "profile-cache",
            "goal": "Add a profile repository cache",
            "anchors": ["file:data/ProfileRepository.ets"],
            "add_nodes": [{
                "id": "new:ProfileCache",
                "kind": "cache",
                "file_path": "data/ProfileCache.ets",
            }],
            "modify_nodes": ["symbol:data/ProfileRepository.ets::ProfileRepository.load"],
            "add_edges": [{
                "source": "symbol:data/ProfileRepository.ets::ProfileRepository.load",
                "relation": "uses_service",
                "target": "new:ProfileCache",
            }],
            "remove_edges": [],
            "assumptions": [],
            "invariants": ["ProfileService.load signature remains compatible"],
            "constraint_coverage": ["preserve ProfileService.load API"],
            "quality_coverage": ["cache-observable"],
            "verification": {
                "tests": ["profile cache test"],
                "observability": ["cache result signal"],
            },
        }
        if supported:
            proposal["coverage_evidence"] = [{
                "target_type": "scenario",
                "target_id": "cache-observable",
                "delta_refs": ["new:ProfileCache"],
                "repository_refs": ["file:data/ProfileRepository.ets"],
                "verification_refs": ["cache result signal"],
            }]
        return proposal

    def test_baseline_is_revision_bound_and_not_candidate_limited(self) -> None:
        intent = {
            "schema_version": "design-intent/v1",
            "id": "profile-cache-intent",
            "goal": "Add a profile repository cache",
            "scope": ["service/ProfileService.ets"],
            "exclusions": ["pages/ProfilePage.ets"],
            "acceptance_criteria": ["cache result is observable"],
            "constraints": [],
            "open_questions": ["cache lifetime"],
        }
        result = self.run_memory(
            self.project, "design-check",
            "--proposal", str(self._write_json("candidate.json", self._proposal("candidate"))),
            "--contract", str(self._write_json("contract.json", self._contract())),
            "--intent", str(self._write_json("intent.json", intent)), "--json",
        )
        payload = json.loads(result.stdout)
        model = payload["repository_model"]

        self.assertEqual("repository-model/v2", model["schema_version"])
        self.assertGreaterEqual(model["snapshot"]["graph_revision"], 1)
        self.assertIn("behavior", model["capabilities"])
        self.assertIn("ownership", model["views"])
        self.assertNotIn("architecture", model)
        self.assertIn("file:service/ProfileService.ets", model["baseline_entry_points"])
        self.assertIn("file:data/ProfileRepository.ets", model["scope_entry_points"])
        self.assertEqual(model["snapshot"]["graph_revision"], payload["baseline_revision"])
        self.assertEqual(["pages/ProfilePage.ets"], payload["synthesis_brief"]["exclusions"])
        self.assertTrue(payload["synthesis_brief"]["candidate_policy"]["smallest_viable_first"])

    def test_coverage_distinguishes_claimed_supported_and_verification_ready(self) -> None:
        result = self.run_memory(
            self.project, "design-check",
            "--proposal", str(self._write_json("supported.json", self._proposal("supported"))),
            "--contract", str(self._write_json("contract.json", self._contract())), "--json",
        )
        scenario = json.loads(result.stdout)["quality_scenarios"][0]

        self.assertEqual("supported", scenario["coverage_state"])
        self.assertEqual(["new:ProfileCache"], scenario["delta_refs"])
        self.assertTrue(scenario["verification_ready"])

        claimed = self.run_memory(
            self.project, "design-check",
            "--proposal", str(self._write_json("claimed.json", self._proposal("claimed", False))),
            "--contract", str(self._write_json("contract.json", self._contract())), "--json",
        )
        claimed_payload = json.loads(claimed.stdout)
        self.assertEqual("claimed", claimed_payload["quality_scenarios"][0]["coverage_state"])
        self.assertIn("unsupported_coverage_claim", {item["code"] for item in claimed_payload["warnings"]})

    def test_comparison_uses_supported_coverage_and_exposes_dimensions(self) -> None:
        result = self.run_memory(
            self.project, "design-compare",
            "--proposal", str(self._write_json("claimed.json", self._proposal("claimed", False))),
            "--proposal", str(self._write_json("supported.json", self._proposal("supported"))),
            "--contract", str(self._write_json("contract.json", self._contract())), "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual("supported", payload["recommended_candidate"])
        winner = next(item for item in payload["candidates"] if item["candidate_id"] == "supported")
        self.assertEqual(1, winner["supported_quality_scenarios"])
        self.assertIn("compatibility", winner["dimensions"])
        self.assertEqual("design-decision/v1", payload["decision"]["schema_version"])
        self.assertTrue(payload["audit"]["architecture_reused"])
        self.assertTrue(all("repository_model" not in item for item in payload["evaluations"]))

    def test_evaluation_builds_bounded_change_plan_dag(self) -> None:
        result = self.run_memory(
            self.project, "design-check",
            "--proposal", str(self._write_json("candidate.json", self._proposal("candidate"))),
            "--contract", str(self._write_json("contract.json", self._contract())), "--json",
        )
        plan = json.loads(result.stdout)["change_plan"]

        self.assertEqual("change-plan/v1", plan["schema_version"])
        self.assertEqual("ready", plan["status"])
        self.assertLessEqual(len(plan["steps"]), 200)
        self.assertTrue(all({"id", "target", "depends_on", "expected_delta", "verification"} <= set(step) for step in plan["steps"]))
        self.assertEqual(plan["steps"], sorted(plan["steps"], key=lambda item: item["order"]))
        self.assertIn("test:profile cache test", {step["target"] for step in plan["steps"]})
        self.assertIn("observe:cache result signal", {step["target"] for step in plan["steps"]})

    def test_verify_accepts_symbol_and_structured_test_evidence(self) -> None:
        test_evidence = {
            "schema_version": "test-evidence/v1",
            "tests": [{
                "command": "profile cache test",
                "status": "passed",
                "exit_code": 0,
                "summary": "1 passed",
                "verifies": ["cache result signal"],
            }],
        }
        result = self.run_memory(
            self.project, "design-verify",
            "--proposal", str(self._write_json("candidate.json", self._proposal("candidate"))),
            "--contract", str(self._write_json("contract.json", self._contract())),
            "--files", "data/ProfileRepository.ets,data/ProfileCache.ets",
            "--actual-symbols", "symbol:data/ProfileRepository.ets::ProfileRepository.load",
            "--test-evidence", str(self._write_json("test-evidence.json", test_evidence)), "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual(1.0, payload["metrics"]["planned_symbol_recall"])
        self.assertEqual(0, payload["metrics"]["failed_test_count"])
        self.assertEqual("verified", payload["quality_scenarios"][0]["coverage_state"])
        self.assertIn("structured_tests", payload["verification_capabilities"])

    def test_design_outcome_persists_only_compact_metrics(self) -> None:
        verification = {
            "schema_version": "design-verification/v2",
            "project_id": "ignored",
            "candidate_id": "candidate",
            "contract_id": "profile-cache",
            "status": "aligned",
            "metrics": {
                "planned_file_recall": 1.0,
                "unplanned_file_ratio": 0.0,
                "planned_symbol_recall": 1.0,
                "scenario_verification_rate": 1.0,
                "failed_test_count": 0,
            },
            "verification": {"replan_triggers": []},
            "raw_diff": "must not persist",
        }
        result = self.run_memory(
            self.project, "design-outcome",
            "--verification", str(self._write_json("verification.json", verification)),
            "--outcome", "success", "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual("design-outcome/v1", payload["schema_version"])
        self.assertNotIn("raw_diff", payload)
        health = json.loads(self.run_memory(self.project, "maintain-health", "--json").stdout)
        self.assertEqual(1, health["design_calibration"]["outcome_count"])
        self.assertEqual(1.0, health["design_calibration"]["average_planned_symbol_recall"])


if __name__ == "__main__":
    import unittest

    unittest.main()
