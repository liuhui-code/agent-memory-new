# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart03Tests(AgentMemoryTestBase):
    def test_search_matches_structured_reflection_payload_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "task_type": "design",
                "outcome": "failure",
                "problem": "Image resource on product card does not appear.",
                "task": "design product card image fix",
                "lesson": "Resource display fixes need business resource names and $r lookup terms.",
                "future_rule": "When product image resources fail, query the product card business terms and app.media references.",
                "reasoning_summary": "The failed plan ignored app.media and searched only UI component names.",
                "context_used": ["query: product card image", "file: pages/ProductCard.ets"],
                "what_worked": ["Adding app.media terms found the right code file."],
                "what_failed": ["Searching only Card component was too broad."],
                "trigger_condition": "Business image or icon resource does not render",
                "repair_action": "Search by business noun plus resource/app.media/$r terms",
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(project, "search", "--query", "商品卡片图片资源不显示", "--json")
            reflections = json.loads(result.stdout)["reflections"]

            self.assertEqual(reflections[0]["task_type"], "design")
            self.assertEqual(reflections[0]["outcome"], "failure")
            self.assertEqual(reflections[0]["problem"], "Image resource on product card does not appear.")

    def test_context_firewall_separates_experience_lanes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            procedure = {
                "experience_type": "procedure_experience",
                "task_type": "diagnosis",
                "outcome": "success",
                "task": "diagnose profile route blank screen",
                "lesson": "Profile route blank screen diagnosis should start from route anchors.",
                "future_rule": "When profile navigation blanks, query route anchors and router logs first.",
                "trigger_condition": "Profile page blanks after route navigation.",
                "repair_action": "Query profile route anchors and inspect router target registration.",
                "verification_method": "Confirm route registration and reproduce navigation.",
                "source_cases": ["episode:profile-route"],
                "scope": "HarmonyOS route diagnosis",
                "evidence": "pages/Profile.ets router.pushUrl",
            }
            correction = {
                "experience_type": "correction_experience",
                "task_type": "diagnosis",
                "outcome": "success",
                "task": "correct profile route overreach",
                "lesson": "Do not treat every profile blank screen as a route issue.",
                "future_rule": "When session invalid appears, auth evidence should guard against route-first diagnosis.",
                "trigger_condition": "Runtime evidence includes session invalid.",
                "repair_action": "Check auth/session logs before applying route diagnosis.",
                "negative_preconditions": ["Do not apply when no auth/session evidence exists."],
                "misleading_followup_terms": ["route blank", "layout issue"],
                "what_failed": ["Route-first memory misled the diagnosis."],
                "verification_method": "Confirm runtime slice has session invalid.",
                "source_cases": ["runtime_log:profile-session"],
                "scope": "HarmonyOS auth diagnosis",
                "evidence": "session invalid log",
            }
            semantic_patch = {
                "experience_type": "semantic_patch_experience",
                "task_type": "workflow",
                "outcome": "success",
                "task": "patch profile load semantics",
                "lesson": "Profile load semantics should mention session validation.",
                "anchor_type": "code_symbol",
                "anchor_key": "pages/Profile.ets::loadProfile",
                "semantic_field": "business_summary",
                "proposed_value": "loads profile data and validates session state",
                "verification_method": "Inspect loadProfile and session log.",
                "trigger_condition": "Business summary omits session validation.",
                "repair_action": "Patch business_summary through learn-business.",
                "evidence": "pages/Profile.ets loadProfile",
            }
            for payload in (procedure, correction, semantic_patch):
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            procedure_context = self.run_memory(project, "context", "--query", "如何诊断 profile route blank screen", "--json")
            procedure_payload = json.loads(procedure_context.stdout)
            self.assertEqual(procedure_payload["memory_intent"], "procedure_reuse")
            self.assertEqual(procedure_payload["reflections"][0]["experience_type"], "procedure_experience")
            self.assertTrue(
                any(note["experience_type"] == "correction_experience" for note in procedure_payload["blocked_memory_notes"])
            )

            semantic_context = self.run_memory(project, "context", "--query", "profile loadProfile 业务语义 business_summary", "--json")
            semantic_payload = json.loads(semantic_context.stdout)
            self.assertEqual(semantic_payload["memory_intent"], "semantic_lookup")
            self.assertTrue(
                any("validates session" in note["proposed_value"] for note in semantic_payload["semantic_patch_notes"])
            )

            correction_context = self.run_memory(project, "context", "--query", "profile route 误导 纠错", "--json")
            correction_payload = json.loads(correction_context.stdout)
            self.assertEqual(correction_payload["memory_intent"], "correction_guard")
            self.assertTrue(correction_payload["correction_guards"])
            self.assertEqual(correction_payload["correction_guards"][0]["experience_type"], "correction_experience")

    def test_reflect_updates_used_reflection_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "old lesson",
                "--lesson",
                "Use maintain-plan before memory mutations.",
            )

            self.run_memory(
                project,
                "reflect",
                "--task",
                "new task",
                "--lesson",
                "The old lesson helped this task.",
                "--used-reflection-ids",
                "1",
                "--reflection-outcome",
                "helped",
            )

            old_reflection = sorted(self.list_records(project, "reflection"), key=lambda row: row["id"])[0]
            self.assertEqual(old_reflection["applied_count"], 1)
            self.assertEqual(old_reflection["last_outcome"], "helped")
            self.assertIsNotNone(old_reflection["last_applied_at"])

    def test_reflect_records_reuse_feedback_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "reflect", "--task", "route lesson", "--lesson", "Route bugs need route anchors.")
            self.run_memory(project, "reflect", "--task", "log lesson", "--lesson", "Log bugs need log anchors.")

            self.run_memory(
                project,
                "reflect",
                "--task",
                "combined diagnosis",
                "--lesson",
                "The route lesson partially helped and the log lesson also mattered.",
                "--used-reflection-ids",
                "1,2",
                "--reflection-outcome",
                "partial",
            )

            events = sorted(self.list_records(project, "reflection-reuse"), key=lambda row: row["reused_reflection_id"])
            self.assertEqual([event["reused_reflection_id"] for event in events], [1, 2])
            self.assertEqual([event["applying_reflection_id"] for event in events], [3, 3])
            self.assertEqual([event["outcome"] for event in events], ["partial", "partial"])
            self.assertEqual(events[0]["task"], "combined diagnosis")

    def test_reflect_review_reports_missing_actionability(self) -> None:
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

            result = self.run_memory(project, "reflect-review", "--json")
            payload = json.loads(result.stdout)
            item = payload["reflections"][0]

            self.assertEqual(item["id"], 1)
            self.assertIn("missing_trigger_condition", item["issues"])
            self.assertIn("missing_repair_action", item["issues"])
            self.assertEqual(item["suggested_action"], "rewrite")

    def test_maintain_plan_includes_reflection_quality_actions(self) -> None:
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

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            self.assertTrue(any(action["action"] == "rewrite_reflection" and action["id"] == 1 for action in actions))

    def test_maintain_plan_marks_misleading_reflection_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "bad lesson",
                "--lesson",
                "Use stale data first.",
            )
            self.run_memory(
                project,
                "reflect",
                "--task",
                "later task",
                "--lesson",
                "That lesson misled the task.",
                "--used-reflection-ids",
                "1",
                "--reflection-outcome",
                "misleading",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            self.assertTrue(any(action["action"] == "mark_stale" and action["id"] == 1 for action in actions))

    def test_maintain_plan_promotes_complete_experience_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
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

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            action = next(
                action for action in actions
                if action["action"] == "promote_experience_candidate" and action["id"] == 1
            )
            self.assertEqual(action["skill_candidate"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(action["experience_type"], "procedure_experience")
            self.assertEqual(action["useful_followup_focus"], "route")
            self.assertEqual(json.loads(action["useful_followup_terms"])[1], "router.pushUrl")
            self.assertEqual(action["query_rounds"], 2)
            self.assertIn("verification_method", action["candidate_fields"])
            self.assertIsNone(action["command"])

    def test_maintain_plan_routes_correction_experience_to_learning_governance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "experience_type": "correction_experience",
                "task_type": "workflow",
                "outcome": "success",
                "problem": "Profile page file semantics were written as a service.",
                "task": "correct profile file business meaning",
                "summary": "Re-read the file and corrected the business responsibility.",
                "reasoning_summary": "The file is a page entry, not a service layer module.",
                "context_used": ["file: pages/Profile.ets"],
                "what_worked": ["Compare route role and page build method."],
                "what_failed": ["Trusting the first broad summary."],
                "hidden_assumptions": ["The file is part of page navigation flow."],
                "negative_preconditions": ["Does not apply to plain utility modules."],
                "query_rounds": 2,
                "trajectory_summary": "The second review step compared route usage with build composition and exposed the wrong page-vs-service summary.",
                "useful_followup_focus": "route",
                "useful_followup_terms": ["Profile", "build()", "route"],
                "misleading_followup_terms": ["service"],
                "inspection_targets": ["pages/Profile.ets"],
                "final_verification_path": "Inspect build() ownership, route usage, and UI composition in the current file.",
                "related_cases": ["case_profile_semantic_fix_001"],
                "verification_method": "Check build method, route usage, and UI composition.",
                "reuse_feedback": "candidate until reused",
                "source_cases": ["file: pages/Profile.ets"],
                "lesson": "Correct learned business semantics when page files were summarized as services.",
                "future_rule": "When a file owns UI composition and route flow, classify it as page-facing business logic first.",
                "scope": "learn-business semantic correction",
                "evidence": "pages/Profile.ets build() and route usage",
                "trigger_condition": "Learned business summary conflicts with current source role.",
                "repair_action": "Rewrite the file business summary and terms from current source.",
                "applies_to": "semantic correction during learn-business review",
                "does_not_apply_to": "procedure diagnosis for runtime bugs",
                "confidence": 0.9,
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            action = next(
                action for action in actions
                if action["action"] == "review_correction_experience" and action["id"] == 1
            )
            self.assertEqual(action["experience_type"], "correction_experience")
            self.assertEqual(action["governance_path"], "learn_semantic_repair")
            self.assertEqual(action["useful_followup_focus"], "route")
            self.assertIn("build()", json.loads(action["useful_followup_terms"])[1])
            self.assertEqual(action["correction_targets"]["file_paths"], ["pages/Profile.ets"])
            self.assertIn("service", action["correction_targets"]["misleading_terms"])
            self.assertEqual(action["learning_rule_draft"]["target_memory_type"], "code_wiki_business_semantics")
            self.assertIn("Learned business summary conflicts with current source role.", action["learning_rule_draft"]["correction_trigger"])
            self.assertIn("Check build method, route usage, and UI composition.", action["learning_rule_draft"]["source_evidence"][1])
            self.assertEqual(action["command_template"], "python tools/agent_memory.py learn-business --project . --payload '<json>' --json")
            self.assertEqual(action["learn_business_payload_template"]["files"][0]["file_path"], "pages/Profile.ets")
            self.assertIn("Profile", action["learn_business_payload_template"]["files"][0]["hint_terms"][0])
            self.assertIn("Rewrite the learn-business payload for the affected records", action["workflow_steps"][2])

    def test_maintain_plan_surfaces_semantic_patch_and_retrieval_interference_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            semantic_patch = {
                "experience_type": "semantic_patch_experience",
                "task_type": "workflow",
                "outcome": "success",
                "task": "patch profile load semantics",
                "lesson": "Profile load semantics should mention session validation.",
                "anchor_type": "code_symbol",
                "anchor_key": "pages/Profile.ets::loadProfile",
                "semantic_field": "business_summary",
                "existing_value": "loads profile page UI",
                "proposed_value": "loads profile data and validates session state",
                "patch_reason": "Runtime logs and caller show session validation before rendering.",
                "verification_method": "Inspect loadProfile and session log.",
                "trigger_condition": "Business summary omits session validation.",
                "repair_action": "Patch business_summary through learn-business.",
                "evidence": "pages/Profile.ets loadProfile",
                "confidence": 0.9,
            }
            misleading_correction = {
                "experience_type": "correction_experience",
                "task_type": "diagnosis",
                "outcome": "success",
                "task": "guard profile route overreach",
                "lesson": "Route-first diagnosis can be misleading for auth failures.",
                "future_rule": "Use auth/session evidence as a guard before route diagnosis.",
                "trigger_condition": "Profile blank screen includes session invalid logs.",
                "repair_action": "Check auth/session logs before route anchors.",
                "negative_preconditions": ["Do not apply when no runtime auth evidence exists."],
                "misleading_followup_terms": ["route blank"],
                "what_failed": ["Route-first memory misled diagnosis."],
                "verification_method": "Confirm runtime slice has session invalid.",
                "reuse_feedback": "misleading until trigger is tightened",
                "source_cases": ["runtime_log:profile-session"],
                "scope": "HarmonyOS auth diagnosis",
                "evidence": "session invalid log",
                "misleading_score": 0.8,
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(semantic_patch, ensure_ascii=False))
            self.run_memory(project, "reflect", "--payload", json.dumps(misleading_correction, ensure_ascii=False))

            result = self.run_memory(project, "maintain-plan", "--json")
            payload = json.loads(result.stdout)
            actions = payload["actions"]

            semantic_action = next(action for action in actions if action["action"] == "review_semantic_patch")
            self.assertEqual(semantic_action["experience_type"], "semantic_patch_experience")
            self.assertEqual(semantic_action["anchor_type"], "code_symbol")
            self.assertEqual(semantic_action["semantic_field"], "business_summary")
            self.assertIn("validates session", semantic_action["proposed_value"])
            self.assertEqual(semantic_action["learn_business_payload_template"]["files"][0]["symbols"][0]["symbol"], "loadProfile")

            interference_action = next(action for action in actions if action["action"] == "review_retrieval_interference")
            self.assertEqual(interference_action["experience_type"], "correction_experience")
            self.assertEqual(interference_action["misleading_score"], 0.8)
            self.assertIn("tighten trigger_condition", interference_action["suggested_actions"])
            self.assertEqual(payload["summary"]["semantic_patch_reviews"], 1)
            self.assertEqual(payload["summary"]["retrieval_interference_reviews"], 1)
            self.assertEqual(payload["governance_summary"]["semantic_patch_reviews"], 1)
            self.assertEqual(payload["governance_summary"]["retrieval_interference_reviews"], 1)
