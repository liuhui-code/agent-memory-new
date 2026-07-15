# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.evidence_fusion import fuse_evidence
from tools.agent_memory_runtime.evidence_models import EvidenceItem
from tools.agent_memory_runtime.goal_planner import build_goal_plan
from tools.agent_memory_runtime.impact_scope import paths_from_diff


class EvidenceFabricUnitTests(AgentMemoryTestBase):
    def test_diff_paths_include_deleted_and_renamed_files(self) -> None:
        diff = """diff --git a/src/Old.ets b/src/New.ets
--- a/src/Old.ets
+++ b/src/New.ets
diff --git a/src/Deleted.ets b/src/Deleted.ets
--- a/src/Deleted.ets
+++ /dev/null
"""

        self.assertEqual(
            ["src/Old.ets", "src/New.ets", "src/Deleted.ets"],
            paths_from_diff(diff),
        )

    def test_goal_planner_prefers_diagnosis_lanes_for_log_symptom(self) -> None:
        plan = build_goal_plan("个人中心空白，日志显示 profile load failed")

        self.assertEqual("diagnosis", plan.goal)
        self.assertEqual("incident", plan.retrieval_lanes[0])
        self.assertIn("log", plan.retrieval_lanes[:2])

    def test_current_code_outranks_lexically_strong_advisory_experience(self) -> None:
        plan = build_goal_plan("修改 ProfileService 的影响", "change_impact")
        code = EvidenceItem(
            evidence_id="code_file:1",
            source="code",
            kind="code_file",
            record_id=1,
            title="ProfileService.ets",
            summary="Current source",
            location="src/ProfileService.ets",
            authority="current_source",
            original_score=5.0,
        )
        experience = EvidenceItem(
            evidence_id="reflection:1",
            source="reflection",
            kind="reflection",
            record_id=1,
            title="Old profile lesson",
            summary="Historical advice",
            location=None,
            authority="advisory_memory",
            original_score=500.0,
            raw={"confidence": 1.0},
        )

        ranked = fuse_evidence([experience, code], plan)

        self.assertEqual("code_file:1", ranked[0].evidence_id)
        self.assertGreater(ranked[0].final_score, ranked[1].final_score)


class EvidenceFabricCliTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "demo"
        self.project.mkdir()
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _seed_code_graph(self) -> None:
        db_path = self.project_memory_dir(self.project) / "memory.db"
        project_id = self.project_id(self.project)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO code_files(
                  project_id, file_path, summary, language, business_summary,
                  business_terms, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    "src/ProfileService.ets",
                    "Loads user profile",
                    "ArkTS",
                    "个人资料加载服务",
                    '["个人中心", "profile"]',
                    "2026-07-13T00:00:00Z",
                ),
            )
            service_id = int(cursor.lastrowid)
            cursor = conn.execute(
                """
                INSERT INTO code_files(
                  project_id, file_path, summary, language, business_summary,
                  business_terms, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    "src/ProfilePage.ets",
                    "Displays user profile",
                    "ArkTS",
                    "个人中心页面",
                    '["个人中心", "profile"]',
                    "2026-07-13T00:00:00Z",
                ),
            )
            page_id = int(cursor.lastrowid)
            conn.execute(
                """
                INSERT INTO memory_edges(
                  project_id, source_type, source_id, relation, target_type,
                  target_id, evidence, confidence, created_at
                ) VALUES (?, 'code_file', ?, 'imports', 'code_file', ?, ?, 0.9, ?)
                """,
                (
                    project_id,
                    page_id,
                    service_id,
                    "src/ProfilePage.ets -> src/ProfileService.ets",
                    "2026-07-13T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO code_log_statements(
                  project_id, file_path, line, function, level, logger,
                  message_template, business_event, symptom_terms, likely_causes,
                  updated_at
                ) VALUES (?, ?, 42, 'loadProfile', 'error', 'ProfileService', ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    "src/ProfileService.ets",
                    "profile load failed",
                    "profile_load_failed",
                    '["个人中心空白"]',
                    '["network_error"]',
                    "2026-07-13T00:00:00Z",
                ),
            )
            conn.commit()

    def test_context_returns_log_keywords_code_and_history_without_diagnosis(self) -> None:
        self._seed_code_graph()

        result = self.run_memory(
            self.project,
            "context",
            "--query",
            "个人中心空白 profile load failed 日志",
            "--json",
        )
        payload = json.loads(result.stdout)

        self.assertTrue(payload["code_log_matches"])
        self.assertTrue(payload["query_handoff"]["log_keywords"])
        self.assertTrue(payload["query_handoff"]["code_anchors"])
        self.assertFalse(payload["query_handoff"]["role_boundary"]["runtime_reads_temporary_logs"])
        self.assertNotIn("evidence_chains", payload)
        self.assertNotIn("log_search_plan", payload)
        self.assertNotIn("likely_causes", payload["code_log_matches"][0])

    def test_impact_scope_finds_reverse_dependency_and_unlearned_gap(self) -> None:
        self._seed_code_graph()

        result = self.run_memory(
            self.project,
            "impact-scope",
            "--files",
            "src/ProfileService.ets,src/Unknown.ets",
            "--query",
            "修改个人资料加载逻辑",
            "--json",
        )
        payload = json.loads(result.stdout)

        summary = payload["impact_summary"]
        self.assertEqual(["src/Unknown.ets"], summary["unlearned_changed_files"])
        self.assertEqual("src/ProfilePage.ets", summary["reverse_dependents"][0]["source"])
        self.assertTrue(any(gap["kind"] == "unlearned_changed_file" for gap in payload["evidence_gaps"]))
        self.assertIn(summary["risk_band"], {"medium", "high"})
