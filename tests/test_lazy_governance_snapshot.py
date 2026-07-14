# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class LazyGovernanceSnapshotTests(AgentMemoryTestBase):
    def test_all_known_lanes_support_focused_execution(self) -> None:
        lanes = (
            "active_learning", "auto_reflection", "experience_conflict",
            "experience_staleness", "experience_usage", "graph_quality",
            "incident_recurrence", "incident_trace", "learn_semantic_repair",
            "log_diagnosis", "memory_hygiene", "memory_quality", "memory_tiers",
            "quality_gate", "retrieval_interference", "runtime_performance",
            "semantic_conflict", "skill_evolution",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            for lane in lanes:
                with self.subTest(lane=lane):
                    data = json.loads(
                        self.run_memory(
                            project,
                            "maintain-plan",
                            "--compact",
                            "--action-lane",
                            lane,
                            "--json",
                        ).stdout
                    )
                    self.assertEqual("focused", data["execution_scope"]["mode"])
                    self.assertEqual(lane, data["execution_scope"]["selected_lane"])
                    self.assertTrue(data["execution_scope"]["computed_groups"])
                    self.assertTrue(all(
                        action["governance_lane"] == lane for action in data["actions"]
                    ))

    def test_unknown_lane_preserves_full_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            data = json.loads(
                self.run_memory(
                    project,
                    "maintain-plan",
                    "--compact",
                    "--action-lane",
                    "typo_lane",
                    "--json",
                ).stdout
            )

        self.assertEqual("full_fallback", data["execution_scope"]["mode"])
        self.assertTrue(data["execution_scope"]["full_archive_summary"])
        self.assertEqual("no_matches", data["action_budget"]["lane_filter_status"])

    def test_known_action_lane_executes_only_declared_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(project, "init")
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "legacy profile behavior",
                "--confidence",
                "0.2",
            )

            data = json.loads(
                self.run_memory(
                    project,
                    "maintain-plan",
                    "--compact",
                    "--action-lane",
                    "memory_tiers",
                    "--json",
                ).stdout
            )

        self.assertEqual("focused", data["execution_scope"]["mode"])
        self.assertEqual("memory_tiers", data["execution_scope"]["selected_lane"])
        self.assertEqual(["memory_tiers"], data["execution_scope"]["computed_groups"])
        self.assertTrue(data["actions"])
        self.assertTrue(
            all(action["governance_lane"] == "memory_tiers" for action in data["actions"])
        )
        self.assertNotIn("graph_quality", data["execution_scope"]["computed_groups"])

    def test_graph_quality_snapshot_tracks_graph_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            source = project / "src" / "Profile.ets"
            source.parent.mkdir(parents=True)
            source.write_text("export class Profile { load(): void {} }\n", encoding="utf-8")
            self.run_memory(project, "init")
            self.run_memory(project, "learn-path", "--path", "src", "--json")

            first = json.loads(self.run_memory(project, "maintain-health", "--json").stdout)
            second = json.loads(self.run_memory(project, "maintain-health", "--json").stdout)
            first_quality = first["graph_quality"]
            second_quality = second["graph_quality"]

            self.assertEqual("recomputed", first_quality["snapshot_status"])
            self.assertEqual("hit", second_quality["snapshot_status"])
            self.assertEqual(first_quality["graph_revision"], second_quality["graph_revision"])
            self.assertEqual(first_quality["graph_revision"], first_quality["quality_revision"])

            source.write_text(
                "export class Profile { load(): void {} save(): void {} }\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", "src", "--json")
            refreshed = json.loads(self.run_memory(project, "maintain-health", "--json").stdout)
            refreshed_quality = refreshed["graph_quality"]

            self.assertEqual("recomputed", refreshed_quality["snapshot_status"])
            self.assertGreater(refreshed_quality["graph_revision"], first_quality["graph_revision"])

            verified = json.loads(
                self.run_memory(
                    project,
                    "maintain-health",
                    "--verify-graph-quality",
                    "--json",
                ).stdout
            )

        self.assertEqual("verified", verified["graph_quality"]["snapshot_status"])
        self.assertEqual(
            refreshed_quality["graph_revision"],
            verified["graph_quality"]["graph_revision"],
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
