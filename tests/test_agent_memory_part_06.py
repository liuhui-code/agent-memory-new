# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart06Tests(AgentMemoryTestBase):
    def test_maintain_skill_draft_all_writes_all_candidate_files(self) -> None:
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
                    "task_type": "design",
                    "outcome": "success",
                    "problem": "Product image resource does not render.",
                    "task": "diagnose product image resource failure",
                    "summary": "The resource key was mismatched.",
                    "reasoning_summary": "Resource anchors and app.media lookups narrowed the issue.",
                    "context_used": ["query: product image resource", "file: ProductCard.ets"],
                    "what_worked": ["Search business image term with app.media anchors."],
                    "what_failed": ["Searching only card component names."],
                    "hidden_assumptions": ["The resource exists in the current module bundle."],
                    "negative_preconditions": ["Does not apply to network image loading."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the wrong resource key.",
                    "useful_followup_focus": "resource",
                    "useful_followup_terms": ["product image", "app.media", "$r"],
                    "misleading_followup_terms": ["card"],
                    "inspection_targets": ["pages/ProductCard.ets", "resources/base/media"],
                    "final_verification_path": "Inspect resource key usage and compare with declared media entries.",
                    "related_cases": ["case_product_resource_001"],
                    "verification_method": "Check resource declarations and lookup sites.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:product-resource-fix"],
                    "skill_candidate": "arkts-resource-missing-diagnosis",
                    "lesson": "Resource failures should start from business noun plus app.media anchors.",
                    "future_rule": "When a business image fails, query the resource anchors before UI component names.",
                    "scope": "HarmonyOS ArkTS resource lookup",
                    "evidence": "ProductCard.ets app.media reference",
                    "trigger_condition": "Business image or icon resource does not render",
                    "anti_pattern": "Search only component names",
                    "repair_action": "Query business resource terms and compare with resource keys",
                    "applies_to": "ArkTS resource lookup failures",
                    "does_not_apply_to": "Remote image network failures",
                    "confidence": 0.9,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "design",
                    "outcome": "success",
                    "problem": "Product icon resource does not render.",
                    "task": "diagnose product icon resource failure",
                    "summary": "The icon resource key was mismatched.",
                    "reasoning_summary": "Resource anchors and app.media lookups converged on the wrong key.",
                    "context_used": ["query: product icon resource", "file: ProductCard.ets"],
                    "what_worked": ["Search business icon term with app.media anchors."],
                    "what_failed": ["Starting from component names only."],
                    "hidden_assumptions": ["The icon resource is bundled locally."],
                    "negative_preconditions": ["Does not apply to remote CDN icon failures."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the wrong icon resource key.",
                    "useful_followup_focus": "resource",
                    "useful_followup_terms": ["product icon", "app.media", "$r"],
                    "misleading_followup_terms": ["card"],
                    "inspection_targets": ["pages/ProductCard.ets", "resources/base/media"],
                    "final_verification_path": "Inspect icon resource key usage and compare with declared media entries.",
                    "related_cases": ["case_product_resource_002"],
                    "verification_method": "Check resource declarations and icon lookup sites.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:product-icon-resource-fix"],
                    "skill_candidate": "arkts-resource-missing-diagnosis",
                    "lesson": "Resource failures should start from business noun plus app.media anchors.",
                    "future_rule": "When a business icon fails, query the resource anchors before UI component names.",
                    "scope": "HarmonyOS ArkTS resource lookup",
                    "evidence": "ProductCard.ets app.media reference",
                    "trigger_condition": "Business icon resource does not render",
                    "anti_pattern": "Search only component names",
                    "repair_action": "Query business resource terms and compare with resource keys",
                    "applies_to": "ArkTS resource lookup failures",
                    "does_not_apply_to": "Remote image network failures",
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
                "all",
                "--json",
            )

            payload = json.loads(result.stdout)
            route_draft = project / "docs" / "skill-candidates" / "arkts-route-blank-screen-diagnosis.md"
            resource_draft = project / "docs" / "skill-candidates" / "arkts-resource-missing-diagnosis.md"
            self.assertTrue(route_draft.exists())
            self.assertTrue(resource_draft.exists())
            self.assertEqual(payload["written_count"], 2)
            self.assertEqual(payload["pattern_names"], [
                "arkts-resource-missing-diagnosis",
                "arkts-route-blank-screen-diagnosis",
            ])
            self.assertEqual(payload["written"][0]["draft_status"], "written")
            self.assertEqual(payload["written"][0]["draft_review_status"], "pending_review")
            self.assertEqual(payload["written"][0]["promotion_stage"], "draft")
            self.assertEqual(payload["written"][0]["write_action"], "wrote_artifact")

    def test_maintain_skill_package_writes_candidate_skill_file(self) -> None:
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
                "maintain-skill-package",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            payload = json.loads(result.stdout)
            package_path = project / "skills" / "_candidates" / "arkts-route-blank-screen-diagnosis" / "SKILL.md"
            checklist_path = project / "skills" / "_candidates" / "arkts-route-blank-screen-diagnosis" / "PROMOTION.md"
            self.assertTrue(package_path.exists())
            self.assertTrue(checklist_path.exists())
            content = package_path.read_text(encoding="utf-8")
            checklist = checklist_path.read_text(encoding="utf-8")
            self.assertEqual(Path(payload["path"]).resolve(), package_path.resolve())
            self.assertEqual(payload["pattern_name"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(payload["draft_status"], "not_written")
            self.assertEqual(payload["draft_review_status"], "")
            self.assertEqual(payload["package_status"], "written")
            self.assertEqual(payload["package_review_status"], "pending_review")
            self.assertEqual(payload["promotion_checklist_status"], "written")
            self.assertEqual(payload["promotion_stage"], "candidate_package")
            self.assertEqual(payload["promotion_readiness"], "review_candidate")
            self.assertEqual(payload["write_action"], "wrote_artifact")
            self.assertEqual(payload["warning"], "")
            self.assertIn("Review the candidate package metadata", payload["review_guidance"][0])
            self.assertIn("artifact_type: \"skill_candidate_package\"", content)
            self.assertIn("promotion_status: \"candidate\"", content)
            self.assertIn("review_status: \"pending_review\"", content)
            self.assertIn("review_notes: []", content)
            self.assertIn("source_draft: \"docs/skill-candidates/arkts-route-blank-screen-diagnosis.md\"", content)
            self.assertIn("Candidate package generated from repeated procedure_experience reflections.", content)
            self.assertIn("## Common Steps", content)
            self.assertIn("## Quality Signals", content)
            self.assertIn("Readiness: `review_candidate`", content)
            self.assertIn("Anchor health:", content)
            self.assertIn("# Promotion Checklist: arkts-route-blank-screen-diagnosis", checklist)
            self.assertIn("Formal target: `skills/arkts-route-blank-screen-diagnosis/SKILL.md`", checklist)
            self.assertIn("Promotion readiness is acceptable (`review_candidate`)", checklist)

    def test_maintain_skill_draft_preserves_existing_reviewed_draft(self) -> None:
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
                "maintain-skill-draft",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            draft_path = project / "docs" / "skill-candidates" / "arkts-route-blank-screen-diagnosis.md"
            draft_path.write_text(
                draft_path.read_text(encoding="utf-8")
                .replace('review_status: "pending_review"', 'review_status: "approved"')
                .replace('reviewer: ""', 'reviewer: "Alice"'),
                encoding="utf-8",
            )
            preserved_content = draft_path.read_text(encoding="utf-8")

            result = self.run_memory(
                project,
                "maintain-skill-draft",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["write_action"], "preserved_existing_reviewed_artifact")
            self.assertIn("did not overwrite", payload["warning"])
            self.assertEqual(payload["existing_review_status"], "approved")
            self.assertEqual(payload["existing_reviewer"], "Alice")
            self.assertEqual(payload["draft_review_status"], "approved")
            self.assertEqual(payload["draft_reviewer"], "Alice")
            self.assertEqual(draft_path.read_text(encoding="utf-8"), preserved_content)
