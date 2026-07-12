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


class ExperienceQueryQualityTests(unittest.TestCase):
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

    def test_misleading_experience_is_capped_and_flagged(self) -> None:
        from tools.agent_memory_runtime.memory_calibration import calibrate_record

        row = {
            "id": 1,
            "experience_type": "procedure_experience",
            "experience_maturity": "deprecated_pattern",
            "confidence": 0.98,
            "quality_score": 0.91,
            "verification_method": "old manual run",
            "source_cases": ["incident_trace:2"],
            "last_outcome": "misleading",
            "misleading_score": 0.9,
            "counter_evidence": {"has_counter_evidence": True, "fields": ["does_not_apply_to"]},
        }

        calibrated = calibrate_record("reflections", row)

        self.assertLessEqual(calibrated["trust_score"], 0.25)
        self.assertEqual("conflict_warning", calibrated["trust_level"])
        self.assertIn("misleading_experience", calibrated["query_risk_flags"])
        self.assertIn("trust capped", " ".join(calibrated["trust_reasons"]))

    def test_verified_procedure_without_counter_evidence_gets_risk_flag(self) -> None:
        from tools.agent_memory_runtime.memory_calibration import calibrate_record

        row = {
            "id": 2,
            "experience_type": "procedure_experience",
            "experience_maturity": "verified_case",
            "confidence": 0.9,
            "quality_score": 0.85,
            "verification_method": "ran route navigation test",
            "source_cases": ["incident_trace:7"],
            "counter_evidence": {"has_counter_evidence": False, "fields": []},
        }

        calibrated = calibrate_record("reflections", row)

        self.assertIn("missing_counter_evidence", calibrated["query_risk_flags"])
        self.assertLessEqual(calibrated["trust_score"], 0.7)
        self.assertIn("missing counter_evidence", " ".join(calibrated["trust_reasons"]))

    def test_context_marks_recent_broad_experience_as_riskier_than_exact_correction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            correction_payload = {
                "experience_type": "correction_experience",
                "task": "ArkTS route blank screen semantic correction",
                "summary": "The pages/Profile route maps to ProfilePage, not UserPage.",
                "lesson": "For pages/Profile blank screen, treat ProfilePage registration as the source truth.",
                "trigger_condition": "ArkTS route blank screen pages/Profile",
                "repair_action": "trust the current ProfilePage route registration instead of the older UserPage assumption",
                "anti_pattern": "reusing an older UserPage route assumption without checking current route registration",
                "verification_method": "checked current route table",
                "source_cases": ["incident_trace:11"],
                "evidence": "entry/src/main/resources/base/profile/main_pages.json",
                "does_not_apply_to": "resource missing failures",
                "confidence": 0.88,
            }
            broad_payload = {
                "experience_type": "procedure_experience",
                "task": "ArkTS route blank screen broad habit",
                "summary": "Try cleaning build cache and rerun route navigation.",
                "lesson": "For ArkTS blank screen, clean cache first.",
                "trigger_condition": "ArkTS route blank screen",
                "repair_action": "clean build cache",
                "verification_method": "worked once in old project",
                "source_cases": ["incident_trace:3"],
                "confidence": 0.95,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(correction_payload))
            self.run_memory(project, "reflect", "--payload", json.dumps(broad_payload))
            result = self.run_memory(project, "context", "--query", "ArkTS pages/Profile route blank screen 报错", "--json")
            data = json.loads(result.stdout)

        correction = data["correction_guards"][0]
        broad = data["reflections"][0]
        self.assertEqual("correction_experience", correction["experience_type"])
        self.assertEqual("procedure_experience", broad["experience_type"])
        self.assertIn("semantic_correction_guidance", correction["query_risk_flags"])
        self.assertIn("missing_counter_evidence", broad["query_risk_flags"])
        self.assertGreaterEqual(correction["trust_score"], broad["trust_score"])

    def test_code_current_query_blocks_broad_procedure_interference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            pages = project / "pages"
            pages.mkdir()
            (pages / "Profile.ets").write_text(
                "export function loadProfile() {\n"
                "  console.error('load profile failed');\n"
                "}\n",
                encoding="utf-8",
            )
            broad_payload = {
                "experience_type": "procedure_experience",
                "task": "Profile blank screen broad old workflow",
                "summary": "Broad Profile issue workflow from an older project.",
                "lesson": "For Profile issues, clean cache first.",
                "trigger_condition": "Profile issue",
                "repair_action": "clean cache",
                "verification_method": "worked once in old project",
                "source_cases": ["incident_trace:old-profile"],
                "confidence": 0.95,
            }

            self.run_memory(project, "learn-path", "--path", "pages")
            self.run_memory(project, "reflect", "--payload", json.dumps(broad_payload))
            result = self.run_memory(project, "context", "--query", "当前代码 Profile loadProfile 函数", "--json")
            data = json.loads(result.stdout)

        self.assertEqual("code_current", data["memory_intent"])
        self.assertIn("wiki_matches", data["retrieval_lanes"]["intent_profile"]["preferred_lanes"])
        self.assertGreaterEqual(len(data["wiki_matches"]), 1)
        self.assertEqual([], data["reflections"])
        self.assertEqual(1, data["memory_brief"]["blocked_count"])
        self.assertIn("code_current_query_prefers_source_anchors", data["blocked_memory_notes"][0]["reason"])

    def test_reflect_records_procedure_and_correction_shapes_distinctly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            procedure_payload = {
                "experience_type": "procedure_experience",
                "task": "ArkTS route diagnosis procedure",
                "summary": "Diagnosed route mismatch through route table and router log anchors.",
                "lesson": "Use route target, page registration, and router failure logs together.",
                "trigger_condition": "page opens blank after router.pushUrl",
                "repair_action": "inspect route target and page registration",
                "verification_method": "reran navigation smoke test",
                "source_cases": ["incident_trace:21"],
                "negative_preconditions": ["does not apply to pure layout visibility bugs"],
                "confidence": 0.9,
            }
            correction_payload = {
                "experience_type": "correction_experience",
                "task": "Correct Profile route business meaning",
                "summary": "Profile route maps to ProfilePage in current source.",
                "lesson": "Do not reuse the older UserPage mapping for pages/Profile.",
                "trigger_condition": "memory says pages/Profile maps to UserPage",
                "repair_action": "treat ProfilePage registration as the current source truth",
                "anti_pattern": "applying old route mapping without checking current source",
                "verification_method": "inspected current route table",
                "source_cases": ["file: entry/src/main/resources/base/profile/main_pages.json"],
                "does_not_apply_to": "unrelated resource loading failures",
                "confidence": 0.86,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(procedure_payload))
            self.run_memory(project, "reflect", "--payload", json.dumps(correction_payload))
            rows = json.loads(self.run_memory(project, "list", "--type", "reflection", "--json").stdout)

        by_type = {row["experience_type"]: row for row in rows}
        self.assertEqual("inspect route target and page registration", by_type["procedure_experience"]["repair_action"])
        self.assertIn("pure layout", by_type["procedure_experience"]["negative_preconditions"])
        self.assertEqual("applying old route mapping without checking current source", by_type["correction_experience"]["anti_pattern"])
        self.assertEqual("unrelated resource loading failures", by_type["correction_experience"]["does_not_apply_to"])
        self.assertIsNone(by_type["correction_experience"]["skill_candidate"])

    def test_correction_experience_rejects_skill_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            payload = {
                "experience_type": "correction_experience",
                "task": "Correct stale Profile route memory",
                "summary": "Profile route maps to ProfilePage.",
                "lesson": "Use current source route registration.",
                "trigger_condition": "old route memory conflicts with source",
                "repair_action": "trust current route registration",
                "anti_pattern": "promoting a single correction into a skill",
                "skill_candidate": "arkts-route-correction-skill",
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNTIME),
                    "reflect",
                    "--payload",
                    json.dumps(payload),
                    "--project",
                    str(project),
                    "--memory-home",
                    str(self.memory_home(project)),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=os.environ.copy(),
            )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("correction_experience cannot set skill_candidate", result.stderr)


if __name__ == "__main__":
    unittest.main()
