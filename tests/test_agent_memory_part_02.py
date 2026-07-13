# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart02Tests(AgentMemoryTestBase):
    def test_maintain_health_reports_scope_health_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text("@Component\nstruct A { build() {} }\n", encoding="utf-8")
            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            (pages / "A.ets").write_text("@Component\nstruct A { build() { console.error('updated'); } }\n", encoding="utf-8")
            self.run_memory(project, "maintain-refresh-scope", "--json")

            result = self.run_memory(project, "maintain-health", "--json")
            payload = json.loads(result.stdout)
            self.assertEqual(payload["counts"]["learn_scopes"], 1)
            self.assertEqual(payload["counts"]["scope_with_drift"], 1)
            self.assertEqual(payload["scope_health"][0]["health_status"], "drift")

    def test_maintain_plan_flags_reflections_when_removed_file_anchor_disappears(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text("@Component\nstruct A { build() {} }\n", encoding="utf-8")
            (pages / "B.ets").write_text("@Component\nstruct B { build() {} }\n", encoding="utf-8")
            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            payload = {
                "experience_type": "procedure_experience",
                "task_type": "diagnosis",
                "outcome": "success",
                "task": "diagnose removed page issue",
                "lesson": "Removed page anchors should be reviewed.",
                "future_rule": "If a referenced page disappears, review old experience before reuse.",
                "scope": "ArkTS page diagnosis",
                "evidence": "pages/B.ets",
                "trigger_condition": "Linked page file is removed",
                "repair_action": "Review or stale related experience",
                "hidden_assumptions": ["pages/B.ets still exists"],
                "negative_preconditions": ["Do not apply when the file still exists"],
                "verification_method": "Check the current code tree for the referenced file",
                "reuse_feedback": "candidate",
                "source_cases": ["file: pages/B.ets"],
                "inspection_targets": ["pages/B.ets"],
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))
            (pages / "B.ets").unlink()
            self.run_memory(project, "maintain-refresh-scope", "--json")

            result = self.run_memory(project, "maintain-plan", "--json")

            payload = json.loads(result.stdout)
            stale_actions = [
                action
                for action in payload["actions"]
                if action["action"] == "mark_experience_stale_if_anchor_removed"
            ]
            self.assertEqual(len(stale_actions), 1)
            self.assertIn("pages/B.ets", stale_actions[0]["removed_files"])
            self.assertEqual(stale_actions[0]["linked_reflection_ids"], [1])

    def test_maintain_plan_flags_skill_pattern_staleness_when_removed_anchor_hits_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text("@Component\nstruct A { build() {} }\n", encoding="utf-8")
            (pages / "B.ets").write_text("@Component\nstruct B { build() {} }\n", encoding="utf-8")
            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            for task in ("first route issue", "second route issue"):
                payload = {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "task": task,
                    "lesson": "Removed page anchors should be reviewed.",
                    "future_rule": "If a referenced page disappears, review old experience before reuse.",
                    "scope": "ArkTS page diagnosis",
                    "evidence": "pages/B.ets",
                    "trigger_condition": "Linked page file is removed",
                    "repair_action": "Review or stale related experience",
                    "hidden_assumptions": ["pages/B.ets still exists"],
                    "negative_preconditions": ["Do not apply when the file still exists"],
                    "verification_method": "Check the current code tree for the referenced file",
                    "reuse_feedback": "candidate",
                    "source_cases": ["file: pages/B.ets"],
                    "inspection_targets": ["pages/B.ets"],
                    "skill_candidate": "removed-anchor-review",
                }
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))
            (pages / "B.ets").unlink()
            self.run_memory(project, "maintain-refresh-scope", "--json")

            result = self.run_memory(project, "maintain-plan", "--json")
            payload = json.loads(result.stdout)
            actions = [action for action in payload["actions"] if action["action"] == "review_skill_pattern_staleness"]
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0]["pattern_name"], "removed-anchor-review")

    def test_maintain_status_marks_semantic_stale_and_context_excludes_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "SQLite source of truth",
                "--source",
                "test",
                "--confidence",
                "1.0",
            )

            self.run_memory(
                project,
                "maintain-status",
                "--type",
                "semantic",
                "--id",
                "1",
                "--status",
                "stale",
                "--reason",
                "test stale",
            )
            context = self.run_memory(project, "context", "--query", "SQLite", "--json")

            facts = self.list_records(project, "semantic")
            self.assertEqual(facts[0]["status"], "stale")
            self.assertEqual(json.loads(context.stdout)["semantic_facts"], [])

    def test_maintain_promote_episode_to_semantic_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "update",
                "--type",
                "episode",
                "--task",
                "review task",
                "--summary",
                "learned durable fact",
            )

            result = self.run_memory(
                project,
                "maintain-promote",
                "--episode-id",
                "1",
                "--fact",
                "Durable promoted fact",
                "--json",
            )

            payload = json.loads(result.stdout)
            facts = self.list_records(project, "semantic")
            episodes = self.list_records(project, "episode")
            self.assertEqual(payload["semantic_fact_id"], 1)
            self.assertEqual(facts[0]["fact"], "Durable promoted fact")
            self.assertEqual(episodes[0]["derived_facts"], "[1]")

    def test_maintain_merge_marks_old_semantic_records_merged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            for fact in ("Skill calls runtime script", "Skills call runtime script"):
                self.run_memory(
                    project,
                    "update",
                    "--type",
                    "semantic",
                    "--fact",
                    fact,
                    "--source",
                    "test",
                )

            result = self.run_memory(
                project,
                "maintain-merge",
                "--type",
                "semantic",
                "--ids",
                "1,2",
                "--fact",
                "Skills call the runtime script.",
                "--json",
            )

            payload = json.loads(result.stdout)
            facts = sorted(self.list_records(project, "semantic"), key=lambda row: row["id"])
            self.assertEqual(payload["merged_into_id"], 3)
            self.assertEqual([facts[0]["status"], facts[1]["status"], facts[2]["status"]], ["merged", "merged", "active"])
            self.assertEqual([facts[0]["merged_into_id"], facts[1]["merged_into_id"]], [3, 3])

    def test_maintain_plan_outputs_confirmable_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            for fact in ("Runtime uses SQLite", "Runtime uses SQLite"):
                self.run_memory(
                    project,
                    "update",
                    "--type",
                    "semantic",
                    "--fact",
                    fact,
                    "--source",
                    "test",
                )
            self.run_memory(
                project,
                "update",
                "--type",
                "episode",
                "--task",
                "planned review",
                "--summary",
                "may contain durable knowledge",
            )
            self.run_memory(
                project,
                "maintain-status",
                "--type",
                "semantic",
                "--id",
                "2",
                "--status",
                "stale",
                "--reason",
                "test stale",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            payload = json.loads(result.stdout)
            actions = payload["actions"]

            self.assertEqual(payload["summary"]["stale"], 1)
            self.assertTrue(all(action["requires_confirmation"] for action in actions))
            self.assertIn("archive", {action["action"] for action in actions})
            self.assertIn("promote_or_archive", {action["action"] for action in actions})
            self.assertTrue(any(action["type"] == "semantic" and action["id"] == 2 for action in actions))

    def test_reflect_writes_actionable_quality_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(
                project,
                "reflect",
                "--task",
                "change runtime command",
                "--lesson",
                "Command behavior changes need tests and docs.",
                "--future-rule",
                "Update parser, tests, skill docs, usage guide, and gitlog together.",
                "--trigger-condition",
                "When changing runtime CLI behavior",
                "--anti-pattern",
                "Only update parser implementation",
                "--repair-action",
                "Update tests, docs, and skill instructions in the same change",
                "--applies-to",
                "runtime command behavior changes",
                "--does-not-apply-to",
                "docs-only edits",
            )

            reflection = self.list_records(project, "reflection")[0]
            self.assertEqual(reflection["trigger_condition"], "When changing runtime CLI behavior")
            self.assertEqual(reflection["anti_pattern"], "Only update parser implementation")
            self.assertEqual(reflection["repair_action"], "Update tests, docs, and skill instructions in the same change")
            self.assertEqual(reflection["applies_to"], "runtime command behavior changes")
            self.assertEqual(reflection["does_not_apply_to"], "docs-only edits")

    def test_reflect_payload_writes_agent_structured_task_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "experience_type": "procedure_experience",
                "task_type": "diagnosis",
                "outcome": "success",
                "problem": "Profile page shows a blank screen after navigation.",
                "task": "diagnose profile blank page",
                "summary": "Queried memory, inspected route registration, and found the profile route path mismatch.",
                "reasoning_summary": "The useful clue was the route_to edge from Home to ProfileDetail plus the router.pushUrl log.",
                "context_used": [
                    "query: profile blank page route",
                    "file: entry/src/main/ets/pages/Home.ets",
                    "log: router.pushUrl failed",
                    "reflection:#3",
                ],
                "what_worked": [
                    "Search by business term profile before scanning all pages.",
                    "Check route edges before editing UI state.",
                ],
                "what_failed": [
                    "Searching only for blank screen was too broad.",
                ],
                "hidden_assumptions": [
                    "The blank screen started after a successful route push.",
                    "The destination page was expected to exist in page registration.",
                ],
                "negative_preconditions": [
                    "Does not apply when the page never navigates.",
                ],
                "query_rounds": 3,
                "trajectory_summary": "First query was broad, second query locked onto route edges, third inspection confirmed the target page mismatch.",
                "useful_followup_focus": "route",
                "useful_followup_terms": [
                    "profile",
                    "router.pushUrl",
                    "pages/ProfileDetail",
                ],
                "misleading_followup_terms": [
                    "blank screen",
                ],
                "inspection_targets": [
                    "entry/src/main/ets/pages/Home.ets",
                    "entry/src/main/resources/base/profile_pages.json",
                ],
                "final_verification_path": "Reproduce navigation -> inspect route registration -> confirm router target mismatch.",
                "related_cases": ["case_profile_route_001"],
                "verification_method": "Confirm route registration, inspect router log, and reproduce navigation.",
                "reuse_feedback": "candidate until reused on another route issue",
                "source_cases": ["episode:profile-route-mismatch", "reflection:#3"],
                "skill_candidate": "arkts-route-blank-screen-diagnosis",
                "mistake": "The first query omitted the business page name.",
                "lesson": "ArkTS blank-screen diagnosis should combine the business page name with route terms.",
                "future_rule": "When a HarmonyOS page opens blank after navigation, query business page terms plus route/router terms first.",
                "scope": "HarmonyOS ArkTS route diagnosis",
                "evidence": "entry/src/main/ets/pages/Home.ets router.pushUrl",
                "trigger_condition": "Page opens blank after route navigation",
                "anti_pattern": "Only search generic symptom terms",
                "repair_action": "Query memory with business page name, route terms, and related log template",
                "applies_to": "ArkTS routing and page navigation failures",
                "does_not_apply_to": "Pure layout rendering bugs without navigation",
                "confidence": 0.9,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            reflection = self.list_records(project, "reflection")[0]
            self.assertEqual(reflection["task_type"], "diagnosis")
            self.assertEqual(reflection["outcome"], "success")
            self.assertEqual(reflection["problem"], "Profile page shows a blank screen after navigation.")
            self.assertIn("route_to edge", reflection["reasoning_summary"])
            self.assertEqual(json.loads(reflection["context_used"])[0], "query: profile blank page route")
            self.assertEqual(json.loads(reflection["what_worked"])[1], "Check route edges before editing UI state.")
            self.assertEqual(json.loads(reflection["what_failed"])[0], "Searching only for blank screen was too broad.")
            self.assertIn("successful route push", json.loads(reflection["hidden_assumptions"])[0])
            self.assertIn("never navigates", json.loads(reflection["negative_preconditions"])[0])
            self.assertEqual(reflection["query_rounds"], 3)
            self.assertIn("second query locked onto route edges", reflection["trajectory_summary"])
            self.assertEqual(reflection["useful_followup_focus"], "route")
            self.assertEqual(json.loads(reflection["useful_followup_terms"])[1], "router.pushUrl")
            self.assertEqual(json.loads(reflection["misleading_followup_terms"])[0], "blank screen")
            self.assertIn("profile_pages.json", json.loads(reflection["inspection_targets"])[1])
            self.assertIn("confirm router target mismatch", reflection["final_verification_path"])
            self.assertEqual(json.loads(reflection["related_cases"])[0], "case_profile_route_001")
            self.assertIn("Confirm route registration", reflection["verification_method"])
            self.assertEqual(reflection["reuse_feedback"], "candidate until reused on another route issue")
            self.assertEqual(json.loads(reflection["source_cases"])[0], "episode:profile-route-mismatch")
            self.assertEqual(reflection["skill_candidate"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(reflection["experience_type"], "procedure_experience")

    def test_reflect_payload_writes_semantic_patch_experience(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "experience_type": "semantic_patch_experience",
                "task_type": "workflow",
                "outcome": "success",
                "task": "correct profile service business meaning",
                "lesson": "Profile service semantics should be anchored to source before reuse.",
                "summary": "Corrected a learned business summary for loadProfile.",
                "anchor_type": "code_symbol",
                "anchor_key": "pages/Profile.ets::loadProfile",
                "semantic_field": "business_summary",
                "existing_value": "loads profile page UI",
                "proposed_value": "loads the user profile and validates the session before rendering",
                "patch_reason": "Caller and runtime logs show session validation happens before profile rendering.",
                "verification_method": "Inspect caller, log statement, and related session code.",
                "evidence": "pages/Profile.ets loadProfile + session invalid log",
                "trigger_condition": "Learned business meaning conflicts with current source.",
                "repair_action": "Apply the semantic patch through learn-business after source review.",
                "confidence": 0.88,
                "applies_to_current_code": True,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            reflection = self.list_records(project, "reflection")[0]
            self.assertEqual(reflection["experience_type"], "semantic_patch_experience")
            self.assertEqual(reflection["anchor_type"], "code_symbol")
            self.assertEqual(reflection["anchor_key"], "pages/Profile.ets::loadProfile")
            self.assertEqual(reflection["semantic_field"], "business_summary")
            self.assertIn("validates the session", reflection["proposed_value"])
            self.assertEqual(reflection["applies_to_current_code"], 1)

    def test_reflect_rejects_semantic_patch_without_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            command = [
                sys.executable,
                str(RUNTIME),
                "reflect",
                "--project",
                str(project),
                "--memory-home",
                str(self.memory_home(project)),
                "--payload",
                json.dumps(
                    {
                        "experience_type": "semantic_patch_experience",
                        "task": "bad patch",
                        "lesson": "Missing anchors should not alter code semantics.",
                        "semantic_field": "business_summary",
                        "proposed_value": "new meaning",
                    },
                    ensure_ascii=False,
                ),
            ]

            result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("anchor_type", result.stderr)
