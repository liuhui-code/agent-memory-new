# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"


class AgentMemoryIncidentTraceTests(unittest.TestCase):
    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

    def project_id(self, project: Path) -> str:
        import hashlib

        return hashlib.sha256(str(project.resolve()).encode("utf-8")).hexdigest()[:16]

    def project_memory_dir(self, project: Path) -> Path:
        return self.memory_home(project) / "projects" / self.project_id(project)

    def run_memory(
        self,
        project: Path,
        *args: str,
        memory_home: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(RUNTIME), *args, "--project", str(project)]
        command.extend(["--memory-home", str(memory_home or self.memory_home(project))])
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
            env=os.environ.copy(),
        )

    def list_records(self, project: Path, kind: str) -> list[dict]:
        result = self.run_memory(project, "list", "--type", kind, "--json")
        return json.loads(result.stdout)

    def write_arkts_fixture(self, project: Path) -> None:
        page = project / "entry" / "src" / "main" / "ets" / "pages" / "Home.ets"
        page.parent.mkdir(parents=True)
        page.write_text(
            """
import { router } from '@kit.ArkUI';

function openProfile() {
  console.error('router.pushUrl failed for ProfileDetail');
  router.pushUrl({ url: 'pages/ProfileDetail' });
}
""".strip()
            + "\n",
            encoding="utf-8",
        )

    def test_incident_trace_schema_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "init")

            db_path = self.project_memory_dir(project) / "memory.db"
            with sqlite3.connect(db_path) as conn:
                names = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual')"
                    )
                }

            self.assertIn("incident_traces", names)
            self.assertIn("incident_trace_links", names)
            self.assertIn("incident_trace_fts", names)

    def test_classifies_arkts_route_incident(self) -> None:
        from tools.agent_memory_runtime.incident_trace_builder import classify_arkts_scene

        scene, reasons = classify_arkts_scene("页面跳转后白屏", "router.pushUrl failed")

        self.assertEqual(scene, "route")
        self.assertTrue(any("router" in reason.lower() for reason in reasons))

    def test_classifies_arkts_resource_incident(self) -> None:
        from tools.agent_memory_runtime.incident_trace_builder import classify_arkts_scene

        scene, reasons = classify_arkts_scene("图片资源显示不出来", "$r('app.media.avatar')")

        self.assertEqual(scene, "resource")
        self.assertTrue(reasons)

    def test_builds_incident_trace_draft_from_code_log_anchor(self) -> None:
        from tools.agent_memory_runtime.incident_trace_builder import build_incident_trace_draft
        from tools.agent_memory_runtime.storage import resolve_project

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write_arkts_fixture(project)
            self.run_memory(project, "learn-path", "--path", "entry", "--json")
            runtime_project = resolve_project(str(project), str(self.memory_home(project)))

            draft = build_incident_trace_draft(
                runtime_project,
                "页面跳转后白屏",
                "router.pushUrl failed for ProfileDetail",
            )

            self.assertEqual(draft["arkts_scene"], "route")
            self.assertTrue(draft["matched_code_logs"])
            self.assertTrue(
                any(link["relation"] == "matched_log" for link in draft["linked_targets"])
            )
            self.assertTrue(draft["candidate_chain"])
            self.assertIn("router", draft["suggested_followup_query"].lower())

    def test_incident_trace_command_writes_compact_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write_arkts_fixture(project)
            self.run_memory(project, "learn-path", "--path", "entry", "--json")

            result = self.run_memory(
                project,
                "incident-trace",
                "--symptom",
                "页面跳转后白屏",
                "--log-text",
                "router.pushUrl failed for ProfileDetail",
                "--json",
            )
            payload = json.loads(result.stdout)
            traces = self.list_records(project, "incident-trace")
            links = self.list_records(project, "incident-trace-link")

            self.assertEqual(payload["arkts_scene"], "route")
            self.assertLessEqual(len(payload["entry_log_text"]), 2000)
            self.assertEqual(len(traces), 1)
            self.assertTrue(any(link["relation"] == "matched_log" for link in links))
            self.assertTrue(any(link["relation"] == "semantic_candidate" for link in links))
            self.assertTrue(payload["causal_chain"])

    def test_incident_trace_status_updates_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "incident-trace",
                "--symptom",
                "页面跳转后白屏",
                "--log-text",
                "router.pushUrl failed for ProfileDetail",
                "--json",
            )

            result = self.run_memory(
                project,
                "incident-trace-status",
                "--id",
                "1",
                "--status",
                "resolved",
                "--resolution",
                "Fixed route target registration.",
                "--json",
            )
            payload = json.loads(result.stdout)
            traces = self.list_records(project, "incident-trace")

            self.assertEqual(payload["status"], "resolved")
            self.assertEqual(traces[0]["resolution"], "Fixed route target registration.")

    def test_context_returns_incident_trace_matches_for_similar_symptom(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "incident-trace",
                "--symptom",
                "页面跳转后白屏",
                "--log-text",
                "router.pushUrl failed for ProfileDetail",
                "--json",
            )

            result = self.run_memory(
                project,
                "context",
                "--query",
                "Profile 页面白屏 router failed",
                "--json",
            )
            payload = json.loads(result.stdout)

            self.assertIn("incident_trace_matches", payload)
            self.assertEqual(payload["incident_trace_matches"][0]["arkts_scene"], "route")

    def test_maintain_plan_promotes_resolved_incident_trace_to_reflection_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write_arkts_fixture(project)
            self.run_memory(project, "learn-path", "--path", "entry", "--json")
            self.run_memory(
                project,
                "incident-trace",
                "--symptom",
                "页面跳转后白屏",
                "--log-text",
                "router.pushUrl failed for ProfileDetail",
                "--json",
            )
            self.run_memory(
                project,
                "incident-trace-status",
                "--id",
                "1",
                "--status",
                "resolved",
                "--resolution",
                "Fixed route target registration.",
                "--json",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            payload = json.loads(result.stdout)
            action = next(
                action for action in payload["actions"]
                if action["action"] == "promote_incident_trace_to_reflection"
            )

            self.assertEqual(action["id"], 1)
            self.assertEqual(action["reflection_payload_template"]["source_cases"], ["incident_trace:1"])
            terms = " ".join(action["reflection_payload_template"]["useful_followup_terms"]).lower()
            self.assertIn("router.pushurl", terms)

    def test_maintain_plan_reviews_incident_trace_without_code_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "incident-trace",
                "--symptom",
                "页面跳转后白屏",
                "--log-text",
                "unmatched runtime-only failure text",
                "--json",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            payload = json.loads(result.stdout)
            action = next(
                action for action in payload["actions"]
                if action["action"] == "review_log_anchor_gap"
            )

            self.assertEqual(action["id"], 1)
            self.assertEqual(action["arkts_scene"], "route")

    def test_vault_export_writes_incident_trace_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "incident-trace",
                "--symptom",
                "页面跳转后白屏",
                "--log-text",
                "router.pushUrl failed for ProfileDetail",
                "--json",
            )

            self.run_memory(project, "vault-export")
            vault = self.project_memory_dir(project) / "vault"

            self.assertTrue((vault / "Codebase Wiki" / "incident-traces.md").exists())
            self.assertTrue((vault / "Governance" / "Incident Trace Review.md").exists())
