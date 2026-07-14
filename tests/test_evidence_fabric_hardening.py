# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.evidence_fusion import classify_causal_evidence, select_diverse_evidence
from tools.agent_memory_runtime.evidence_models import EvidenceItem
from tools.agent_memory_runtime.goal_planner import build_goal_plan
from tools.agent_memory_runtime.storage import resolve_project


class EvidenceFabricHardeningTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "demo"
        self.project.mkdir()
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def database(self) -> Path:
        return self.project_memory_dir(self.project) / "memory.db"

    def seed_code_graph(self, valid_to: str | None = None) -> None:
        with sqlite3.connect(self.database()) as conn:
            project_id = self.project_id(self.project)
            service_id = conn.execute(
                """
                INSERT INTO code_files(
                  project_id, file_path, summary, language, business_summary,
                  business_terms, updated_at
                ) VALUES (?, 'src/ProfileService.ets', 'Loads profile', 'ArkTS',
                          'Profile service', '["profile"]', '2026-07-13T00:00:00Z')
                """,
                (project_id,),
            ).lastrowid
            page_id = conn.execute(
                """
                INSERT INTO code_files(
                  project_id, file_path, summary, language, business_summary,
                  business_terms, updated_at
                ) VALUES (?, 'src/ProfilePage.ets', 'Profile page', 'ArkTS',
                          'Profile page', '["profile"]', '2026-07-13T00:00:00Z')
                """,
                (project_id,),
            ).lastrowid
            conn.execute(
                """
                INSERT INTO code_files(
                  project_id, file_path, summary, language, business_summary,
                  business_terms, updated_at
                ) VALUES (?, 'tests/ProfileServiceTest.ets', 'Tests profile load', 'ArkTS',
                          'Profile service tests', '["profile"]', '2026-07-13T00:00:00Z')
                """,
                (project_id,),
            )
            conn.execute(
                """
                INSERT INTO memory_edges(
                  project_id, source_type, source_id, relation, target_type,
                  target_id, evidence, confidence, valid_to, created_at
                ) VALUES (?, 'code_file', ?, 'imports', 'code_file', ?,
                          'ProfilePage -> ProfileService', 0.9, ?, '2026-07-13T00:00:00Z')
                """,
                (project_id, page_id, service_id, valid_to),
            )
            conn.commit()

    def test_schema_contains_edge_metadata_and_impact_feedback(self) -> None:
        with sqlite3.connect(self.database()) as conn:
            edge_columns = {row[1] for row in conn.execute("PRAGMA table_info(memory_edges)")}
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        self.assertTrue(
            {"source_revision", "extractor_version", "valid_from", "valid_to", "evidence_kind", "last_verified_at"}
            <= edge_columns
        )
        self.assertIn("impact_feedback", tables)

    def test_learning_writes_current_edge_provenance(self) -> None:
        source = self.project / "pages"
        source.mkdir()
        (source / "Profile.ets").write_text(
            "struct Profile { load() { console.error('profile failed') } }\n",
            encoding="utf-8",
        )

        self.run_memory(self.project, "learn-path", "--path", "pages", "--json")
        edges = self.list_records(self.project, "memory-edge")

        self.assertTrue(edges)
        self.assertTrue(all(edge["extractor_version"] == "code-wiki:v4" for edge in edges))
        self.assertTrue(all(edge["valid_to"] is None for edge in edges))
        self.assertTrue(all(edge["last_verified_at"] for edge in edges))

    def test_invalid_edge_is_excluded_from_impact_scope(self) -> None:
        self.seed_code_graph(valid_to="2026-07-13T01:00:00Z")

        result = self.run_memory(
            self.project,
            "impact-scope",
            "--files",
            "src/ProfileService.ets",
            "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual([], payload["impact_summary"]["reverse_dependents"])

    def test_query_plan_is_bounded_and_global_scope_is_explicit(self) -> None:
        plan = build_goal_plan("整体架构和高频事故", explicit_scope="auto")

        self.assertEqual("global", plan.query_scope)
        self.assertLessEqual(len(plan.subqueries), 3)
        self.assertEqual(3, plan.max_rounds)

    def test_empty_query_stops_when_second_round_adds_no_evidence(self) -> None:
        result = self.run_memory(
            self.project,
            "evidence-context",
            "--query",
            "totally-unmatched-local-anchor",
            "--json",
        )
        execution = json.loads(result.stdout)["retrieval_metadata"]["query_execution"]

        self.assertEqual("no_new_evidence", execution["stop_reason"])
        self.assertEqual(2, execution["round_count"])

    def test_global_query_returns_bounded_aggregate_evidence(self) -> None:
        self.seed_code_graph()

        result = self.run_memory(
            self.project,
            "evidence-context",
            "--query",
            "整体架构和高频事故",
            "--scope",
            "global",
            "--json",
        )
        payload = json.loads(result.stdout)
        items = sum(payload["evidence"].values(), [])

        self.assertEqual("global", payload["goal_plan"]["query_scope"])
        self.assertTrue(any(item["kind"] == "aggregate_summary" for item in items))

    def test_diversity_limits_duplicate_experience_patterns(self) -> None:
        items = [
            EvidenceItem(
                evidence_id=f"reflection:{index}", source="reflection", kind="reflection",
                record_id=index, title="Same broad lesson", summary=f"case {index}",
                location=None, authority="advisory_memory", original_score=10 - index,
            )
            for index in range(6)
        ]

        selected = select_diverse_evidence(items, 10)

        self.assertEqual(1, len(selected))

    def test_runtime_log_normalizes_trace_context(self) -> None:
        from tools.agent_memory_runtime.otel_lite import runtime_event_to_otel_lite
        from tools.agent_memory_runtime.runtime_logs import normalize_runtime_log_line

        event = normalize_runtime_log_line(
            "07-13 12:00:00.100 EntryAbility E Profile: failed "
            "event_name=profile.load.failed trace_id=abc span_id=def trace_flags=01 "
            "request_id=req-1 result=failed module=entry ability=EntryAbility",
            1,
        )
        otel = runtime_event_to_otel_lite(event)

        self.assertEqual("abc", otel["trace_id"])
        self.assertEqual("def", otel["span_id"])
        self.assertEqual("profile.load.failed", otel["event_name"])
        self.assertEqual("failed", otel["attributes"]["app.result"])

    def test_causal_levels_require_more_than_shared_text(self) -> None:
        code = evidence("code_file:1", "code", "learned_code_anchor", {"id": 1})
        edge = evidence("memory_edge:2", "edge", "graph_relation", {"id": 2})
        resolved = evidence(
            "incident_trace:3",
            "incident",
            "observed_incident",
            {"id": 3, "status": "resolved", "resolution": "rollback fixed the symptom"},
        )
        rejected = evidence(
            "incident_trace:4",
            "incident",
            "observed_incident",
            {"id": 4, "status": "ignored"},
        )

        self.assertEqual("association", classify_causal_evidence([code])["level"])
        self.assertEqual("supported", classify_causal_evidence([code, edge])["level"])
        self.assertEqual("verified", classify_causal_evidence([resolved])["level"])
        self.assertEqual("rejected", classify_causal_evidence([rejected])["level"])

    def test_failed_test_feedback_boosts_future_recommendation(self) -> None:
        self.seed_code_graph()
        first = json.loads(
            self.run_memory(
                self.project, "impact-scope", "--files", "src/ProfileService.ets", "--json"
            ).stdout
        )
        self.assertEqual("tests/ProfileServiceTest.ets", first["recommended_tests"][0]["test_path"])

        self.run_memory(
            self.project,
            "impact-feedback",
            "--files",
            "src/ProfileService.ets",
            "--executed-tests",
            "tests/ProfileServiceTest.ets",
            "--failed-tests",
            "tests/ProfileServiceTest.ets",
            "--outcome",
            "fail",
            "--json",
        )
        second = json.loads(
            self.run_memory(
                self.project, "impact-scope", "--files", "src/ProfileService.ets", "--json"
            ).stdout
        )
        top = second["recommended_tests"][0]

        self.assertIn("historical_failure_for_similar_change", top["reasons"])
        self.assertEqual(1, second["audit"]["impact_feedback"]["failures"])

    def test_graph_neighbor_can_contribute_a_bounded_test_signal(self) -> None:
        from tools.agent_memory_runtime.impact_feedback import recommend_tests

        self.seed_code_graph()
        recommendations = recommend_tests(
            resolve_project(str(self.project), str(self.memory_home(self.project))),
            ["src/AccountLedger.ets"],
            ["src/ProfilePage.ets"],
        )

        self.assertEqual("tests/ProfileServiceTest.ets", recommendations[0]["test_path"])
        self.assertIn("one_hop_graph_proximity", recommendations[0]["reasons"])


def evidence(evidence_id: str, source: str, authority: str, raw: dict) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        source=source,
        kind=evidence_id.split(":", 1)[0],
        record_id=int(raw["id"]),
        title=evidence_id,
        summary="summary",
        location=None,
        authority=authority,
        original_score=80.0,
        raw=raw,
    )
