# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart05Tests(AgentMemoryTestBase):
    def test_reflect_review_surfaces_runtime_feedback_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "task": "Diagnose profile blank with runtime evidence",
                "lesson": "Auth/session runtime signals should outrank broad page hypotheses.",
                "summary": "Runtime diagnosis for profile blank.",
                "future_rule": "Check runtime auth/session signals before escalating to route investigation.",
                "experience_type": "correction_experience",
                "task_type": "diagnosis",
                "problem": "个人资料页空白，怀疑登录态异常",
                "scope": "pages/Profile.ets",
                "evidence": "candidate_chain: profile_load_failed -> session_invalid",
                "trigger_condition": "Profile page is blank after login.",
                "verification_method": "Confirm the dominant runtime slice against the code-log anchors.",
                "reuse_feedback": "partial",
                "useful_followup_focus": "log",
                "useful_followup_terms": ["load profile failed", "session invalid", "401"],
                "misleading_followup_terms": ["route blank", "layout issue"],
                "inspection_targets": ["pages/Profile.ets", "ProfileService.loadProfile"],
                "final_verification_path": "06-03 10:21:13.200 -> 06-03 10:21:13.300",
                "what_failed": [
                    "Earlier diagnosis leaned toward a route/navigation cause.",
                    "The route hypothesis did not fit the dominant runtime evidence.",
                ],
                "repair_action": "Inspect the dominant runtime slice first, then confirm the auth/session code path.",
                "source_cases": ["runtime_log:profile blank", "session:session_001"],
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(project, "reflect-review", "--json")
            data = json.loads(result.stdout)

            self.assertEqual(len(data["reflections"]), 1)
            item = data["reflections"][0]
            self.assertIn("runtime_feedback_summary", item)
            self.assertIn("load profile failed", " ".join(item["runtime_feedback_summary"]["effective_signals"]).lower())
            self.assertIn("route", " ".join(item["runtime_feedback_summary"]["misleading_signals"]).lower())
            self.assertIn("06-03 10:21:13.200", " ".join(item["runtime_feedback_summary"]["verification_checkpoints"]))

    def test_maintain_plan_includes_learn_and_governance_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Profile.ets").write_text(
                "import hilog from '@ohos.hilog';\n"
                "@Entry\n"
                "@Component\n"
                "struct ProfilePage {\n"
                "  aboutToAppear() {\n"
                "    hilog.error(0x0000, 'ProfilePage', 'load profile failed');\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            self.run_memory(
                project,
                "reflect",
                "--payload",
                json.dumps(
                    {
                        "task": "Correct profile diagnosis after runtime evidence",
                        "lesson": "Session invalid should redirect diagnosis toward auth handling.",
                        "future_rule": "Prefer auth/session repair before route fixes when runtime evidence shows session invalid.",
                        "experience_type": "correction_experience",
                        "task_type": "diagnosis",
                        "problem": "个人资料页空白，怀疑登录态异常",
                        "scope": "pages/Profile.ets",
                        "evidence": "candidate_chain: profile_load_failed -> session_invalid",
                        "trigger_condition": "Profile page is blank after login.",
                        "verification_method": "Confirm runtime failure slice against code-log anchors.",
                        "reuse_feedback": "partial",
                        "useful_followup_focus": "log",
                        "useful_followup_terms": ["load profile failed", "session invalid", "401"],
                        "misleading_followup_terms": ["route blank"],
                        "inspection_targets": ["pages/Profile.ets"],
                        "final_verification_path": "pages/Profile.ets",
                        "what_failed": ["Earlier diagnosis leaned toward a route/navigation cause."],
                        "repair_action": "Inspect the auth/session code path first.",
                        "source_cases": ["runtime_log:profile blank"],
                        "hidden_assumptions": ["The page blank state was caused by routing."],
                        "negative_preconditions": ["Do not apply when runtime logs show route target missing."],
                    },
                    ensure_ascii=False,
                ),
            )
            (project / "pages" / "Profile.ets").unlink()
            self.run_memory(project, "maintain-refresh-scope", "--json")

            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

            self.assertIn("governance_summary", data)
            self.assertIn("learn_governance_summary", data)
            self.assertGreaterEqual(data["learn_governance_summary"]["correction_repairs"], 1)
            self.assertGreaterEqual(data["learn_governance_summary"]["semantic_drift_reviews"], 1)
            self.assertIn("pages/Profile.ets", data["learn_governance_summary"]["top_affected_paths"])
            self.assertGreaterEqual(data["governance_summary"]["counts_by_lane"]["learn_semantic_repair"], 1)
            self.assertTrue(any(action["action"] == "review_semantic_drift" for action in data["actions"]))
            self.assertTrue(any(action["action"] == "review_correction_experience" for action in data["actions"]))

    def test_maintain_plan_surfaces_recurring_incident_fingerprint_and_can_write_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "task": "Diagnose profile blank after login",
                    "lesson": "Repeated auth/session runtime signals indicate the same incident family.",
                    "future_rule": "Check auth/session signals before route fixes.",
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "problem": "个人资料页空白，怀疑登录态异常",
                    "scope": "pages/Profile.ets",
                    "evidence": "candidate_chain: profile_load_failed -> session_invalid",
                    "trigger_condition": "Profile page is blank after login.",
                    "verification_method": "Confirm runtime slice against code-log anchors.",
                    "reuse_feedback": "helped",
                    "useful_followup_focus": "log",
                    "useful_followup_terms": ["load profile failed", "session invalid", "401"],
                    "misleading_followup_terms": ["route blank"],
                    "inspection_targets": ["pages/Profile.ets", "ProfileService.loadProfile"],
                    "final_verification_path": "pages/Profile.ets",
                    "repair_action": "Inspect auth/session logs before route debugging.",
                    "what_worked": ["Check session invalid after profile load failed."],
                    "source_cases": ["runtime_log:profile blank", "session:session_001"],
                    "hidden_assumptions": ["The page blank state is not always a route issue."],
                    "negative_preconditions": ["Do not apply when route target missing is explicit."],
                },
                {
                    "task": "Diagnose profile blank after token expiry",
                    "lesson": "The same auth/session incident fingerprint recurs after token expiry.",
                    "future_rule": "Check auth/session signals before route fixes.",
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "problem": "个人资料页空白，登录后没有数据",
                    "scope": "pages/Profile.ets",
                    "evidence": "candidate_chain: profile_load_failed -> session_invalid -> 401",
                    "trigger_condition": "Profile page is blank after token expiry.",
                    "verification_method": "Confirm runtime slice against code-log anchors.",
                    "reuse_feedback": "helped",
                    "useful_followup_focus": "log",
                    "useful_followup_terms": ["load profile failed", "session invalid", "401"],
                    "misleading_followup_terms": ["layout issue"],
                    "inspection_targets": ["pages/Profile.ets", "SessionManager.validate"],
                    "final_verification_path": "pages/Profile.ets",
                    "repair_action": "Inspect auth/session logs before UI rendering hypotheses.",
                    "what_worked": ["Check session invalid after profile load failed."],
                    "source_cases": ["runtime_log:profile blank", "session:session_002"],
                    "hidden_assumptions": ["The page blank state is not always a route issue."],
                    "negative_preconditions": ["Do not apply when API returns valid profile data."],
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)
            action = next(item for item in data["actions"] if item["action"] == "review_recurring_incident_fingerprint")

            self.assertEqual(action["type"], "incident_fingerprint")
            self.assertEqual(action["governance_lane"], "incident_recurrence")
            self.assertIn("session invalid", " ".join(action["common_log_events"]).lower())
            self.assertEqual(action["supporting_count"], 2)
            self.assertIn("maintain-incident-fingerprint-draft", action["write_command_template"])

            write_result = self.run_memory(
                project,
                "maintain-incident-fingerprint-draft",
                "--fingerprint-name",
                action["fingerprint_name"],
                "--json",
            )
            written = json.loads(write_result.stdout)
            self.assertEqual(written["fingerprint_name"], action["fingerprint_name"])
            self.assertTrue(Path(written["path"]).exists())
            self.assertEqual(written["supporting_count"], 2)

    def test_maintain_incident_strategy_draft_writes_markdown_file(self) -> None:
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

            result = self.run_memory(
                project,
                "maintain-incident-strategy-draft",
                "--strategy-name",
                "log-auth-session-profile-blank-diagnosis",
                "--json",
            )
            payload = json.loads(result.stdout)
            draft_path = project / "docs" / "incident-strategies" / "log-auth-session-profile-blank-diagnosis.md"
            self.assertTrue(draft_path.exists())
            content = draft_path.read_text(encoding="utf-8")
            self.assertEqual(Path(payload["path"]).resolve(), draft_path.resolve())
            self.assertEqual(payload["strategy_name"], "log-auth-session-profile-blank-diagnosis")
            self.assertEqual(payload["draft_status"], "written")
            self.assertIn("artifact_type: \"incident_strategy_draft\"", content)
            self.assertIn("promotion_status: \"draft\"", content)
            self.assertIn("## Goal Symptoms", content)
            self.assertIn("## Common Log Events", content)
            self.assertIn("load profile failed", content)
            self.assertIn("session invalid", content)


    def test_maintain_skill_draft_writes_markdown_file(self) -> None:
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

            result = self.run_memory(
                project,
                "maintain-skill-draft",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            payload = json.loads(result.stdout)
            draft_path = project / "docs" / "skill-candidates" / "arkts-route-blank-screen-diagnosis.md"
            self.assertTrue(draft_path.exists())
            content = draft_path.read_text(encoding="utf-8")
            self.assertEqual(Path(payload["path"]).resolve(), draft_path.resolve())
            self.assertEqual(payload["pattern_name"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(payload["draft_status"], "written")
            self.assertEqual(payload["draft_review_status"], "pending_review")
            self.assertEqual(payload["package_status"], "not_written")
            self.assertEqual(payload["package_review_status"], "")
            self.assertEqual(payload["promotion_stage"], "draft")
            self.assertEqual(payload["write_action"], "wrote_artifact")
            self.assertEqual(payload["warning"], "")
            self.assertIn("Review the draft and record reviewer metadata", payload["review_guidance"][0])
            self.assertIn("artifact_type: \"skill_candidate_draft\"", content)
            self.assertIn("promotion_status: \"draft\"", content)
            self.assertIn("review_status: \"pending_review\"", content)
            self.assertIn("reviewer: \"\"", content)
            self.assertIn("review_notes: []", content)
            self.assertIn("supporting_reflection_ids: [1, 2]", content)
            self.assertIn("common_followup_focus: [\"route\"]", content)
            self.assertIn("- Review status: pending_review", content)
            self.assertIn("## Common Steps", content)
            self.assertIn("query route anchors", content)
            self.assertIn("## Failure Modes", content)
