# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.agent_benchmark_eval import evaluate_agent_benchmark
from tools.agent_memory_runtime.agent_benchmark_governance import agent_benchmark_summary
from tools.agent_memory_runtime.storage import resolve_project


class AgentBenchmarkCostTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "demo"
        self.project.mkdir()
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_efficiency_gate_is_independent_from_quality_gate(self) -> None:
        pack = benchmark_pack(self.project)
        baseline = observation("baseline", 1000, 1000, 2, 900, 100)
        memory = observation("memory", 1050, 1100, 1, 940, 110)

        passing = evaluate_agent_benchmark(pack, pack["cases"], [baseline, memory])

        self.assertEqual("pass", passing["quality_gate"])
        self.assertEqual("pass", passing["efficiency_gate"])
        self.assertEqual("pass", passing["promotion_gate"])
        self.assertEqual(1.0, passing["efficiency_metrics"]["cost_attribution_coverage"])
        self.assertEqual(0.05, passing["efficiency_metrics"]["token_overhead_ratio"])
        self.assertEqual(
            1.0,
            passing["efficiency_metrics"]["memory_source_read_amplification"],
        )

        memory.update({
            "token_estimate": 1200,
            "model_input_tokens": 1090,
            "model_uncached_input_tokens": 1090,
            "elapsed_ms": 1300,
        })
        failing = evaluate_agent_benchmark(pack, pack["cases"], [baseline, memory])

        self.assertEqual("pass", failing["quality_gate"])
        self.assertEqual("fail", failing["efficiency_gate"])
        self.assertEqual("fail", failing["promotion_gate"])
        self.assertFalse(
            failing["efficiency_gate_checks"]["token_overhead_within_budget"]
        )

    def test_cli_can_fail_on_efficiency_without_failing_quality(self) -> None:
        cases = Path(self.temp_dir.name) / "cases.json"
        responses = Path(self.temp_dir.name) / "responses.json"
        write_json(cases, benchmark_pack(self.project))
        write_json(responses, {
            "schema_version": "agent-benchmark-responses/v1",
            "observations": [
                observation("baseline", 1000, 1000, 2, 900, 100),
                observation("memory", 1300, 1300, 1, 1170, 130),
            ],
        })

        with self.assertRaises(subprocess.CalledProcessError) as caught:
            self.run_memory(
                self.project,
                "eval-agent-benchmark",
                "--cases", str(cases),
                "--responses", str(responses),
                "--fail-on-efficiency-fail",
                "--json",
            )

        payload = json.loads(caught.exception.stdout)
        self.assertEqual("pass", payload["quality_gate"])
        self.assertEqual("fail", payload["efficiency_gate"])

    def test_read_amplification_is_an_efficiency_not_quality_gate(self) -> None:
        pack = benchmark_pack(self.project)
        baseline = observation("baseline", 1000, 1000, 1, 900, 100)
        memory = observation("memory", 1000, 1000, 1, 900, 100)
        memory["source_read_count"] = 3

        result = evaluate_agent_benchmark(pack, pack["cases"], [baseline, memory])

        self.assertEqual("pass", result["quality_gate"])
        self.assertEqual("fail", result["efficiency_gate"])
        self.assertFalse(
            result["efficiency_gate_checks"]["source_read_amplification_within_budget"]
        )
        self.assertFalse(
            result["efficiency_gate_checks"]["source_read_amplification_non_regression"]
        )
        self.assertEqual(2.0, result["efficiency_limits"]["source_read_amplification"])

    def test_governance_summary_exposes_memory_read_amplification(self) -> None:
        project = resolve_project(str(self.project), str(self.memory_home(self.project)))
        write_json(project.runtime_dir / "last_agent_benchmark.json", {
            "quality_gate": "pass",
            "efficiency_gate": "fail",
            "promotion_gate": "fail",
            "summary": {"case_count": 1, "suite": "development"},
            "efficiency_metrics": {
                "memory_source_read_amplification": 1.75,
                "per_case": [{
                    "case_id": "case-1",
                    "checks": {"token_overhead_within_budget": False},
                }],
            },
        })

        summary = agent_benchmark_summary(project)

        self.assertEqual(1.75, summary["source_read_amplification"])
        self.assertEqual(1, summary["failed_case_efficiency_count"])
        self.assertEqual(["case-1"], summary["failed_case_efficiency_ids"])

    def test_per_case_read_amplification_cannot_hide_in_aggregate(self) -> None:
        pack = two_case_benchmark_pack(self.project)
        values = [
            case_observation("case-1", "baseline", reads=3),
            case_observation("case-1", "memory", reads=1),
            case_observation("case-2", "baseline", reads=1),
            case_observation("case-2", "memory", reads=3),
        ]

        result = evaluate_agent_benchmark(pack, pack["cases"], values)

        self.assertTrue(
            result["efficiency_gate_checks"]["source_read_amplification_within_budget"]
        )
        self.assertTrue(
            result["efficiency_gate_checks"]["source_read_amplification_non_regression"]
        )
        self.assertFalse(
            result["efficiency_gate_checks"][
                "every_case_source_read_amplification_within_budget"
            ]
        )
        self.assertFalse(
            result["efficiency_gate_checks"][
                "every_case_source_read_amplification_non_regression"
            ]
        )

    def test_per_case_token_and_elapsed_overhead_cannot_hide_in_aggregate(self) -> None:
        pack = two_case_benchmark_pack(self.project)
        values = [
            case_observation("case-1", "baseline", tokens=2000, elapsed=2000),
            case_observation("case-1", "memory", tokens=1000, elapsed=1000),
            case_observation("case-2", "baseline", tokens=1000, elapsed=1000),
            case_observation("case-2", "memory", tokens=1300, elapsed=1300),
        ]

        result = evaluate_agent_benchmark(pack, pack["cases"], values)

        self.assertTrue(result["efficiency_gate_checks"]["token_overhead_within_budget"])
        self.assertTrue(result["efficiency_gate_checks"]["elapsed_overhead_within_budget"])
        self.assertFalse(
            result["efficiency_gate_checks"]["every_case_token_overhead_within_budget"]
        )
        self.assertFalse(
            result["efficiency_gate_checks"]["every_case_elapsed_overhead_within_budget"]
        )

    def test_unselected_response_cases_do_not_affect_efficiency(self) -> None:
        pack = two_case_benchmark_pack(self.project)
        values = [
            case_observation("case-1", "baseline"),
            case_observation("case-1", "memory"),
            case_observation("case-2", "baseline"),
            case_observation("case-2", "memory", reads=5, tokens=3000, elapsed=3000),
        ]

        result = evaluate_agent_benchmark(pack, pack["cases"][:1], values)

        self.assertEqual("pass", result["efficiency_gate"])
        self.assertEqual(
            ["case-1"],
            [item["case_id"] for item in result["efficiency_metrics"]["per_case"]],
        )


def benchmark_pack(project: Path) -> dict:
    return {
        "schema_version": "agent-benchmark-cases/v1",
        "suite": "development",
        "project_path": str(project),
        "cases": [{
            "id": "case-1",
            "task_type": "diagnosis",
            "review_status": "validated",
            "task": {"description": "Profile route fails.", "constraints": []},
            "source": {"before_revision": "abc"},
            "oracle": {
                "root_cause_category": "route",
                "expected_files": ["src/Profile.ets"],
                "forbidden_files": [],
                "expected_causal_level": "supported",
            },
        }],
    }


def two_case_benchmark_pack(project: Path) -> dict:
    value = benchmark_pack(project)
    second = json.loads(json.dumps(value["cases"][0]))
    second["id"] = "case-2"
    value["cases"].append(second)
    return value


def case_observation(
    case_id: str,
    variant: str,
    *,
    reads: int = 1,
    tokens: int = 1000,
    elapsed: int = 1000,
) -> dict:
    value = observation(variant, tokens, elapsed, 1, tokens - 100, 100)
    value["case_id"] = case_id
    value["source_read_count"] = reads
    return value


def observation(
    variant: str,
    tokens: int,
    elapsed_ms: int,
    searches: int,
    input_tokens: int,
    output_tokens: int,
) -> dict:
    return {
        "schema_version": "agent-benchmark-response/v1",
        "case_id": "case-1",
        "variant": variant,
        "root_cause_category": "route",
        "predicted_files": ["src/Profile.ets"],
        "supporting_files": [],
        "investigated_files": ["src/Profile.ets"],
        "causal_level": "supported",
        "verification_status": "unknown",
        "query_rounds": 1,
        "source_search_count": searches,
        "token_estimate": tokens,
        "model_input_tokens": input_tokens,
        "model_cached_input_tokens": 0,
        "model_uncached_input_tokens": input_tokens,
        "model_output_tokens": output_tokens,
        "model_reasoning_tokens": 0,
        "command_count": searches + 1,
        "command_output_bytes": 1000,
        "source_read_count": 1,
        "source_read_output_bytes": 1000,
        "tool_error_count": 0,
        "source_search_miss_count": 0,
        "source_search_error_count": 0,
        "source_read_error_count": 0,
        "other_tool_error_count": 0,
        "source_file_count": 1,
        "cost_metrics_reported": True,
        "memory_context_bytes": 400 if variant == "memory" else 0,
        "memory_context_token_estimate": 100 if variant == "memory" else 0,
        "elapsed_ms": elapsed_ms,
        "summary": "The profile route owner contains the invalid transition.",
    }


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
