# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.diagnosis_hypotheses import build_runtime_hypothesis_ledger
from tools.agent_memory_runtime.runtime_log_parsing import normalize_runtime_log_line
from tools.agent_memory_runtime.runtime_log_reflection import build_runtime_episode_candidate
from tools.agent_memory_runtime.runtime_span_graph import build_runtime_span_graph


class CausalDiagnosisTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "demo"
        self.project.mkdir()
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_runtime_parser_extracts_parent_and_resource_identity(self) -> None:
        event = normalize_runtime_log_line(
            "2026-07-14T10:00:01Z Worker E failed event_name=load.failed "
            "trace_id=t1 span_id=child parent_span_id=root service.name=profile "
            "service.version=2 service.instance.id=node-1 deployment.environment.name=prod",
            2,
        )

        self.assertEqual("root", event["parent_span_id"])
        self.assertEqual("profile", event["service_name"])
        self.assertEqual("2", event["service_version"])
        self.assertEqual("node-1", event["service_instance_id"])
        self.assertEqual("prod", event["deployment_environment"])

    def test_span_graph_builds_parent_edge_and_verified_path_order(self) -> None:
        events = [
            runtime_event(1, "2026-07-14T10:00:00Z", "root", "", "request.start"),
            runtime_event(2, "2026-07-14T10:00:01Z", "child", "root", "profile.failed"),
        ]

        graph = build_runtime_span_graph(events)

        self.assertEqual("parent_of", graph["edges"][0]["relation"])
        self.assertTrue(graph["causal_paths"][0]["temporal_order_verified"])
        self.assertTrue(graph["causal_paths"][0]["correlation_verified"])
        self.assertEqual("good", graph["quality"]["status"])

    def test_episode_chain_is_chronological_not_relevance_ordered(self) -> None:
        later = runtime_event(9, "2026-07-14T10:00:09Z", "child", "root", "profile.failed")
        earlier = runtime_event(2, "2026-07-14T10:00:02Z", "root", "", "request.start")

        candidate = build_runtime_episode_candidate("profile failed", [], [later, earlier])

        self.assertEqual("source_line_chronological", candidate["chain_order"])
        self.assertEqual(["request.start", "profile.failed"], candidate["candidate_chain"])

    def test_runtime_analysis_returns_graph_and_persists_hypothesis_ledger(self) -> None:
        log_file = self.project / "runtime.log"
        log_file.write_text(
            "2026-07-14T10:00:00Z App I start event_name=request.start trace_id=t1 span_id=root\n"
            "2026-07-14T10:00:01Z Worker E failed event_name=profile.failed trace_id=t1 "
            "span_id=child parent_span_id=root error_code=E42 result=failed\n",
            encoding="utf-8",
        )

        payload = json.loads(self.run_memory(
            self.project,
            "analyze-runtime-log",
            "--query",
            "profile failed E42",
            "--log-file",
            str(log_file),
            "--json",
        ).stdout)

        self.assertEqual(2, len(payload["span_graph"]["spans"]))
        self.assertTrue(payload["hypothesis_ledger"]["hypotheses"])
        ledger_path = self.project_memory_dir(self.project) / "runtime" / "last_hypothesis_ledger.json"
        self.assertTrue(ledger_path.exists())

    def test_incident_trace_persists_span_graph_and_explicit_verification(self) -> None:
        payload = json.loads(self.run_memory(
            self.project,
            "incident-trace",
            "--symptom",
            "profile load failed",
            "--log-text",
            "2026-07-14T10:00:00Z App E failed event_name=profile.failed "
            "trace_id=t1 span_id=s1 error_code=E42 result=failed",
            "--json",
        ).stdout)
        self.assertEqual("runtime-span-graph/v1", payload["span_graph"]["schema_version"])
        self.assertTrue(payload["span_graph"]["audit"]["persisted"])

        updated = json.loads(self.run_memory(
            self.project,
            "incident-trace-status",
            "--id",
            str(payload["id"]),
            "--status",
            "resolved",
            "--resolution",
            "profile loads",
            "--intervention",
            "reverted profile parser",
            "--verification-evidence",
            "20 repeated loads passed",
            "--json",
        ).stdout)
        self.assertEqual("reverted profile parser", updated["intervention"])
        self.assertEqual("20 repeated loads passed", updated["verification_evidence"])

    def test_diagnosis_query_returns_and_persists_ledger(self) -> None:
        payload = json.loads(self.run_memory(
            self.project,
            "evidence-context",
            "--query",
            "why does profile load fail",
            "--goal",
            "diagnosis",
            "--json",
        ).stdout)

        self.assertEqual("diagnosis-hypothesis-ledger/v1", payload["hypothesis_ledger"]["schema_version"])
        self.assertTrue(payload["hypothesis_ledger"]["hypotheses"])
        ledger_path = self.project_memory_dir(self.project) / "runtime" / "last_hypothesis_ledger.json"
        self.assertTrue(ledger_path.exists())

    def test_runtime_ledger_requires_temporal_and_correlation_support(self) -> None:
        event = runtime_event(1, "", "", "", "profile.failed")
        ledger = build_runtime_hypothesis_ledger("profile failed", [event], build_runtime_span_graph([event]))

        self.assertEqual("open", ledger["hypotheses"][0]["status"])
        self.assertIn("shared runtime identity", ledger["hypotheses"][0]["missing_evidence"])


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
        "trace_id": "trace-1" if span_id else "",
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "event_name": event_name,
        "event_type": event_name,
        "result": "failed" if "failed" in event_name else "",
        "reason": "",
        "error_code": "",
    }
