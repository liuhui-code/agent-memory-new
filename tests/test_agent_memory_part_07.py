# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart07Tests(AgentMemoryTestBase):
    def test_maintain_skill_promotion_status_reports_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Settings page opens blank after route navigation.",
                    "task": "diagnose settings route blank screen",
                    "summary": "The route target was wrong.",
                    "reasoning_summary": "Route and log anchors narrowed the issue.",
                    "context_used": ["query: settings blank route"],
                    "what_worked": ["Search page business term with route terms."],
                    "what_failed": ["Generic blank-screen search was broad."],
                    "hidden_assumptions": ["The blank screen occurred after navigation."],
                    "negative_preconditions": ["Does not apply to static layout visibility issues."],
                    "query_rounds": 2,
                    "trajectory_summary": "Route anchors became useful after the second query round.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["settings", "router.pushUrl", "pages/Settings"],
                    "misleading_followup_terms": ["blank screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/Settings.ets"],
                    "final_verification_path": "Check route registration and reproduce the navigation path.",
                    "related_cases": ["case_settings_route_001"],
                    "verification_method": "Check route registration, log output, and reproduce navigation.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:settings-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                    "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Search generic blank-screen terms only",
                    "repair_action": "Query page business terms, router target, and related log template",
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Profile page opens blank after route navigation.",
                    "task": "diagnose profile route blank screen",
                    "summary": "The profile route registration was mismatched.",
                    "reasoning_summary": "Route anchors and router logs converged quickly.",
                    "context_used": ["query: profile blank route"],
                    "what_worked": ["Combine business page name and route terms."],
                    "what_failed": ["Starting from pure rendering terms."],
                    "hidden_assumptions": ["Navigation reached the target route."],
                    "negative_preconditions": ["Does not apply to local layout overflow."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the route target registration.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
                    "misleading_followup_terms": ["white screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets"],
                    "final_verification_path": "Inspect route registration and replay the same navigation path.",
                    "related_cases": ["case_profile_route_001"],
                    "verification_method": "Check route registration, logs, and navigation replay.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:profile-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "HarmonyOS route blank-screen diagnosis should start from route anchors.",
                    "future_rule": "When a page blanks after navigation, prefer route anchors before layout debugging.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Treat navigation blank screens as generic rendering bugs",
                    "repair_action": "Query page business terms, route target, and router logs first",
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))
            self.run_memory(
                project,
                "maintain-skill-package",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            result = self.run_memory(
                project,
                "maintain-skill-promotion-status",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )
            payload = json.loads(result.stdout)

            self.assertEqual(payload["pattern_name"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(payload["formal_target"], "skills/arkts-route-blank-screen-diagnosis/SKILL.md")
            self.assertIn("package_review_not_completed", payload["promotion_blockers"])
            self.assertIn("promotion_readiness_not_high_enough", payload["promotion_blockers"])
            self.assertFalse(payload["ready_for_manual_promotion"])

    def test_maintain_skill_package_preserves_existing_reviewed_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Settings page opens blank after route navigation.",
                    "task": "diagnose settings route blank screen",
                    "summary": "The route target was wrong.",
                    "reasoning_summary": "Route and log anchors narrowed the issue.",
                    "context_used": ["query: settings blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Search page business term with route terms."],
                    "what_failed": ["Generic blank-screen search was broad."],
                    "hidden_assumptions": ["The blank screen occurred after navigation."],
                    "negative_preconditions": ["Does not apply to static layout visibility issues."],
                    "query_rounds": 2,
                    "trajectory_summary": "Route anchors became useful after the second query round.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["settings", "router.pushUrl", "pages/Settings"],
                    "misleading_followup_terms": ["blank screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/Settings.ets"],
                    "final_verification_path": "Check route registration and reproduce the navigation path.",
                    "related_cases": ["case_settings_route_001"],
                    "verification_method": "Check route registration, log output, and reproduce navigation.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:settings-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                    "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Search generic blank-screen terms only",
                    "repair_action": "Query page business terms, router target, and related log template",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Profile page opens blank after route navigation.",
                    "task": "diagnose profile route blank screen",
                    "summary": "The profile route registration was mismatched.",
                    "reasoning_summary": "Route anchors and router logs converged quickly.",
                    "context_used": ["query: profile blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Combine business page name and route terms."],
                    "what_failed": ["Starting from pure rendering terms."],
                    "hidden_assumptions": ["Navigation reached the target route."],
                    "negative_preconditions": ["Does not apply to local layout overflow."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the route target registration.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
                    "misleading_followup_terms": ["white screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets"],
                    "final_verification_path": "Inspect route registration and replay the same navigation path.",
                    "related_cases": ["case_profile_route_001"],
                    "verification_method": "Check route registration, logs, and navigation replay.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:profile-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "HarmonyOS route blank-screen diagnosis should start from route anchors.",
                    "future_rule": "When a page blanks after navigation, prefer route anchors before layout debugging.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Treat navigation blank screens as generic rendering bugs",
                    "repair_action": "Query page business terms, route target, and router logs first",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            self.run_memory(
                project,
                "maintain-skill-package",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            package_path = project / "skills" / "_candidates" / "arkts-route-blank-screen-diagnosis" / "SKILL.md"
            package_path.write_text(
                package_path.read_text(encoding="utf-8")
                .replace('review_status: "pending_review"', 'review_status: "approved"')
                .replace('reviewer: ""', 'reviewer: "Bob"'),
                encoding="utf-8",
            )
            preserved_content = package_path.read_text(encoding="utf-8")

            result = self.run_memory(
                project,
                "maintain-skill-package",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["write_action"], "preserved_existing_reviewed_artifact")
            self.assertIn("did not overwrite", payload["warning"])
            self.assertEqual(payload["existing_review_status"], "approved")
            self.assertEqual(payload["existing_reviewer"], "Bob")
            self.assertEqual(payload["package_review_status"], "approved")
            self.assertEqual(payload["package_reviewer"], "Bob")
            self.assertEqual(package_path.read_text(encoding="utf-8"), preserved_content)

    def test_maintain_promote_reflection_to_semantic_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "durable workflow",
                "--lesson",
                "Runtime changes need parser tests and skill docs.",
            )

            result = self.run_memory(
                project,
                "maintain-promote",
                "--reflection-id",
                "1",
                "--fact",
                "Runtime changes must update parser tests and skill docs.",
                "--json",
            )

            payload = json.loads(result.stdout)
            facts = self.list_records(project, "semantic")
            reflection = self.list_records(project, "reflection")[0]
            self.assertEqual(payload["semantic_fact_id"], 1)
            self.assertEqual(facts[0]["source"], "reflection:1")
            self.assertIsNotNone(reflection["reviewed_at"])

    def test_vault_export_writes_reflection_quality_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "thin reflection",
                "--lesson",
                "Be careful.",
            )

            self.run_memory(project, "vault-export")

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Reflection Quality.md"
            self.assertTrue(dashboard.exists())
            self.assertIn("missing_trigger_condition", dashboard.read_text(encoding="utf-8"))

    def test_vault_export_writes_experience_candidates_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "task_type": "diagnosis",
                "outcome": "success",
                "problem": "Settings page opens blank after route navigation.",
                "task": "diagnose settings route blank screen",
                "summary": "The route target was wrong.",
                "reasoning_summary": "Route and log anchors narrowed the issue.",
                "context_used": ["query: settings blank route", "log: router.pushUrl failed"],
                "what_worked": ["Search page business term with route terms."],
                "what_failed": ["Generic blank-screen search was broad."],
                "hidden_assumptions": ["The blank screen occurred after navigation."],
                "negative_preconditions": ["Does not apply to static layout visibility issues."],
                "verification_method": "Check route registration, log output, and reproduce navigation.",
                "reuse_feedback": "helped",
                "source_cases": ["episode:settings-route-fix", "file: pages/Home.ets"],
                "skill_candidate": "arkts-route-blank-screen-diagnosis",
                "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                "scope": "HarmonyOS ArkTS routing",
                "evidence": "pages/Home.ets router.pushUrl",
                "trigger_condition": "Page blanks after route navigation",
                "anti_pattern": "Search generic blank-screen terms only",
                "repair_action": "Query page business terms, router target, and related log template",
                "applies_to": "ArkTS route target failures",
                "does_not_apply_to": "Non-navigation rendering bugs",
                "confidence": 0.9,
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            self.run_memory(project, "vault-export")

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Experience Candidates.md"
            index = self.project_memory_dir(project) / "vault" / "index.md"
            self.assertTrue(dashboard.exists())
            content = dashboard.read_text(encoding="utf-8")
            self.assertIn("arkts-route-blank-screen-diagnosis", content)
            self.assertIn("Check route registration", content)
            self.assertIn("episode:settings-route-fix", content)
            self.assertIn("[[Governance/Experience Candidates]]", index.read_text(encoding="utf-8"))

    def test_vault_export_writes_reflection_reuse_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "reflect", "--task", "old diagnosis", "--lesson", "Route bugs need route anchors.")
            self.run_memory(
                project,
                "reflect",
                "--task",
                "new diagnosis",
                "--lesson",
                "The old diagnosis partially helped.",
                "--used-reflection-ids",
                "1",
                "--reflection-outcome",
                "partial",
            )

            self.run_memory(project, "vault-export")

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Reflection Reuse.md"
            index = self.project_memory_dir(project) / "vault" / "index.md"
            self.assertTrue(dashboard.exists())
            content = dashboard.read_text(encoding="utf-8")
            self.assertIn("reused reflection #1", content)
            self.assertIn("applying reflection #2", content)
            self.assertIn("partial", content)
            self.assertIn("[[Governance/Reflection Reuse]]", index.read_text(encoding="utf-8"))
