# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class AgentMemoryRuntimePart11Tests(AgentMemoryTestBase):
    def test_context_maps_problem_to_log_keywords_and_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = profile_project(Path(temp_dir))
            self.run_memory(project, "learn-path", "--path", "pages")

            payload = json.loads(self.run_memory(
                project, "context", "--query", "个人资料页空白 profile load failed", "--json",
            ).stdout)

            handoff = payload["query_handoff"]
            self.assertTrue(handoff["log_keywords"])
            self.assertTrue(handoff["log_anchors"])
            self.assertTrue(any(item["file_path"] == "pages/Profile.ets" for item in handoff["code_anchors"]))
            self.assertFalse(handoff["role_boundary"]["runtime_reads_temporary_logs"])
            self.assertFalse(handoff["role_boundary"]["runtime_builds_causal_chains"])

    def test_agent_candidate_cause_can_be_queried_as_second_round(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = profile_project(Path(temp_dir))
            self.run_memory(project, "learn-path", "--path", "pages")

            payload = json.loads(self.run_memory(
                project, "context", "--query", "session invalid", "--json",
            ).stdout)

            self.assertTrue(payload["code_log_matches"])
            self.assertIn("SessionManager.ets", payload["code_log_matches"][0]["file_path"])
            self.assertTrue(payload["query_handoff"]["next_query_contract"]["one_candidate_per_query"])

    def test_context_usage_and_reflection_keep_agent_authored_lesson(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = profile_project(Path(temp_dir))
            self.run_memory(project, "learn-path", "--path", "pages")
            self.run_memory(project, "context", "--query", "profile load failed", "--json")
            self.run_memory(
                project,
                "reflect",
                "--task",
                "诊断个人资料页空白",
                "--lesson",
                "Agent 对比源码调用顺序后确认应先检查会话恢复。",
            )

            latest = self.list_records(project, "reflection")[0]
            self.assertIn("Agent 对比源码", latest["lesson"])
            self.assertFalse(latest["repair_action"])
            sample = json.loads(self.usage_sample_path(project).read_text(encoding="utf-8"))
            self.assertIn("context", sample["commands"])
            self.assertNotIn("analyze-runtime-log", sample["commands"])


def profile_project(root: Path) -> Path:
    project = root / "app"
    pages = project / "pages"
    pages.mkdir(parents=True)
    (pages / "Profile.ets").write_text(
        "struct ProfilePage {\n"
        "  loadProfile() {\n"
        "    console.error('profile load failed')\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    (pages / "SessionManager.ets").write_text(
        "class SessionManager {\n"
        "  restore() {\n"
        "    console.warn('session invalid')\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    return project
