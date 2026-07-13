# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart08Tests(AgentMemoryTestBase):
    def test_vault_export_writes_skill_pattern_candidates_dashboard(self) -> None:
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

            self.run_memory(project, "vault-export")

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Skill Pattern Candidates.md"
            index = self.project_memory_dir(project) / "vault" / "index.md"
            self.assertTrue(dashboard.exists())
            content = dashboard.read_text(encoding="utf-8")
            self.assertIn("Reviewed draft or candidate-package artifacts are preserved by the runtime", content)
            self.assertIn("arkts-route-blank-screen-diagnosis", content)
            self.assertIn("Promotion stage: `candidate_package`", content)
            self.assertIn("Draft status: `not_written`", content)
            self.assertIn("Package status: `written`", content)
            self.assertIn("Package review status: `approved`", content)
            self.assertIn("Package reviewer: `Bob`", content)
            self.assertIn("Promotion checklist status: `written`", content)
            self.assertIn("Promotion checklist path: `skills/_candidates/arkts-route-blank-screen-diagnosis/PROMOTION.md`", content)
            self.assertIn("Promotion readiness: `review_candidate`", content)
            self.assertIn("Quality score: `", content)
            self.assertIn("Anchor health: `", content)
            self.assertIn("Review guidance:", content)
            self.assertIn("Review the candidate package metadata", content)
            self.assertIn("docs/skill-candidates/arkts-route-blank-screen-diagnosis.md", content)
            self.assertIn("router.pushUrl", content)
            self.assertIn("supporting reflections", content.lower())
            self.assertIn("[[Governance/Skill Pattern Candidates]]", index.read_text(encoding="utf-8"))

    def test_vault_export_writes_incident_strategy_candidates_dashboard(self) -> None:
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

            self.run_memory(project, "vault-export")

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Incident Strategy Candidates.md"
            index = self.project_memory_dir(project) / "vault" / "index.md"
            self.assertTrue(dashboard.exists())
            content = dashboard.read_text(encoding="utf-8")
            self.assertIn("log-auth-session-profile-blank-diagnosis", content)
            self.assertIn("Common log events", content)
            self.assertIn("load profile failed", content)
            self.assertIn("session invalid", content)
            self.assertIn("maintain-incident-strategy-draft", content)
            self.assertIn("[[Governance/Incident Strategy Candidates]]", index.read_text(encoding="utf-8"))

    def test_vault_export_writes_learned_scopes_and_refresh_drift_dashboards(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text("@Component\nstruct A { build() {} }\n", encoding="utf-8")
            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            (pages / "A.ets").write_text("@Component\nstruct A { build() { console.error('updated'); } }\n", encoding="utf-8")
            self.run_memory(project, "maintain-refresh-scope", "--json")
            self.run_memory(project, "vault-export")

            vault_dir = self.project_memory_dir(project) / "vault"
            scopes = (vault_dir / "Governance" / "Learned Scopes.md").read_text(encoding="utf-8")
            drift = (vault_dir / "Governance" / "Refresh Drift.md").read_text(encoding="utf-8")
            index = (vault_dir / "index.md").read_text(encoding="utf-8")
            self.assertIn("Scope #1 (path)", scopes)
            self.assertIn("Health: `drift`", scopes)
            self.assertIn("Changed files: 1", drift)
            self.assertIn("[[Governance/Learned Scopes]]", index)
            self.assertIn("[[Governance/Refresh Drift]]", index)

    def test_vault_export_truncates_large_record_sets_for_scale(self) -> None:
        from tools.agent_memory_runtime.storage import connect, ensure_initialized, now_iso, resolve_project

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            runtime_project = resolve_project(str(project), str(self.memory_home(project)))
            ensure_initialized(runtime_project)
            with connect(runtime_project) as conn:
                for index in range(520):
                    ts = now_iso()
                    conn.execute(
                        """
                        INSERT INTO episodes(
                          project_id, task, summary, outcome, files_touched, commands_run,
                          importance, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            runtime_project.project_id,
                            f"episode {index}",
                            f"summary {index}",
                            None,
                            None,
                            None,
                            0.5,
                            ts,
                        ),
                    )
                for index in range(1050):
                    ts = now_iso()
                    conn.execute(
                        """
                        INSERT INTO semantic_facts(
                          project_id, fact, source, confidence, category, scope, evidence,
                          created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            runtime_project.project_id,
                            f"fact {index}",
                            "test",
                            0.8,
                            None,
                            None,
                            None,
                            ts,
                            ts,
                        ),
                    )
                conn.commit()

            self.run_memory(project, "vault-export")

            vault_dir = self.project_memory_dir(project) / "vault"
            episodes_dir = vault_dir / "Episodes"
            facts_page = (vault_dir / "Semantic Facts" / "project-facts.md").read_text(encoding="utf-8")

            self.assertEqual(500, len(list(episodes_dir.glob("*.md"))))
            self.assertIn("Truncated vault export: showing 1000 of 1050 records", facts_page)

    def test_context_records_query_miss_when_all_result_sets_are_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(project, "context", "--query", "no-such-memory-token", "--json")

            misses = self.miss_list(project)
            self.assertEqual(len(misses), 1)
            self.assertEqual(misses[0]["query"], "no-such-memory-token")
            self.assertEqual(misses[0]["source"], "context")
            self.assertEqual(misses[0]["status"], "open")
            self.assertEqual(json.loads(misses[0]["result_counts"])["semantic_facts"], 0)

    def test_repeated_query_miss_updates_existing_open_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(project, "context", "--query", "No Such Memory Token", "--json")
            self.run_memory(project, "context", "--query", "  no   such memory token  ", "--json")

            misses = self.miss_list(project)
            self.assertEqual(len(misses), 1)
            self.assertEqual(misses[0]["query"], "No Such Memory Token")
            self.assertEqual(misses[0]["normalized_query"], "no such memory token")
            self.assertEqual(misses[0]["miss_count"], 2)
            self.assertIsNotNone(misses[0]["last_seen_at"])

    def test_context_does_not_record_query_miss_when_memory_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "SQLite remains the source of truth.",
                "--source",
                "test",
            )

            self.run_memory(project, "context", "--query", "SQLite", "--json")

            self.assertEqual(self.miss_list(project), [])

    def test_wiki_search_records_query_miss_when_no_wiki_match_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(project, "wiki-search", "--query", "missing-wiki-token", "--json")

            misses = self.miss_list(project)
            self.assertEqual(len(misses), 1)
            self.assertEqual(misses[0]["source"], "wiki-search")

    def test_miss_status_updates_query_miss_review_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "context", "--query", "unanswered-question", "--json")

            self.run_memory(
                project,
                "miss-status",
                "--id",
                "1",
                "--status",
                "resolved",
                "--resolution",
                "added semantic fact",
            )

            miss = self.miss_list(project)[0]
            self.assertEqual(miss["status"], "resolved")
            self.assertEqual(miss["resolution"], "added semantic fact")
            self.assertIsNotNone(miss["reviewed_at"])

    def test_maintain_plan_includes_open_query_miss_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "symbols": [{"symbol": "profileCache", "symbol_type": "field"}],
                        "logs": [{"message_template": "load profile start", "level": "info"}],
                    }
                ]
            }
            self.run_memory(project, "learn-business", "--payload", json.dumps(payload, ensure_ascii=False), "--json")
            self.run_memory(project, "context", "--query", "unanswered-question", "--json")

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            action = next(action for action in actions if action["action"] == "review_query_miss" and action["id"] == 1)
            self.assertEqual(action["miss_count"], 1)
            self.assertEqual(
                action["suggested_fixes"],
                ["learn_missing_scope", "add_business_terms", "rewrite_reflection", "ignore_noise"],
            )
            self.assertIn("unanswered", action["suggested_query_terms"])
            self.assertIn("pages/profiledetail.ets", action["suggested_query_terms"])
            self.assertIn("profilecache", action["suggested_query_terms"])
            self.assertEqual(
                action["query_command_template"],
                "python tools/agent_memory.py search --project . --query '<query>' --json",
            )
            self.assertEqual(
                action["query_workflow_steps"],
                [
                    "Start from suggested_query_terms and keep the original user problem wording.",
                    "Prefer exact route, resource, log, file, and symbol anchors before generic keywords.",
                    "Run query or search again with the strongest 2-6 followup terms.",
                    "If retrieval is still weak, enrich the listed code records with learn-business before querying again.",
                ],
            )
            self.assertIn("pages/ProfileDetail.ets", action["semantic_gap_targets"]["files_missing_business_terms"])
            self.assertIn(
                "pages/ProfileDetail.ets::profileCache",
                action["semantic_gap_targets"]["symbols_missing_business_terms"],
            )
            self.assertIn(
                "pages/ProfileDetail.ets::load profile start",
                action["semantic_gap_targets"]["logs_missing_business_summary"],
            )
