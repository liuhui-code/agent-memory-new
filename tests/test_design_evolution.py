# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase, REPO_ROOT


class DesignEvolutionTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "design-evolution"
        self.project.mkdir()
        self.write_project()
        self.run_memory(self.project, "init")
        self.run_memory(self.project, "learn-path", "--path", ".", "--json")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_project(self) -> None:
        files = {
            "pages/ProfilePage.ets": """
import { ProfileCard } from '../components/ProfileCard'
import { ProfileService } from '../service/ProfileService'
@Entry
@Component
struct ProfilePage {
  @State profileName: string = ''
  private service: ProfileService = new ProfileService()
  handleSave(): void { this.profileName = this.profileName + '!' }
  refresh(): void { this.handleSave() }
  build() {
    Column() {
      ProfileCard({ onSave: this.handleSave })
      Button('Save').onClick(this.handleSave)
    }
  }
}
""",
            "components/ProfileCard.ets": """
@Component
export struct ProfileCard {
  @Event onSave: () => void
  build() { Button('Save').onClick(() => this.onSave()) }
}
""",
            "service/ProfileService.ets": """
export class ProfileService {
  load(): void { console.info('profile.load result=ok') }
}
""",
            "tests/ProfileServiceTest.ets": "export class ProfileServiceTest {}\n",
        }
        for relative, content in files.items():
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content.strip() + "\n", encoding="utf-8")

    def write_json(self, name: str, value: dict) -> Path:
        path = self.project / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def contract(self) -> dict:
        return {
            "schema_version": "design-contract/v1",
            "id": "profile-contract",
            "goal": "Improve profile state design",
            "constraints": ["keep ProfileService API compatible"],
            "quality_scenarios": [{
                "id": "mod-state",
                "attribute": "modifiability",
                "stimulus": "add a profile state",
                "environment": "normal development",
                "artifact": "profile state owner",
                "response": "change one state owner",
                "measure": "no service API changes",
                "priority": "high",
            }],
        }

    def proposal(self, candidate_id: str, risky: bool = False) -> dict:
        edges = []
        modified = ["file:pages/ProfilePage.ets"]
        if risky:
            modified.append("file:service/ProfileService.ets")
            edges.append({
                "source": "file:service/ProfileService.ets",
                "relation": "imports",
                "target": "file:pages/ProfilePage.ets",
            })
        return {
            "schema_version": "design-delta/v1",
            "id": candidate_id,
            "contract_id": "profile-contract",
            "goal": "Improve profile state design",
            "anchors": ["file:pages/ProfilePage.ets"],
            "add_nodes": [],
            "modify_nodes": modified,
            "add_edges": edges,
            "remove_edges": [],
            "assumptions": [],
            "invariants": ["ProfilePage remains the state owner"],
            "constraint_coverage": ["keep ProfileService API compatible"],
            "quality_coverage": ["mod-state"],
            "verification": {"tests": ["profile state test"], "observability": []},
        }

    def test_versioned_contract_and_custom_rule_are_evaluated(self) -> None:
        rules = {
            "schema_version": "design-rules/v1",
            "rules": [{
                "id": "service-no-ui",
                "kind": "forbid_edge",
                "severity": "error",
                "source_layer": "service",
                "target_layer": "ui",
                "rationale": "service must not depend on UI",
            }],
        }
        result = self.run_memory(
            self.project, "design-check",
            "--proposal", str(self.write_json("risky.json", self.proposal("risky", True))),
            "--contract", str(self.write_json("contract.json", self.contract())),
            "--rules", str(self.write_json("rules.json", rules)), "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual("design-evaluation/v1", payload["schema_version"])
        self.assertEqual("blocked", payload["status"])
        self.assertIn("rule:service-no-ui", {item["code"] for item in payload["errors"]})
        self.assertTrue(payload["quality_scenarios"][0]["covered"])

    def test_compare_hard_gates_before_change_size(self) -> None:
        good = self.write_json("good.json", self.proposal("good"))
        risky = self.write_json("small-risky.json", self.proposal("risky", True))
        contract = self.write_json("contract.json", self.contract())
        result = self.run_memory(
            self.project, "design-compare", "--proposal", str(risky), "--proposal", str(good),
            "--contract", str(contract), "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual("good", payload["recommended_candidate"])
        self.assertTrue(payload["audit"]["architecture_reused"])
        risky_summary = next(item for item in payload["candidates"] if item["candidate_id"] == "risky")
        self.assertGreater(risky_summary["hard_violations"], 0)

    def test_arkts_edges_expose_evidence_class_and_semantics(self) -> None:
        result = self.run_memory(
            self.project, "evidence-context", "--goal", "design",
            "--query", "Profile page state callback API", "--json",
        )
        architecture = json.loads(result.stdout)["architecture_slice"]
        relations = {edge["relation"] for edge in architecture["edges"]}

        self.assertTrue({"calls", "reads_state", "writes_state", "exposes_api", "consumes_api"} <= relations)
        self.assertTrue(all(edge["evidence_class"] in {"exact", "static", "heuristic", "inferred"} for edge in architecture["edges"]))
        extractors = {edge["extractor_version"].split("/", 1)[0] for edge in architecture["edges"]}
        self.assertIn("code-wiki:v4", extractors)
        self.assertIn("semantic-index:v1", extractors)

    def test_verify_reports_plan_to_diff_drift(self) -> None:
        proposal = self.write_json("good.json", self.proposal("good"))
        result = self.run_memory(
            self.project, "design-verify", "--proposal", str(proposal),
            "--contract", str(self.write_json("contract.json", self.contract())),
            "--files", "service/ProfileService.ets", "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual("replan", payload["status"])
        self.assertEqual(["pages/ProfilePage.ets"], payload["missing_planned_files"])
        self.assertEqual(["service/ProfileService.ets"], payload["unexpected_files"])
        self.assertEqual(0.0, payload["metrics"]["planned_file_recall"])

    def test_design_eval_case_pack(self) -> None:
        pack = {
            "schema_version": "design-eval-cases/v1",
            "cases": [{
                "id": "cycle-preference",
                "contract": self.contract(),
                "proposals": [self.proposal("good"), self.proposal("risky", True)],
                "expected_findings": {"risky": ["dependency_cycle"]},
                "expected_recommended": "good",
                "actual_files": ["pages/ProfilePage.ets"],
                "executed_tests": ["profile state test"],
                "expected_verify_status": "aligned",
            }],
        }
        result = self.run_memory(
            self.project, "eval-design", "--cases", str(self.write_json("cases.json", pack)), "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual("pass", payload["status"])
        self.assertEqual(1.0, payload["metrics"]["finding_recall"])
        self.assertEqual(1.0, payload["metrics"]["candidate_preference_accuracy"])

    def test_seeded_arkts_design_catalog_passes(self) -> None:
        result = self.run_memory(
            self.project, "eval-design", "--cases", str(REPO_ROOT / "docs/eval/design-cases.json"), "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual("pass", payload["status"])
        self.assertEqual(11, payload["metrics"]["case_count"])
        self.assertEqual(1.0, payload["metrics"]["finding_recall"])
        self.assertEqual("pass", payload["quality_gate"]["status"])
        self.assertEqual(1, payload["metric_coverage"]["candidate_preference_accuracy"]["sample_count"])
        self.assertEqual(1, payload["metric_coverage"]["planned_file_recall"]["sample_count"])


if __name__ == "__main__":
    import unittest

    unittest.main()
