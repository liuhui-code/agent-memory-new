# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.agent_benchmark_cases import eligible_cases
from tools.agent_memory_runtime.agent_benchmark import (
    bounded_trials,
    runner_configuration,
    select_cases,
)
from tools.agent_memory_runtime.agent_benchmark_eval import (
    canonical_category,
    causal_level_satisfies,
    evaluate_agent_benchmark,
    every_case_non_regression,
    memory_root_cause_trial_stability,
    memory_context_within_budget,
    runner_configuration_consistent,
    trial_stability_non_regression,
)
from tools.agent_memory_runtime.benchmark_memory import design_command, diagnosis_command
from tools.agent_memory_runtime.benchmark_history import build_history_cases
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
        self.assertEqual("fail", payload["efficiency_gate"])
        self.assertEqual("fail", payload["promotion_gate"])
        self.assertGreater(payload["context_uplift"]["agent_outcome_score_delta"], 0)
        self.assertEqual(500.0, payload["context_uplift"]["token_savings"])
        health = json.loads(self.run_memory(self.project, "maintain-health", "--json").stdout)
        self.assertEqual("pass", health["agent_benchmark"]["quality_gate"])
        self.assertEqual("fail", health["agent_benchmark"]["efficiency_gate"])
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

    def test_external_runner_repeats_paired_trials(self) -> None:
        self.git("init", "-q")
        source = self.project / "src" / "Profile.ets"
        source.parent.mkdir()
        source.write_text("router.pushUrl({ url: 'pages/Profile' })\n", encoding="utf-8")
        self.commit("add profile route")
        cases = Path(self.temp_dir.name) / "mutations.json"
        responses = Path(self.temp_dir.name) / "runner-responses.json"
        self.run_memory(
            self.project, "eval-mutate-arkts", "--target", str(cases),
            "--operator", "corrupt_route_target", "--limit", "1", "--json",
        )
        runner = Path(self.temp_dir.name) / "benchmark-runner"
        runner.write_text(runner_script(), encoding="utf-8")
        runner.chmod(0o755)

        payload = json.loads(self.run_memory(
            self.project, "eval-agent-benchmark",
            "--cases", str(cases), "--runner", str(runner),
            "--trials", "2", "--output-responses", str(responses), "--json",
        ).stdout)

        observations = json.loads(responses.read_text())["observations"]
        self.assertEqual(4, payload["summary"]["observation_count"])
        self.assertEqual(2, payload["summary"]["trial_count"])
        self.assertEqual([1, 1, 2, 2], [item["trial_index"] for item in observations])

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
        self.assertEqual("ui_layout", canonical_category("ArkTS breakpoint layout"))
        self.assertEqual("media", canonical_category("WebM sticker media"))

    def test_split_view_fix_remains_a_diagnosis_case(self) -> None:
        cases = build_history_cases([{
            "commit": "a" * 40,
            "parent": "b" * 40,
            "committed_at": "2026-01-01T00:00:00Z",
            "subject": "fix: nav in split view",
            "files": ["features/home/src/main/ets/views/Chat/ChatList.ets"],
        }], 1)

        self.assertEqual("diagnosis", cases[0]["task_type"])
        self.assertEqual("route", cases[0]["oracle"]["root_cause_category"])

    def test_design_benchmark_uses_agent_owned_design_context(self) -> None:
        command = design_command(
            Path("/runtime/agent_memory.py"),
            Path("/workspace"),
            Path("/memory-home"),
        )

        self.assertIn("design-context", command)
        self.assertIn("--compact", command)
        self.assertNotIn("design-assist", command)

    def test_diagnosis_benchmark_uses_compact_context(self) -> None:
        command = diagnosis_command(
            Path("/runtime/agent_memory.py"),
            Path("/workspace"),
            Path("/memory-home"),
        )

        self.assertIn("context", command)
        self.assertIn("--compact", command)

    def test_case_ids_select_in_requested_order(self) -> None:
        cases = [{"id": "a"}, {"id": "b"}, {"id": "c"}]

        selected = select_cases(cases, ["c", "a", "c"])

        self.assertEqual(["c", "a"], [case["id"] for case in selected])

    def test_case_id_rejects_ineligible_case(self) -> None:
        with self.assertRaises(SystemExit):
            select_cases([{"id": "eligible"}], ["rejected"])

    def test_runner_configuration_requires_matching_metadata(self) -> None:
        values = [
            {"runner_metadata": {"model": "gpt-5.6-sol", "reasoning_effort": "low"}},
            {"runner_metadata": {"model": "gpt-5.6-sol", "reasoning_effort": "low"}},
        ]

        self.assertTrue(runner_configuration_consistent(values))
        self.assertTrue(runner_configuration(values)["consistent"])
        values[1]["runner_metadata"]["reasoning_effort"] = "high"
        self.assertFalse(runner_configuration_consistent(values))

    def test_memory_context_budget_rejects_oversized_payload(self) -> None:
        values = [
            observation("case-1", "baseline", "route", ["src/Profile.ets"], 1000),
            observation("case-1", "memory", "route", ["src/Profile.ets"], 900),
        ]
        self.assertTrue(memory_context_within_budget(values))

        values[1]["memory_context_token_estimate"] = 1501

        self.assertFalse(memory_context_within_budget(values))

    def test_every_case_gate_prevents_aggregate_masking(self) -> None:
        results = [
            {"context_outcome_delta": 0.4},
            {"context_outcome_delta": 0.0},
            {"context_outcome_delta": -0.4},
        ]

        self.assertFalse(every_case_non_regression(results))

    def test_trial_stability_requires_two_of_three_non_regressions(self) -> None:
        results = [{"trial_count": 3, "trial_non_regression_rate": 1 / 3}]

        self.assertFalse(trial_stability_non_regression(results))
        results[0]["trial_non_regression_rate"] = 2 / 3
        self.assertTrue(trial_stability_non_regression(results))

    def test_root_cause_trial_stability_requires_two_of_three_agreement(self) -> None:
        results = [{"trial_count": 3, "memory_root_cause_consistency": 1 / 3}]

        self.assertFalse(memory_root_cause_trial_stability(results))
        results[0]["memory_root_cause_consistency"] = 2 / 3
        self.assertTrue(memory_root_cause_trial_stability(results))

    def test_single_trial_does_not_claim_or_gate_stability(self) -> None:
        results = [{
            "trial_count": 1,
            "trial_non_regression_rate": 0.0,
            "memory_root_cause_consistency": 0.0,
        }]

        self.assertTrue(trial_stability_non_regression(results))
        self.assertTrue(memory_root_cause_trial_stability(results))

    def test_repeated_scoring_preserves_trial_results(self) -> None:
        pack = benchmark_pack(self.project)
        values = []
        for trial, memory_category in enumerate(("route", "resource", "resource"), 1):
            baseline = observation("case-1", "baseline", "route", ["src/Profile.ets"], 1000)
            memory = observation("case-1", "memory", memory_category, ["src/Profile.ets"], 800)
            baseline["trial_index"] = trial
            memory["trial_index"] = trial
            values.extend((baseline, memory))

        result = evaluate_agent_benchmark(pack, pack["cases"], values)

        self.assertEqual(3, result["summary"]["trial_count"])
        self.assertTrue(result["summary"]["stability_evaluated"])
        self.assertEqual(3, len(result["cases"][0]["trial_results"]))
        self.assertFalse(result["gate_checks"]["trial_stability_non_regression"])
        self.assertEqual(0.6667, result["cases"][0]["memory_root_cause_consistency"])

    def test_trial_count_is_bounded(self) -> None:
        self.assertEqual(3, bounded_trials(3))
        with self.assertRaises(SystemExit):
            bounded_trials(0)
        with self.assertRaises(SystemExit):
            bounded_trials(11)

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
        "memory_context_bytes": 400 if variant == "memory" else 0,
        "memory_context_token_estimate": 100 if variant == "memory" else 0,
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
    "trial_index": request.get("trial_index", 1),
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
