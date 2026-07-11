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


class QualityPerformanceScoringTests(unittest.TestCase):
    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

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

    def test_quality_scoring_rewards_structured_verified_experience(self) -> None:
        from tools.agent_memory_runtime.quality_scoring import score_reflection_quality

        row = {
            "id": 1,
            "experience_type": "procedure_experience",
            "confidence": 0.9,
            "status": "active",
            "verification_method": "ran targeted unit test",
            "source_cases": '["incident_trace:1"]',
            "trigger_condition": "ArkTS route blank screen",
            "repair_action": "inspect router.pushUrl target",
            "reuse_feedback": "reused successfully",
        }

        score = score_reflection_quality(row)

        self.assertGreaterEqual(score["quality_score"], 0.75)
        self.assertIn(score["quality_band"], {"good", "excellent"})
        self.assertGreater(score["score_parts"]["evidence_strength"], 0.6)
        self.assertEqual(score["recommended_action"], "keep_active")

    def test_quality_scoring_penalizes_misleading_stale_experience(self) -> None:
        from tools.agent_memory_runtime.quality_scoring import score_reflection_quality

        row = {
            "id": 2,
            "experience_type": "procedure_experience",
            "confidence": 0.35,
            "status": "stale",
            "is_stale": 1,
            "misleading_score": 0.9,
            "lesson": "broad old advice",
        }

        score = score_reflection_quality(row)

        self.assertLess(score["quality_score"], 0.45)
        self.assertEqual(score["quality_band"], "poor")
        self.assertEqual(score["recommended_action"], "review_or_stale")

    def test_performance_sample_scores_fast_bounded_operation_highly(self) -> None:
        from tools.agent_memory_runtime.performance_scoring import build_performance_sample
        from tools.agent_memory_runtime.storage import resolve_project

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "app"
            project_root.mkdir()
            project = resolve_project(str(project_root), str(self.memory_home(project_root)))

            sample = build_performance_sample(
                project,
                operation="context",
                elapsed_ms=25.0,
                result_counts={"semantic_facts": 2, "reflections": 1},
                token_estimate=900,
                status="ok",
            )

        self.assertEqual(sample["operation"], "context")
        self.assertGreater(sample["performance_score"], 0.8)
        self.assertEqual(sample["performance_band"], "excellent")

    def test_maintain_plan_includes_quality_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            payload = {
                "experience_type": "procedure_experience",
                "task": "Diagnose ArkTS route blank screen",
                "summary": "Route target mismatch was found through incident trace.",
                "lesson": "When ArkTS navigation opens a blank page, inspect router.pushUrl target and page registration first.",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "verification_method": "ran targeted route test",
                "source_cases": ["incident_trace:1"],
                "reuse_feedback": "reused successfully",
                "confidence": 0.9,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(payload))
            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        self.assertIn("quality_summary", data)
        self.assertGreaterEqual(data["quality_summary"]["scored_records"], 1)
        self.assertGreaterEqual(data["quality_summary"]["high_value_records"], 1)
        high_value_ids = {item["record_id"] for item in data["high_value_records"]}
        self.assertIn(1, high_value_ids)

    def test_maintain_health_includes_runtime_performance_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()

            self.run_memory(project, "init")
            self.run_memory(project, "context", "--query", "no matching memory", "--json")
            self.run_memory(project, "maintain-plan", "--json")
            result = self.run_memory(project, "maintain-health", "--json")
            data = json.loads(result.stdout)

        self.assertIn("runtime_performance", data)
        self.assertGreaterEqual(data["runtime_performance"]["sample_count"], 1)
        self.assertIn("context", data["runtime_performance"]["operations"])
        self.assertIn("maintain-plan", data["runtime_performance"]["operations"])

    def test_maintain_plan_reviews_runtime_performance_budget(self) -> None:
        from tools.agent_memory_runtime.performance_scoring import append_performance_sample, build_performance_sample
        from tools.agent_memory_runtime.storage import ensure_dirs, resolve_project

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "app"
            project_root.mkdir()
            self.run_memory(project_root, "init")
            project = resolve_project(str(project_root), str(self.memory_home(project_root)))
            ensure_dirs(project)
            append_performance_sample(
                project,
                build_performance_sample(
                    project,
                    operation="context",
                    elapsed_ms=2400.0,
                    result_counts={"semantic_facts": 80, "reflections": 60},
                    token_estimate=3600,
                    status="ok",
                ),
            )

            result = self.run_memory(project_root, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        actions = [action for action in data["actions"] if action["action"] == "review_runtime_performance_budget"]
        self.assertEqual(1, len(actions))
        self.assertEqual("context", actions[0]["operation"])
        self.assertEqual("runtime_performance", actions[0]["type"])
        self.assertGreater(actions[0]["p95_elapsed_ms"], actions[0]["target_p95_ms"])
        self.assertGreater(data["runtime_performance"]["sample_count"], 0)
        self.assertEqual(1, data["governance_summary"]["runtime_performance_reviews"])

    def test_context_reranks_reflections_by_quality_signal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            weak_payload = {
                "experience_type": "procedure_experience",
                "task": "ArkTS route blank screen",
                "summary": "Old broad advice for route blank screen.",
                "lesson": "Try broad route checks.",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "try broad route checks",
                "verification_method": "not verified on current source",
                "source_cases": ["old_case:1"],
                "reuse_feedback": "misleading",
                "confidence": 0.4,
                "misleading_score": 0.5,
            }
            strong_payload = {
                "experience_type": "procedure_experience",
                "task": "ArkTS route blank screen diagnosis",
                "summary": "Verified route target mismatch diagnosis.",
                "lesson": "For ArkTS route blank screen, inspect router.pushUrl target and page registration first.",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "verification_method": "ran route navigation test",
                "source_cases": ["incident_trace:7"],
                "reuse_feedback": "reused successfully",
                "confidence": 0.95,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(weak_payload))
            self.run_memory(project, "reflect", "--payload", json.dumps(strong_payload))
            result = self.run_memory(project, "context", "--query", "ArkTS route blank screen 如何定位", "--json")
            data = json.loads(result.stdout)

        self.assertEqual(data["reflections"][0]["id"], 2)
        self.assertGreater(data["reflections"][0]["quality_score"], data["reflections"][1]["quality_score"])
        self.assertGreater(data["reflections"][0]["rerank_score"], data["reflections"][1]["rerank_score"])

    def test_maintain_plan_adds_low_quality_memory_review_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "Old unverified ArkTS route guess",
                "--source",
                "unknown",
                "--confidence",
                "0.1",
            )
            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        actions = [action for action in data["actions"] if action["action"] == "review_low_quality_memory"]
        self.assertEqual(1, len(actions))
        self.assertEqual("semantic", actions[0]["type"])
        self.assertEqual(1, actions[0]["id"])
        self.assertIn("mark_stale", actions[0]["suggested_actions"])
        self.assertEqual(1, data["governance_summary"]["low_quality_memory_reviews"])

    def test_maintain_plan_adds_high_value_experience_review_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            payload = {
                "experience_type": "procedure_experience",
                "task": "Diagnose ArkTS route blank screen",
                "summary": "Route target mismatch was found through incident trace.",
                "lesson": "When ArkTS navigation opens a blank page, inspect router.pushUrl target and page registration first.",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "verification_method": "ran targeted route test",
                "source_cases": ["incident_trace:1"],
                "reuse_feedback": "reused successfully",
                "confidence": 0.9,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(payload))
            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        actions = [action for action in data["actions"] if action["action"] == "review_high_value_experience"]
        self.assertEqual(1, len(actions))
        self.assertEqual("reflection", actions[0]["type"])
        self.assertEqual("procedure_experience", actions[0]["experience_type"])
        self.assertIn("review_for_skill_pattern", actions[0]["suggested_actions"])
        self.assertEqual(1, data["governance_summary"]["high_value_experience_reviews"])

    def test_quality_report_rewards_resolved_incident_trace_evidence_chain(self) -> None:
        from tools.agent_memory_runtime.evidence_chain_quality import enrich_reflections_with_evidence_chains
        from tools.agent_memory_runtime.quality_scoring import build_quality_report
        from tools.agent_memory_runtime.storage import connect, ensure_dirs, resolve_project

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "app"
            project_root.mkdir()
            project = resolve_project(str(project_root), str(self.memory_home(project_root)))
            ensure_dirs(project)
            self.run_memory(project_root, "init")
            with connect(project) as conn:
                trace_id = self.insert_trace_with_link(conn, project.project_id, "resolved")
            reflection = {
                "id": 1,
                "experience_type": "procedure_experience",
                "confidence": 0.9,
                "status": "active",
                "verification_method": "ran route test",
                "source_cases": json.dumps([f"incident_trace:{trace_id}"]),
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "reuse_feedback": "reused successfully",
                "lesson": "Route diagnosis follows incident trace anchors.",
            }

            enriched = enrich_reflections_with_evidence_chains(project, [reflection])
            report = build_quality_report([], enriched, [])

        scored = report["high_value_records"][0]
        self.assertEqual(1.0, scored["evidence_chain_score"])
        self.assertIn("resolved incident trace with linked anchors", scored["evidence_chain_reasons"])

    def test_maintain_plan_reviews_weak_evidence_chain_for_high_value_experience(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            payload = {
                "experience_type": "procedure_experience",
                "task": "Diagnose ArkTS route blank screen",
                "summary": "Good-looking route diagnosis without durable source case.",
                "lesson": "Inspect router.pushUrl target and page registration first.",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "verification_method": "ran targeted route test",
                "source_cases": ["ad_hoc_note:1"],
                "reuse_feedback": "reused successfully",
                "confidence": 0.9,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(payload))
            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        actions = [action for action in data["actions"] if action["action"] == "review_weak_evidence_chain"]
        self.assertEqual(1, len(actions))
        self.assertEqual(1, actions[0]["id"])
        self.assertLess(actions[0]["evidence_chain_score"], 0.6)
        self.assertEqual(1, data["governance_summary"]["weak_evidence_chain_reviews"])
        self.assertEqual(1, data["evidence_chain_summary"]["weak_reflections"])

    def insert_trace_with_link(self, conn: sqlite3.Connection, project_id: str, status: str) -> int:
        cur = conn.execute(
            """
            INSERT INTO incident_traces(
              project_id, trace_key, status, symptom, arkts_scene, diagnosis_summary,
              suspected_chain, resolution, confidence, created_at, updated_at
            )
            VALUES (?, 'trace-test', ?, 'ArkTS route blank screen', 'route', 'route target mismatch',
                    '["router.pushUrl", "pages/Profile"]', 'fixed route target', 0.9,
                    '2026-07-11T00:00:00Z', '2026-07-11T00:00:00Z')
            """,
            (project_id, status),
        )
        trace_id = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO incident_trace_links(
              project_id, trace_id, target_type, target_id, target_key, relation, score, evidence, created_at
            )
            VALUES (?, ?, 'code_log_statement', 42, 'pages/Profile.ets::router.pushUrl',
                    'matched_log', 0.9, 'matched route log', '2026-07-11T00:00:00Z')
            """,
            (project_id, trace_id),
        )
        conn.commit()
        return trace_id
