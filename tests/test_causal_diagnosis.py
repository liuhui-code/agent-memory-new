# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase, REPO_ROOT, RUNTIME
from tools.agent_memory_runtime.runtime_log_parsing import normalize_runtime_log_line
from tools.agent_memory_runtime.runtime_span_graph import build_runtime_span_graph


class CausalDiagnosisTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "demo"
        self.project.mkdir()
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_runtime_parser_extracts_identity_for_incident_storage(self) -> None:
        event = normalize_runtime_log_line(
            "2026-07-14T10:00:01Z Worker E failed event_name=load.failed "
            "trace_id=t1 span_id=child parent_span_id=root service.name=profile",
            2,
        )

        self.assertEqual("root", event["parent_span_id"])
        self.assertEqual("profile", event["service_name"])

    def test_span_graph_records_relation_order_without_diagnosis(self) -> None:
        events = [
            runtime_event(1, "2026-07-14T10:00:00Z", "root", "", "request.start"),
            runtime_event(2, "2026-07-14T10:00:01Z", "child", "root", "profile.failed"),
        ]

        graph = build_runtime_span_graph(events)

        self.assertEqual("parent_of", graph["edges"][0]["relation"])
        self.assertTrue(graph["relation_paths"][0]["temporal_order_verified"])
        self.assertTrue(graph["relation_paths"][0]["correlation_verified"])
        self.assertNotIn("root_cause", graph)
        self.assertNotIn("hypotheses", graph)

    def test_context_handoff_assigns_causal_reasoning_to_agent(self) -> None:
        payload = json.loads(self.run_memory(
            self.project,
            "context",
            "--query",
            "why does profile load fail",
            "--json",
        ).stdout)

        boundary = payload["query_handoff"]["role_boundary"]
        self.assertFalse(boundary["runtime_reads_temporary_logs"])
        self.assertFalse(boundary["runtime_builds_causal_chains"])
        self.assertIn("infer call/causal chains", boundary["agent_cli"])
        self.assertNotIn("evidence_chains", payload)

    def test_removed_reasoning_heavy_commands_are_not_public(self) -> None:
        for command in ("evidence-context", "analyze-runtime-log"):
            process = subprocess.run(
                [sys.executable, str(RUNTIME), command, "--project", str(self.project)],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, process.returncode)
            self.assertIn("invalid choice", process.stderr)


def runtime_event(
    line: int,
    timestamp: str,
    span_id: str,
    parent_span_id: str,
    event_name: str,
) -> dict:
    return {
        "line_number": line,
        "timestamp": timestamp,
        "trace_id": "trace-1",
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "event_name": event_name,
        "event_type": event_name,
        "result": "failed" if "failed" in event_name else "",
        "reason": "",
        "error_code": "",
    }
