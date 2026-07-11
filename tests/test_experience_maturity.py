# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"


class ExperienceMaturityTests(unittest.TestCase):
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

    def test_raw_reflection_is_raw_observation(self) -> None:
        from tools.agent_memory_runtime.experience_maturity import score_experience_maturity

        result = score_experience_maturity({"task": "try route fix", "lesson": "check route"})

        self.assertEqual("raw_observation", result["experience_maturity"])
        self.assertLess(result["experience_maturity_score"], 0.45)
        self.assertEqual("add_structure", result["recommended_maturity_action"])

    def test_trigger_and_repair_without_verification_is_structured_candidate(self) -> None:
        from tools.agent_memory_runtime.experience_maturity import score_experience_maturity

        result = score_experience_maturity(
            {
                "experience_type": "procedure_experience",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "scope": "ArkTS route diagnosis",
            }
        )

        self.assertEqual("structured_candidate", result["experience_maturity"])
        self.assertIn("has trigger_condition", result["maturity_reasons"])
        self.assertIn("has repair_action", result["maturity_reasons"])

    def test_verified_source_case_is_verified_case(self) -> None:
        from tools.agent_memory_runtime.experience_maturity import score_experience_maturity

        result = score_experience_maturity(
            {
                "verification_method": "ran route navigation test",
                "source_cases": json.dumps(["incident_trace:1"]),
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
            }
        )

        self.assertEqual("verified_case", result["experience_maturity"])
        self.assertGreaterEqual(result["experience_maturity_score"], 0.65)
        self.assertIn("has verification_method", result["maturity_reasons"])
        self.assertIn("has source_cases", result["maturity_reasons"])

    def test_successful_reuse_is_reused_pattern(self) -> None:
        from tools.agent_memory_runtime.experience_maturity import score_experience_maturity

        result = score_experience_maturity(
            {
                "verification_method": "ran route navigation test",
                "source_cases": json.dumps(["incident_trace:1"]),
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "applied_count": 2,
                "last_outcome": "helped",
            }
        )

        self.assertEqual("reused_pattern", result["experience_maturity"])
        self.assertIn("positive reuse", " ".join(result["maturity_reasons"]))

    def test_skill_candidate_requires_mature_support(self) -> None:
        from tools.agent_memory_runtime.experience_maturity import score_experience_maturity

        result = score_experience_maturity(
            {
                "experience_type": "procedure_experience",
                "skill_candidate": "arkts-route-blank-screen-diagnosis",
                "verification_method": "ran route navigation test",
                "source_cases": json.dumps(["incident_trace:1"]),
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "applied_count": 2,
                "last_outcome": "helped",
            }
        )

        self.assertEqual("skill_candidate", result["experience_maturity"])
        self.assertGreaterEqual(result["experience_maturity_score"], 0.8)

    def test_stale_or_misleading_reflection_is_deprecated(self) -> None:
        from tools.agent_memory_runtime.experience_maturity import score_experience_maturity

        stale = score_experience_maturity({"status": "stale", "verification_method": "old test"})
        misleading = score_experience_maturity({"last_outcome": "misleading", "misleading_score": 0.8})

        self.assertEqual("deprecated_pattern", stale["experience_maturity"])
        self.assertEqual("deprecated_pattern", misleading["experience_maturity"])
        self.assertEqual("deprecate_or_rewrite", misleading["recommended_maturity_action"])

    def test_counter_evidence_summary_reports_missing_fields(self) -> None:
        from tools.agent_memory_runtime.experience_maturity import build_counter_evidence_summary

        result = build_counter_evidence_summary(
            {
                "negative_preconditions": json.dumps(["does not apply when route target is correct"]),
                "does_not_apply_to": "resource missing failures",
            }
        )

        self.assertTrue(result["has_counter_evidence"])
        self.assertIn("negative_preconditions", result["fields"])
        self.assertIn("does_not_apply_to", result["fields"])
        self.assertNotIn("negative_preconditions", result["missing_fields"])

    def test_context_reflections_include_maturity_and_influence_trust(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            mature_payload = {
                "experience_type": "procedure_experience",
                "task": "ArkTS route blank screen diagnosis",
                "summary": "Verified route target mismatch diagnosis.",
                "lesson": "For ArkTS route blank screen, inspect router.pushUrl target and page registration first.",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "verification_method": "ran route navigation test",
                "source_cases": ["incident_trace:7"],
                "negative_preconditions": ["does not apply when route target and page registration are already verified"],
                "does_not_apply_to": "resource missing failures",
                "confidence": 0.9,
            }
            raw_payload = {
                "task": "ArkTS route blank screen broad note",
                "summary": "Broad route note.",
                "lesson": "Check route maybe.",
                "confidence": 0.6,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(mature_payload))
            self.run_memory(project, "reflect", "--payload", json.dumps(raw_payload))
            result = self.run_memory(project, "context", "--query", "ArkTS route blank screen", "--json")
            data = json.loads(result.stdout)

        by_id = {item["id"]: item for item in data["reflections"]}
        self.assertEqual("verified_case", by_id[1]["experience_maturity"])
        self.assertEqual("raw_observation", by_id[2]["experience_maturity"])
        self.assertIn("counter_evidence", by_id[1])
        self.assertGreater(by_id[1]["trust_score"], by_id[2]["trust_score"])

    def test_maintain_plan_reviews_missing_counter_evidence_for_verified_experience(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            payload = {
                "experience_type": "procedure_experience",
                "task": "ArkTS route blank screen diagnosis",
                "summary": "Verified route target mismatch diagnosis.",
                "lesson": "For ArkTS route blank screen, inspect router.pushUrl target and page registration first.",
                "scope": "ArkTS route diagnosis",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "inspect router.pushUrl target",
                "verification_method": "ran route navigation test",
                "source_cases": ["incident_trace:7"],
                "confidence": 0.95,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(payload))
            result = self.run_memory(project, "maintain-plan", "--json")
            data = json.loads(result.stdout)

        actions = [action for action in data["actions"] if action["action"] == "review_missing_counter_evidence"]
        self.assertEqual(1, len(actions))
        self.assertEqual("reflection", actions[0]["type"])
        self.assertEqual(1, actions[0]["id"])
        self.assertEqual("memory_quality", actions[0]["governance_lane"])
        self.assertIn("negative_preconditions", actions[0]["missing_counter_evidence_fields"])
        self.assertEqual(1, data["governance_summary"]["missing_counter_evidence_reviews"])


if __name__ == "__main__":
    unittest.main()
