# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase, REPO_ROOT
from tools.agent_memory_runtime.design_check import load_proposal
from tools.agent_memory_runtime.goal_planner import build_goal_plan


class RepositoryDesignTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "design-demo"
        self.project.mkdir()
        self.write_arkts_project()
        self.run_memory(self.project, "init")
        self.run_memory(self.project, "learn-path", "--path", ".", "--json")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_arkts_project(self) -> None:
        files = {
            "pages/ProfilePage.ets": """
import { ProfileCard } from '../components/ProfileCard'
import { ProfileService } from '../service/ProfileService'
@Entry
@Component
struct ProfilePage {
  @State profileName: string = ''
  private service: ProfileService = new ProfileService()
  handleSave(): void {}
  build() {
    Column() {
      ProfileCard({ onSave: this.handleSave })
    }
  }
}
""",
            "components/ProfileCard.ets": """
@Component
export struct ProfileCard {
  @Event onSave: () => void
  build() {
    Button('Save').onClick(() => this.onSave())
  }
}
""",
            "service/ProfileService.ets": """
export class ProfileService {
  load(): void {
    console.info('profile.load result=ok')
  }
}
""",
            "ability/EntryAbility.ets": "export default class EntryAbility {}\n",
            "tests/ProfileServiceTest.ets": "export class ProfileServiceTest {}\n",
            "module.json5": '{"module":{"name":"entry","abilities":[{"name":"EntryAbility"}]}}\n',
        }
        for relative, content in files.items():
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content.strip() + "\n", encoding="utf-8")

    def proposal_file(self, payload: dict) -> Path:
        path = self.project / "proposal.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def base_proposal(self) -> dict:
        return {
            "goal": "Improve profile loading design",
            "anchors": ["file:pages/ProfilePage.ets"],
            "add_nodes": [],
            "modify_nodes": ["file:pages/ProfilePage.ets"],
            "add_edges": [],
            "remove_edges": [],
            "assumptions": [],
            "invariants": ["ProfilePage remains the only owner of profileName"],
        }

    def test_design_goal_is_code_and_graph_first(self) -> None:
        plan = build_goal_plan("设计 Profile 缓存和状态流方案")

        self.assertEqual("design", plan.goal)
        self.assertEqual(1.0, plan.source_weights["code"])
        self.assertEqual(1.0, plan.source_weights["edge"])
        self.assertLess(plan.source_weights["reflection"], plan.source_weights["semantic"])
        self.assertLessEqual(len(plan.subqueries), 3)
        self.assertEqual("local", build_goal_plan("design the overall architecture").query_scope)

    def test_learning_extracts_arkts_design_edges(self) -> None:
        edges = self.list_records(self.project, "memory-edge")
        relations = {edge["relation"] for edge in edges}

        self.assertTrue(
            {"defines_state", "renders_component", "uses_service", "dispatches_event",
             "handles_event", "configured_by", "tested_by"} <= relations
        )
        static_edges = [edge for edge in edges if not edge["extractor_version"].startswith("semantic-index:")]
        self.assertTrue(all(edge["extractor_version"] == "code-wiki:v4" for edge in static_edges))

    def test_design_context_contains_bounded_architecture_slice(self) -> None:
        result = self.run_memory(
            self.project,
            "evidence-context",
            "--goal",
            "design",
            "--query",
            "Profile page service state design",
            "--json",
        )
        payload = json.loads(result.stdout)
        architecture = payload["architecture_slice"]
        relations = {edge["relation"] for edge in architecture["edges"]}

        self.assertEqual("design", payload["goal_plan"]["goal"])
        self.assertIn("file:pages/ProfilePage.ets", architecture["entry_points"])
        self.assertIn("uses_service", relations)
        self.assertIn("renders_component", relations)
        self.assertLessEqual(architecture["audit"]["node_count"], 80)
        self.assertLessEqual(architecture["audit"]["edge_count"], 160)
        self.assertLessEqual(architecture["audit"]["max_depth"], 2)

    def test_design_check_blocks_cycle_and_multiple_state_owners(self) -> None:
        proposal = self.base_proposal()
        proposal["modify_nodes"].append("file:service/ProfileService.ets")
        proposal["add_edges"] = [
            {
                "source": "file:service/ProfileService.ets",
                "relation": "imports",
                "target": "file:pages/ProfilePage.ets",
            },
            {
                "source": "file:service/ProfileService.ets",
                "relation": "owns_state",
                "target": "symbol:pages/ProfilePage.ets::profileName",
            },
        ]
        result = self.run_memory(
            self.project,
            "design-check",
            "--proposal",
            str(self.proposal_file(proposal)),
            "--json",
        )
        payload = json.loads(result.stdout)
        codes = {item["code"] for item in payload["errors"]}

        self.assertEqual("blocked", payload["status"])
        self.assertIn("dependency_cycle", codes)
        self.assertIn("multiple_state_owners", codes)
        self.assertFalse(payload["audit"]["persisted"])
        self.assertFalse(payload["audit"]["llm_used"])

    def test_design_check_accepts_a_bounded_clean_proposal(self) -> None:
        result = self.run_memory(
            self.project,
            "design-check",
            "--proposal",
            str(self.proposal_file(self.base_proposal())),
            "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual("clean", payload["status"])
        self.assertEqual([], payload["errors"])
        self.assertEqual([], payload["warnings"])

    def test_design_check_rejects_invalid_proposal_shape(self) -> None:
        path = self.proposal_file({"goal": "Bad proposal", "add_nodes": {"id": "new:x"}})

        with self.assertRaisesRegex(SystemExit, "field must be a list: add_nodes"):
            load_proposal(path)

    def test_query_skill_uses_one_level_progressive_disclosure(self) -> None:
        skill = REPO_ROOT / "skills" / "agent-memory-query" / "SKILL.md"
        lines = skill.read_text(encoding="utf-8").splitlines()
        references = skill.parent / "references"

        self.assertLessEqual(len(lines), 120)
        self.assertEqual(
            {"evidence-policy.md", "code-understanding.md", "incident-diagnosis.md",
             "change-impact.md", "code-design.md"},
            {path.name for path in references.glob("*.md")},
        )
        self.assertNotIn("Delta Graph", skill.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import unittest

    unittest.main()
