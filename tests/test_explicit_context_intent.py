# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import tempfile
from pathlib import Path

from agent_memory_test_base import AgentMemoryTestBase


class ExplicitContextIntentTests(AgentMemoryTestBase):
    def seed_procedure(self, project: Path) -> None:
        payload = {
            "experience_type": "procedure_experience",
            "task_type": "workflow",
            "outcome": "success",
            "task": "refresh cached files safely",
            "lesson": "Refresh cached files in bounded groups and verify before publishing.",
            "trigger_condition": "A cache file refresh workflow is requested.",
            "repair_action": "Refresh bounded groups, verify the generation, then publish.",
            "verification_method": "Run the controlled cache refresh fixture.",
            "source_cases": ["development_fixture:intent-contract-cache-refresh"],
            "negative_preconditions": ["Do not use for read-only cache lookup."],
            "confidence": 0.9,
        }
        self.run_memory(project, "reflect", "--payload", json.dumps(payload))

    def test_explicit_procedure_intent_overrides_domain_word_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_procedure(project)

            for query in (
                "how should the current cache file refresh proceed",
                "优化缓存文件刷新流程 cache refresh workflow",
            ):
                with self.subTest(query=query):
                    result = self.run_memory(
                        project,
                        "context",
                        "--query",
                        query,
                        "--intent",
                        "procedure_reuse",
                        "--compact",
                        "--json",
                    )
                    data = json.loads(result.stdout)
                    self.assertEqual("procedure_reuse", data["memory_intent"])
                    self.assertEqual("explicit", data["memory_intent_source"])
                    self.assertEqual(1, data["query_handoff"]["experience_refs"][0]["reflection_id"])

    def test_omitted_intent_preserves_inference_and_reports_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "app"
            project.mkdir()
            self.seed_procedure(project)

            result = self.run_memory(
                project,
                "context",
                "--query",
                "how should the current cache file refresh proceed",
                "--compact",
                "--json",
            )
            data = json.loads(result.stdout)

            self.assertEqual("memory_maintenance", data["memory_intent"])
            self.assertEqual("inferred", data["memory_intent_source"])
