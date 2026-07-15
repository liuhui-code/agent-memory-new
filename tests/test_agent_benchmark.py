# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.agent_benchmark_cases import eligible_cases
from tools.agent_memory_runtime.agent_benchmark_eval import canonical_category, causal_level_satisfies
from tools.agent_memory_runtime.agent_benchmark_protocol import validate_observation


class AgentBenchmarkTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "demo"
        self.project.mkdir()
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def git(self, *args: str) -> str:
        process = subprocess.run(
            ["git", *args],
            cwd=self.project,
            text=True,
            capture_output=True,
            check=True,
        )
        return process.stdout.strip()

    def commit(self, message: str) -> str:
        self.git("add", ".")
        self.git(
            "-c", "user.name=Agent Benchmark Tests",
            "-c", "user.email=tests@example.invalid",
            "commit", "-qm", message,
        )
        return self.git("rev-parse", "HEAD")

    def seed_git_route_fix(self) -> tuple[str, str]:
        self.git("init", "-q")
        source = self.project / "src" / "Profile.ets"
        source.parent.mkdir()
        source.write_text("router.pushUrl({ url: 'pages/Profile' })\n", encoding="utf-8")
        before = self.commit("initial profile route")
        source.write_text("router.pushUrl({ url: 'pages/ProfileDetail' })\n", encoding="utf-8")
        test = self.project / "tests" / "ProfileRouteTest.ets"
        test.parent.mkdir()
        test.write_text("expect('pages/ProfileDetail')\n", encoding="utf-8")
        after = self.commit("fix route blank screen")
        return before, after

    def test_history_harvester_builds_review_only_cases_with_hidden_oracle(self) -> None:
        before, after = self.seed_git_route_fix()
        target = Path(self.temp_dir.name) / "history.json"

        payload = json.loads(self.run_memory(
            self.project,
            "eval-harvest-history",
            "--target", str(target),
            "--limit", "5",
            "--json",
        ).stdout)

        case = json.loads(target.read_text(encoding="utf-8"))["cases"][0]
        self.assertEqual("draft", case["review_status"])
        self.assertEqual(before, case["source"]["before_revision"])
        self.assertEqual(after, case["source"]["after_revision"])
        self.assertIn("src/Profile.ets", case["oracle"]["expected_files"])
        self.assertIn("oracle", case["leakage_guard"]["hidden_fields"])
        self.assertTrue(target.exists())

    def test_mutation_generator_does_not_modify_source(self) -> None:
        source = self.project / "src" / "Profile.ets"
        source.parent.mkdir()
        original = (
            "async function load() { await fetchProfile() }\n"
            "const oldRoute = 'pages/Profile'\n"
            "router.pushUrl({ url: 'pages/Profile' })\n"
            "const icon = $r('app.media.profile')\n"
        )
        source.write_text(original, encoding="utf-8")
        target = Path(self.temp_dir.name) / "mutations.json"

        payload = json.loads(self.run_memory(
            self.project,
            "eval-mutate-arkts",
            "--target", str(target),
            "--operator", "corrupt_route_target",
            "--limit", "1",
            "--json",
        ).stdout)

        mutation = json.loads(target.read_text(encoding="utf-8"))["cases"][0]["source"]["mutation"]
        self.assertEqual("corrupt_route_target", mutation["operator"])
        self.assertEqual("pages/Profile__missing__", mutation["replacement"])
        self.assertEqual(2, mutation["occurrence"])
        self.assertEqual(original, source.read_text(encoding="utf-8"))
        self.assertFalse(payload["audit"]["source_modified"])
        self.assertNotIn("cases", payload)

    def test_recorded_ab_benchmark_reports_context_uplift_and_governance(self) -> None:
        cases = Path(self.temp_dir.name) / "cases.json"
        responses = Path(self.temp_dir.name) / "responses.json"
        write_json(cases, benchmark_pack(self.project))
        write_json(responses, response_pack([
            observation("case-1", "baseline", "resource", ["src/Other.ets"], 1000),
            observation("case-1", "memory", "route", ["src/Profile.ets"], 500),
        ]))

        payload = json.loads(self.run_memory(
            self.project,
            "eval-agent-benchmark",
            "--cases", str(cases),
            "--responses", str(responses),
            "--json",
        ).stdout)

        self.assertEqual("pass", payload["quality_gate"])
        self.assertGreater(payload["context_uplift"]["agent_outcome_score_delta"], 0)
        self.assertEqual(500.0, payload["context_uplift"]["token_savings"])
        health = json.loads(self.run_memory(self.project, "maintain-health", "--json").stdout)
        self.assertEqual("pass", health["agent_benchmark"]["quality_gate"])
        self.assertEqual(1, health["agent_benchmark"]["case_count"])

    def test_external_runner_receives_materialized_mutation_without_oracle(self) -> None:
        self.git("init", "-q")
        source = self.project / "src" / "Profile.ets"
        source.parent.mkdir()
        source.write_text("router.pushUrl({ url: 'pages/Profile' })\n", encoding="utf-8")
        self.commit("add profile route")
        cases = Path(self.temp_dir.name) / "mutations.json"
        responses = Path(self.temp_dir.name) / "runner-responses.json"
        self.run_memory(
            self.project,
            "eval-mutate-arkts",
            "--target", str(cases),
            "--operator", "corrupt_route_target",
            "--limit", "1",
            "--json",
        )
        runner = Path(self.temp_dir.name) / "benchmark-runner"
        runner.write_text(runner_script(), encoding="utf-8")
        runner.chmod(0o755)

        payload = json.loads(self.run_memory(
            self.project,
            "eval-agent-benchmark",
            "--cases", str(cases),
            "--runner", str(runner),
            "--output-responses", str(responses),
            "--json",
        ).stdout)

        self.assertEqual("pass", payload["quality_gate"])
        self.assertEqual("external", payload["runner_mode"])
        self.assertEqual(2, payload["summary"]["observation_count"])
        self.assertEqual("agent-benchmark-responses/v1", json.loads(responses.read_text())["schema_version"])

    def test_runner_response_rejects_private_reasoning_fields(self) -> None:
        value = observation("case-1", "memory", "route", ["src/Profile.ets"], 500)
        value["thoughts"] = "private reasoning"

        with self.assertRaises(SystemExit):
            validate_observation(value)

    def test_holdout_pack_never_allows_draft_cases(self) -> None:
        pack = benchmark_pack(self.project)
        pack["suite"] = "holdout"
        pack["cases"][0]["review_status"] = "draft"

        self.assertEqual([], eligible_cases(pack, allow_drafts=True))

    def test_agent_category_phrases_are_normalized_without_fuzzy_judging(self) -> None:
        self.assertEqual("route", canonical_category("navigation route target typo"))
        self.assertEqual("async", canonical_category("await ordering regression"))
        self.assertEqual("database_failure", canonical_category("database failure"))

    def test_verified_causal_evidence_satisfies_supported_oracle(self) -> None:
        self.assertTrue(causal_level_satisfies("verified", "supported"))
        self.assertFalse(causal_level_satisfies("association", "supported"))
        self.assertFalse(causal_level_satisfies("rejected", "supported"))


def benchmark_pack(project: Path) -> dict:
    return {
        "schema_version": "agent-benchmark-cases/v1",
        "suite": "development",
        "project_path": str(project),
        "cases": [{
            "id": "case-1",
            "task_type": "diagnosis",
            "review_status": "validated",
            "task": {"description": "Profile navigation opens a blank destination."},
            "source": {"before_revision": "working-tree"},
            "provenance": {"kind": "reviewed_incident"},
            "oracle": {
                "expected_files": ["src/Profile.ets"],
                "forbidden_files": ["src/Other.ets"],
                "root_cause_category": "route",
                "expected_causal_level": "supported",
            },
        }],
    }


def observation(case_id: str, variant: str, category: str, files: list[str], tokens: int) -> dict:
    return {
        "schema_version": "agent-benchmark-response/v1",
        "case_id": case_id,
        "variant": variant,
        "root_cause_category": category,
        "predicted_files": files,
        "investigated_files": files,
        "causal_level": "supported",
        "verification_status": "pass" if variant == "memory" else "unknown",
        "query_rounds": 1,
        "token_estimate": tokens,
        "elapsed_ms": 100,
        "summary": "bounded result",
    }


def response_pack(observations: list[dict]) -> dict:
    return {"schema_version": "agent-benchmark-responses/v1", "observations": observations}


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def runner_script() -> str:
    return """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

request = json.load(sys.stdin)
assert "oracle" not in request["case"]
assert "mutation" not in request["case"]["source"]
text = (Path(request["workspace"]) / "src" / "Profile.ets").read_text()
assert "pages/Profile__missing__" in text
memory = request["variant"] == "memory"
if memory:
    assert request["memory_access"]["isolated"] is True
    assert Path(request["memory_access"]["runtime"]).is_file()
else:
    assert "memory_access" not in request
result = {
    "schema_version": "agent-benchmark-response/v1",
    "case_id": request["case_id"],
    "variant": request["variant"],
    "root_cause_category": "route" if memory else "resource",
    "predicted_files": ["src/Profile.ets"] if memory else ["src/Other.ets"],
    "investigated_files": ["src/Profile.ets"],
    "causal_level": "supported",
    "verification_status": "pass" if memory else "unknown",
    "query_rounds": 1,
    "token_estimate": 500 if memory else 1000,
    "elapsed_ms": 100,
    "summary": "bounded result",
}
json.dump(result, sys.stdout)
"""
