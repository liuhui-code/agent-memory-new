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
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(RUNTIME), *args, "--project", str(project)]
        command.extend(["--memory-home", str(memory_home or self.memory_home(project))])
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=check,
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

    def learn_fixture(self, project: Path) -> None:
        self.write_arkts_fixture(project)
        self.run_memory(project, "learn-path", "--path", "entry", "--json")

    def record_incident(self, project: Path, verified: bool = True) -> dict:
        args = [
            "incident-trace",
            "--symptom", "页面跳转后白屏",
            "--scene", "route",
            "--diagnosis-summary", "Profile route target was not registered",
            "--observed-event", "navigation failed after profile click",
            "--causal-step", "Home.openProfile -> router.pushUrl",
            "--code-anchor", "entry/src/main/ets/pages/Home.ets::openProfile",
            "--status", "resolved" if verified else "diagnosed",
        ]
        if verified:
            args.extend([
                "--resolution", "Profile route opens normally",
                "--intervention", "Registered the ProfileDetail route target",
                "--verification-evidence", "Route test passed 50 consecutive runs",
            ])
        args.append("--json")
        return json.loads(self.run_memory(project, *args).stdout)

    def test_incident_trace_schema_has_evidence_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "init")

            db_path = self.project_memory_dir(project) / "memory.db"
            with sqlite3.connect(db_path) as conn:
                columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(incident_traces)")
                }

            self.assertIn("capture_mode", columns)
            self.assertIn("evidence_state", columns)

    def test_raw_log_arguments_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "init")

            result = self.run_memory(
                project,
                "incident-trace",
                "--symptom", "page failed",
                "--diagnosis-summary", "Agent analyzed the failure",
                "--log-text", "temporary runtime stream",
                "--json",
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("unrecognized arguments: --log-text", result.stderr)
            self.assertEqual([], self.list_records(project, "incident-trace"))

    def test_agent_structured_incident_persists_no_temporary_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.learn_fixture(project)

            payload = self.record_incident(project)

            self.assertEqual("agent-incident-record/v2", payload["schema_version"])
            self.assertEqual("agent_structured", payload["capture_mode"])
            self.assertEqual("verified", payload["evidence_state"])
            self.assertIsNone(payload["entry_log_text"])
            self.assertIsNone(payload["suspected_chain"])
            self.assertIsNone(payload["span_graph"])
            self.assertEqual(
                ["navigation failed after profile click"], payload["observed_events"]
            )
            self.assertEqual(
                ["Home.openProfile -> router.pushUrl"], payload["agent_causal_steps"]
            )
            self.assertTrue(
                any(link["target_type"] == "code_symbol" for link in payload["links"])
            )
            self.assertFalse(payload["role_boundary"]["runtime_reads_temporary_logs"])
            self.assertFalse(payload["role_boundary"]["runtime_builds_causal_chains"])

    def test_unknown_anchor_keeps_incident_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "init")

            payload = json.loads(self.run_memory(
                project,
                "incident-trace",
                "--symptom", "unknown page failure",
                "--scene", "unknown",
                "--diagnosis-summary", "Agent suspects an unavailable owner",
                "--code-anchor", "src/Missing.ets::run",
                "--json",
            ).stdout)

            self.assertEqual("reported", payload["evidence_state"])
            self.assertLessEqual(payload["confidence"], 0.45)
            self.assertEqual("unresolved_agent_anchor", payload["links"][0]["relation"])

    def test_status_update_promotes_supported_record_only_after_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.learn_fixture(project)
            created = self.record_incident(project, verified=False)
            self.assertEqual("supported", created["evidence_state"])

            updated = json.loads(self.run_memory(
                project,
                "incident-trace-status",
                "--id", str(created["id"]),
                "--status", "resolved",
                "--resolution", "Profile route opens normally",
                "--intervention", "Registered the ProfileDetail route target",
                "--verification-evidence", "Route test passed 50 consecutive runs",
                "--json",
            ).stdout)

            self.assertEqual("verified", updated["evidence_state"])

    def test_context_returns_only_structured_sanitized_incidents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.learn_fixture(project)
            self.record_incident(project)

            payload = json.loads(self.run_memory(
                project, "context", "--query", "Profile route target failed", "--json"
            ).stdout)
            incident = payload["incident_trace_matches"][0]

            self.assertEqual("verified", incident["evidence_state"])
            self.assertEqual(["Home.openProfile -> router.pushUrl"], incident["agent_causal_steps"])
            self.assertNotIn("entry_log_text", incident)
            self.assertNotIn("candidate_chain", incident)
            self.assertNotIn("span_graph", incident)

    def test_legacy_incident_is_quarantined_from_context_and_governance_flags_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "init")
            db_path = self.project_memory_dir(project) / "memory.db"
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO incident_traces(
                      project_id, trace_key, status, symptom, arkts_scene,
                      entry_log_text, source, created_at, updated_at
                    ) VALUES (?, 'legacy', 'resolved', 'legacy profile failure', 'route',
                              'old runtime stream', 'incident-trace', '2026-01-01', '2026-01-01')
                    """,
                    (self.project_id(project),),
                )
                conn.commit()

            context = json.loads(self.run_memory(
                project, "context", "--query", "legacy profile failure", "--json"
            ).stdout)
            plan = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)

            self.assertEqual([], context["incident_trace_matches"])
            self.assertTrue(any(
                action["action"] == "review_legacy_incident_trace"
                for action in plan["actions"]
            ))

    def test_maintain_promotes_only_verified_structured_incident(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.learn_fixture(project)
            trace = self.record_incident(project)

            plan = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)
            action = next(
                action for action in plan["actions"]
                if action["action"] == "promote_incident_trace_to_reflection"
            )

            self.assertEqual(trace["id"], action["id"])
            self.assertEqual("verified", action["evidence_state"])
            self.assertEqual(
                [f"incident_trace:{trace['id']}"],
                action["reflection_payload_template"]["source_cases"],
            )

    def test_vault_export_marks_incident_evidence_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.learn_fixture(project)
            self.record_incident(project)

            self.run_memory(project, "vault-export")
            page = self.project_memory_dir(project) / "vault" / "Codebase Wiki" / "incident-traces.md"

            self.assertIn("verified", page.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
