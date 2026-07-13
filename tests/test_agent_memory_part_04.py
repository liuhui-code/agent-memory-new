# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart04Tests(AgentMemoryTestBase):
    def test_maintain_plan_surfaces_new_old_procedure_experience_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            old_payload = {
                "experience_type": "procedure_experience",
                "task_type": "diagnosis",
                "outcome": "success",
                "task": "diagnose profile blank screen",
                "lesson": "Start with route anchors for post-navigation blank screens.",
                "future_rule": "When a page blanks after navigation, inspect route target registration first.",
                "trigger_condition": "Page blanks after navigation.",
                "repair_action": "Check route registration and router target before auth investigation.",
                "verification_method": "Reproduce navigation and inspect route target.",
                "inspection_targets": ["pages/Profile.ets", "router_map.json"],
                "scope": "HarmonyOS route diagnosis",
                "evidence": "router.pushUrl call and route registry",
                "hidden_assumptions": ["The failure starts after navigation."],
                "negative_preconditions": ["Does not apply when auth/session logs already fail before route change."],
                "reuse_feedback": "candidate until reused",
                "source_cases": ["episode:profile-route-fix"],
            }
            new_payload = {
                "experience_type": "procedure_experience",
                "task_type": "diagnosis",
                "outcome": "success",
                "task": "diagnose profile blank screen with auth evidence",
                "lesson": "Auth/session evidence should override route-first diagnosis for the same symptom.",
                "future_rule": "When a page blanks after navigation and session invalid logs appear, check auth/session first.",
                "trigger_condition": "Page blanks after navigation.",
                "repair_action": "Check session invalid logs and auth state before route registration.",
                "verification_method": "Confirm session invalid logs exist in the runtime slice.",
                "inspection_targets": ["pages/Profile.ets", "router_map.json", "hilog: session invalid"],
                "scope": "HarmonyOS route diagnosis",
                "evidence": "session invalid log and auth state handling",
                "hidden_assumptions": ["The symptom still appears after navigation."],
                "negative_preconditions": ["Does not apply when there is no auth/session runtime evidence."],
                "reuse_feedback": "candidate until reused",
                "source_cases": ["episode:profile-auth-fix"],
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(old_payload, ensure_ascii=False))
            self.run_memory(project, "reflect", "--payload", json.dumps(new_payload, ensure_ascii=False))

            result = self.run_memory(project, "maintain-plan", "--json")
            payload = json.loads(result.stdout)
            actions = payload["actions"]

            conflict_action = next(action for action in actions if action["action"] == "review_experience_conflict")
            self.assertEqual(conflict_action["conflict_kind"], "procedure_rule_conflict")
            self.assertEqual(conflict_action["older_reflection_id"], 1)
            self.assertEqual(conflict_action["newer_reflection_id"], 2)
            self.assertEqual(conflict_action["experience_type"], "procedure_experience")
            self.assertIn("Page blanks after navigation.", conflict_action["shared_trigger_condition"])
            self.assertIn("route registration", conflict_action["older_repair_action"])
            self.assertIn("session invalid logs", conflict_action["newer_repair_action"])
            self.assertIn("review which trigger boundaries are still valid", conflict_action["suggested_actions"][0])
            self.assertEqual(payload["summary"]["experience_conflict_reviews"], 1)
            self.assertEqual(payload["governance_summary"]["experience_conflict_reviews"], 1)

    def test_maintain_plan_surfaces_new_old_semantic_patch_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            old_patch = {
                "experience_type": "semantic_patch_experience",
                "task_type": "workflow",
                "outcome": "success",
                "task": "patch profile load semantics",
                "lesson": "Profile load semantics should mention route hydration.",
                "anchor_type": "code_symbol",
                "anchor_key": "pages/Profile.ets::loadProfile",
                "semantic_field": "business_summary",
                "existing_value": "loads profile page UI",
                "proposed_value": "loads profile data and hydrates route-bound page state",
                "patch_reason": "Initial review focused on route hydration before render.",
                "verification_method": "Inspect loadProfile caller and route state handling.",
                "trigger_condition": "Business summary omits route hydration.",
                "repair_action": "Patch business_summary through learn-business.",
                "evidence": "pages/Profile.ets loadProfile",
                "confidence": 0.82,
            }
            new_patch = {
                "experience_type": "semantic_patch_experience",
                "task_type": "workflow",
                "outcome": "success",
                "task": "patch profile load semantics again",
                "lesson": "Profile load semantics should mention session validation instead of route hydration.",
                "anchor_type": "code_symbol",
                "anchor_key": "pages/Profile.ets::loadProfile",
                "semantic_field": "business_summary",
                "existing_value": "loads profile page UI",
                "proposed_value": "loads profile data and validates session state before rendering",
                "patch_reason": "Later runtime review showed session validation is the decisive business step.",
                "verification_method": "Inspect loadProfile and session invalid log path.",
                "trigger_condition": "Business summary omits session validation.",
                "repair_action": "Patch business_summary through learn-business.",
                "evidence": "pages/Profile.ets loadProfile plus session invalid log",
                "confidence": 0.91,
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(old_patch, ensure_ascii=False))
            self.run_memory(project, "reflect", "--payload", json.dumps(new_patch, ensure_ascii=False))

            result = self.run_memory(project, "maintain-plan", "--json")
            payload = json.loads(result.stdout)
            actions = payload["actions"]

            conflict_action = next(
                action
                for action in actions
                if action["action"] == "review_experience_conflict"
                and action["conflict_kind"] == "semantic_patch_conflict"
            )
            self.assertEqual(conflict_action["older_reflection_id"], 1)
            self.assertEqual(conflict_action["newer_reflection_id"], 2)
            self.assertEqual(conflict_action["anchor_key"], "pages/Profile.ets::loadProfile")
            self.assertEqual(conflict_action["semantic_field"], "business_summary")
            self.assertIn("hydrates route-bound page state", conflict_action["older_proposed_value"])
            self.assertIn("validates session state", conflict_action["newer_proposed_value"])
            self.assertEqual(payload["summary"]["experience_conflict_reviews"], 1)

    def test_maintain_plan_clusters_procedure_experiences_into_skill_pattern_candidate(self) -> None:
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

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            action = next(action for action in actions if action["action"] == "review_skill_pattern_candidate")
            self.assertEqual(action["pattern_name"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(action["experience_type"], "procedure_experience")
            self.assertEqual(action["supporting_reflection_ids"], [1, 2])
            self.assertEqual(action["supporting_count"], 2)
            self.assertIn("route", action["common_followup_focus"])
            self.assertIn("router.pushUrl", action["common_query_terms"])
            self.assertIn("case_profile_route_001", action["supporting_cases"])
            self.assertIn("query route anchors", action["common_steps"])
            self.assertIn("inspect route target and page registration", action["common_steps"])
            self.assertIn("Check route registration and reproduce the navigation path.", action["common_stop_conditions"])
            self.assertIn("Search generic blank-screen terms only", action["failure_modes"])
            self.assertIn("verification checklist", action["expected_outputs"])
            self.assertEqual(action["draft_path"], "docs/skill-candidates/arkts-route-blank-screen-diagnosis.md")
            self.assertEqual(action["draft_status"], "not_written")
            self.assertEqual(action["draft_review_status"], "")
            self.assertEqual(action["package_path"], "skills/_candidates/arkts-route-blank-screen-diagnosis/SKILL.md")
            self.assertEqual(action["package_status"], "not_written")
            self.assertEqual(action["package_review_status"], "")
            self.assertEqual(action["promotion_checklist_path"], "skills/_candidates/arkts-route-blank-screen-diagnosis/PROMOTION.md")
            self.assertEqual(action["promotion_checklist_status"], "not_written")
            self.assertEqual(action["promotion_stage"], "clustered")
            self.assertEqual(action["promotion_readiness"], "review_candidate")
            self.assertGreaterEqual(action["quality_score"], 5)
            self.assertIn("has_minimum_supporting_reflections", action["quality_reasons"])
            self.assertEqual(action["helped_reuse_count"], 2)
            self.assertEqual(action["partial_reuse_count"], 0)
            self.assertEqual(action["misleading_reuse_count"], 0)
            self.assertEqual(action["anchor_health"], "missing")
            self.assertIn("pages/Home.ets", action["missing_anchor_paths"])
            self.assertIn("Write the draft artifact first", action["review_guidance"][0])
            self.assertIn("maintain-skill-draft", action["write_command_template"])
            self.assertIn("maintain-skill-package", action["package_command_template"])
            self.assertIn("# Skill Candidate: arkts-route-blank-screen-diagnosis", action["draft_markdown"])
            self.assertIn("## Trigger Cluster", action["draft_markdown"])
            self.assertIn("## Common Steps", action["draft_markdown"])
            self.assertIn("## Common Stop Conditions", action["draft_markdown"])
            self.assertIn("## Failure Modes", action["draft_markdown"])

    def test_maintain_plan_clusters_runtime_incidents_into_strategy_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "个人资料页空白，登录态异常。",
                    "task": "diagnose profile blank via runtime logs",
                    "summary": "Runtime logs showed profile failure and invalid session.",
                    "reasoning_summary": "Runtime evidence was compressed into matched events, bounded slices, and a lightweight candidate chain before diagnosis.",
                    "context_used": ["query: 个人资料页空白，登录态异常", "log_event: load profile failed", "slice: 10:21:10 -> 10:21:13"],
                    "what_worked": ["Use code-log memory to build a log_search_plan first.", "Inspect bounded runtime log slices instead of scanning the full raw log."],
                    "what_failed": ["Earlier diagnosis leaned toward a route/navigation cause."],
                    "hidden_assumptions": ["The failure happened after the page entered and requested profile data."],
                    "negative_preconditions": ["Does not apply when there is no runtime evidence from the profile flow."],
                    "query_rounds": 1,
                    "trajectory_summary": "profile_load_started -> profile_load_failed -> session_invalid -> navigate_login",
                    "useful_followup_focus": "log",
                    "useful_followup_terms": ["load profile failed", "session invalid", "401", "ProfilePage"],
                    "misleading_followup_terms": ["blank screen", "route issue"],
                    "inspection_targets": ["pages/Profile.ets", "ProfilePage", "load profile failed"],
                    "final_verification_path": "Confirm 401 and session invalid in the dominant runtime slice, then inspect the profile load path.",
                    "related_cases": ["case_runtime_profile_auth_001"],
                    "verification_method": "Confirm the dominant runtime slice against profile code-log anchors and reproduce the login-to-profile path.",
                    "reuse_feedback": "helped",
                    "source_cases": ["runtime_log:profile_blank_auth", "session:session_001", "episode:profile-auth-incident"],
                    "skill_candidate": "arkts-auth-session-diagnosis",
                    "lesson": "For profile blank incidents, check runtime auth/session evidence before route debugging.",
                    "future_rule": "When profile pages load blank, start with auth/session log anchors and only then inspect route paths.",
                    "scope": "HarmonyOS runtime log diagnosis",
                    "evidence": "runtime log slice with 401 + session invalid",
                    "trigger_condition": "Profile page is blank after login or page entry",
                    "anti_pattern": "Treat profile blank as a generic route problem without runtime evidence.",
                    "repair_action": "Query log anchors, inspect dominant auth/session slices, then inspect the profile load path.",
                    "applies_to": "Auth and session related runtime incidents",
                    "does_not_apply_to": "Pure rendering bugs with no auth/runtime signals",
                    "confidence": 0.92,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "登录后个人中心没数据，怀疑 session 失效。",
                    "task": "diagnose personal-center no-data via runtime logs",
                    "summary": "Runtime logs again pointed to auth/session failure before any route issue.",
                    "reasoning_summary": "Runtime evidence was compressed into matched events, bounded slices, and a lightweight candidate chain before diagnosis.",
                    "context_used": ["query: 登录后个人中心没数据，怀疑 session 失效", "log_event: session invalid", "slice: 11:02:14 -> 11:02:18"],
                    "what_worked": ["Use code-log memory to build a log_search_plan first.", "Inspect bounded runtime log slices instead of scanning the full raw log."],
                    "what_failed": ["Earlier diagnosis leaned toward a route/navigation cause."],
                    "hidden_assumptions": ["The page had already entered the profile fetch flow."],
                    "negative_preconditions": ["Does not apply when there is no profile request or session evidence."],
                    "query_rounds": 1,
                    "trajectory_summary": "profile_load_started -> profile_load_failed -> session_invalid -> navigate_login",
                    "useful_followup_focus": "log",
                    "useful_followup_terms": ["session invalid", "load profile failed", "401", "SessionManager"],
                    "misleading_followup_terms": ["route blank", "layout issue"],
                    "inspection_targets": ["pages/Profile.ets", "SessionManager", "load profile failed"],
                    "final_verification_path": "Confirm session invalid and failed profile load in the dominant runtime slice, then inspect the auth/session handling path.",
                    "related_cases": ["case_runtime_profile_auth_002"],
                    "verification_method": "Confirm the dominant runtime slice against auth/session code-log anchors and reproduce the login-to-profile path.",
                    "reuse_feedback": "helped",
                    "source_cases": ["runtime_log:profile_blank_auth", "session:session_002", "episode:profile-auth-incident-2"],
                    "skill_candidate": "arkts-auth-session-diagnosis",
                    "lesson": "For personal-center no-data incidents, auth/session logs are often stronger than route hypotheses.",
                    "future_rule": "When profile pages have no data after login, prioritize auth/session log anchors before route inspection.",
                    "scope": "HarmonyOS runtime log diagnosis",
                    "evidence": "runtime log slice with failed profile load and invalid session",
                    "trigger_condition": "Profile page has no data after login or page entry",
                    "anti_pattern": "Start with route debugging before checking auth/session runtime evidence.",
                    "repair_action": "Query log anchors, inspect dominant auth/session slices, then inspect the auth/session handling path.",
                    "applies_to": "Auth and session related runtime incidents",
                    "does_not_apply_to": "Pure rendering bugs with no auth/runtime signals",
                    "confidence": 0.92,
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            action = next(action for action in actions if action["action"] == "review_incident_strategy_candidate")
            self.assertEqual(action["strategy_name"], "log-auth-session-profile-blank-diagnosis")
            self.assertEqual(action["experience_type"], "procedure_experience")
            self.assertEqual(action["supporting_reflection_ids"], [1, 2])
            self.assertIn("log", action["common_followup_focus"])
            self.assertIn("load profile failed", action["common_log_events"])
            self.assertIn("session invalid", action["common_log_events"])
            self.assertIn("Use code-log memory to build a log_search_plan first.", action["recommended_steps"])
            self.assertIn("Inspect bounded runtime log slices instead of scanning the full raw log.", action["recommended_steps"])
            self.assertIn("Earlier diagnosis leaned toward a route/navigation cause.", action["misleading_signals"])
            self.assertEqual(action["draft_path"], "docs/incident-strategies/log-auth-session-profile-blank-diagnosis.md")
            self.assertIn("maintain-incident-strategy-draft", action["write_command_template"])
            self.assertIn("# Incident Strategy: log-auth-session-profile-blank-diagnosis", action["draft_markdown"])

    def test_maintain_plan_surfaces_log_design_gap_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "个人资料页空白，登录态异常。",
                    "task": "diagnose profile blank via runtime logs",
                    "summary": "Runtime logs showed profile failure and invalid session.",
                    "reasoning_summary": "Runtime evidence was compressed into matched events, bounded slices, and a lightweight candidate chain before diagnosis.",
                    "context_used": ["query: 个人资料页空白，登录态异常", "log_event: load profile failed", "slice: 10:21:10 -> 10:21:13"],
                    "what_worked": [
                        "Use code-log memory to build a log_search_plan first.",
                        "Inspect bounded runtime log slices instead of scanning the full raw log.",
                        "Use the dominant event combination session invalid + load profile failed to narrow the diagnosis path.",
                    ],
                    "what_failed": ["Earlier diagnosis leaned toward a route/navigation cause."],
                    "hidden_assumptions": ["The failure happened after profile loading began."],
                    "negative_preconditions": ["Does not apply when no auth/session evidence is present."],
                    "query_rounds": 1,
                    "trajectory_summary": "profile_load_started -> profile_load_failed -> session_invalid -> navigate_login",
                    "useful_followup_focus": "log",
                    "useful_followup_terms": ["load profile failed", "session invalid", "401", "ProfilePage"],
                    "misleading_followup_terms": ["blank screen", "route issue"],
                    "inspection_targets": ["pages/Profile.ets", "ProfilePage", "load profile failed"],
                    "final_verification_path": "Confirm 401 and session invalid in the dominant runtime slice, then inspect the profile load path.",
                    "verification_method": "Confirm the dominant runtime slice against profile code-log anchors and reproduce the login-to-profile path.",
                    "reuse_feedback": "helped",
                    "source_cases": ["runtime_log:profile_blank_auth", "session:session_001", "episode:profile-auth-incident"],
                    "lesson": "For profile blank incidents, check runtime auth/session evidence before route debugging.",
                    "future_rule": "When profile pages load blank, start with auth/session log anchors and only then inspect route paths.",
                    "evidence": "candidate_chain: profile_load_started -> profile_load_failed -> session_invalid; top_slice: 10:21:10 -> 10:21:13",
                    "repair_action": "Inspect the dominant runtime slice first, then confirm auth/session handling in source files.",
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "登录后个人中心没数据，怀疑 session 失效。",
                    "task": "diagnose personal-center no-data via runtime logs",
                    "summary": "Runtime logs again pointed to auth/session failure before any route issue.",
                    "reasoning_summary": "Runtime evidence was compressed into matched events, bounded slices, and a lightweight candidate chain before diagnosis.",
                    "context_used": ["query: 登录后个人中心没数据，怀疑 session 失效", "log_event: session invalid", "slice: 11:02:14 -> 11:02:18"],
                    "what_worked": [
                        "Use code-log memory to build a log_search_plan first.",
                        "Inspect bounded runtime log slices instead of scanning the full raw log.",
                        "Use the dominant event combination session invalid + load profile failed to narrow the diagnosis path.",
                    ],
                    "what_failed": ["Earlier diagnosis leaned toward a route/navigation cause."],
                    "hidden_assumptions": ["The page had already entered the profile fetch flow."],
                    "negative_preconditions": ["Does not apply when there is no profile request or session evidence."],
                    "query_rounds": 1,
                    "trajectory_summary": "profile_load_started -> profile_load_failed -> session_invalid -> navigate_login",
                    "useful_followup_focus": "log",
                    "useful_followup_terms": ["session invalid", "load profile failed", "401", "SessionManager"],
                    "misleading_followup_terms": ["route blank", "layout issue"],
                    "inspection_targets": ["pages/Profile.ets", "SessionManager", "load profile failed"],
                    "final_verification_path": "Confirm session invalid and failed profile load in the dominant runtime slice, then inspect the auth/session handling path.",
                    "verification_method": "Confirm the dominant runtime slice against auth/session code-log anchors and reproduce the login-to-profile path.",
                    "reuse_feedback": "helped",
                    "source_cases": ["runtime_log:profile_blank_auth", "session:session_002", "episode:profile-auth-incident-2"],
                    "lesson": "For personal-center no-data incidents, auth/session logs are often stronger than route hypotheses.",
                    "future_rule": "When profile pages have no data after login, prioritize auth/session log anchors before route inspection.",
                    "evidence": "candidate_chain: profile_load_started -> profile_load_failed -> session_invalid; top_slice: 11:02:14 -> 11:02:18",
                    "repair_action": "Inspect the dominant runtime slice first, then confirm auth/session handling in source files.",
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            action = next(action for action in actions if action["action"] == "review_log_design_gap")
            self.assertEqual(action["type"], "log_design")
            self.assertEqual(action["goal_area"], "auth_session_profile_blank")
            self.assertIn("decision_checkpoint", action["suggested_log_kinds"])
            self.assertIn("request_correlation", action["suggested_log_kinds"])
            self.assertIn("session invalid", " ".join(action["high_value_log_anchor_targets"]))
            self.assertTrue(action["log_design_feedback"])
