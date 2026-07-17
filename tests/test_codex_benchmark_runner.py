# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.source_exploration import (
    exploration_contract,
    source_exploration_within_budget,
)


RUNNER = Path(__file__).resolve().parents[1] / "examples" / "codex-agent-benchmark-runner.py"


class CodexBenchmarkRunnerTests(unittest.TestCase):
    def test_runner_wraps_codex_result_and_measures_usage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            memory_query = root / "memory-query"
            memory_query.write_text(fake_memory_query(), encoding="utf-8")
            memory_query.chmod(0o755)
            fake = root / "fake-codex"
            fake.write_text(fake_codex(), encoding="utf-8")
            fake.chmod(0o755)
            request = benchmark_request(workspace, [str(memory_query), "<task-description>"])
            environment = os.environ.copy()
            environment["AGENT_BENCHMARK_CODEX"] = str(fake)
            environment["AGENT_BENCHMARK_CODEX_MODEL"] = "gpt-5.6-sol"
            environment["AGENT_BENCHMARK_CODEX_REASONING_EFFORT"] = "low"

            process = subprocess.run(
                [str(RUNNER)],
                input=json.dumps(request),
                text=True,
                capture_output=True,
                env=environment,
                check=True,
            )

            result = json.loads(process.stdout)
            self.assertEqual("case-1", result["case_id"])
            self.assertEqual("memory", result["variant"])
            self.assertEqual(1, result["trial_index"])
            self.assertEqual(125, result["token_estimate"])
            self.assertEqual("gpt-5.6-sol", result["runner_metadata"]["model"])
            self.assertEqual("low", result["runner_metadata"]["reasoning_effort"])
            self.assertEqual("runner_preloaded", result["runner_metadata"]["memory_delivery"])
            self.assertEqual("isolated_home", result["runner_metadata"]["user_context"])
            self.assertEqual(
                "anchor_first_gap_driven_v4",
                result["runner_metadata"]["retrieval_policy"],
            )
            self.assertEqual(1, result["expansion_rounds"])
            self.assertEqual(["missing_state_owner"], result["expansion_reason_codes"])
            self.assertEqual("supported_cause_found", result["stop_reason"])
            self.assertEqual("direct_source_mechanism", result["evidence_basis"])
            self.assertEqual(
                ["features/home/src/main/ets/pages/ProfilePage.ets"],
                result["mechanism_evidence_files"],
            )
            self.assertEqual([], result["supporting_files"])
            self.assertEqual(1, result["source_search_count"])
            self.assertEqual("runner_telemetry", result["source_search_count_source"])
            self.assertEqual(1, result["non_anchor_file_count"])
            self.assertGreater(result["memory_context_bytes"], 0)
            self.assertGreater(result["memory_context_token_estimate"], 0)
            self.assertGreaterEqual(result["elapsed_ms"], 0)

    def test_memory_prompt_contains_preloaded_context(self) -> None:
        module = load_runner_module()
        prompt = module.build_prompt(
            benchmark_request(Path("/workspace")),
            {"summary": "Profile route context."},
        )

        self.assertIn("Profile route context.", prompt)
        self.assertIn("queried once by the benchmark runner", prompt)
        self.assertIn("Treat its output only as context", prompt)
        self.assertIn("role=primary first", prompt)
        self.assertIn("without naming one allowed expansion reason", prompt)
        self.assertIn("at most 3 source-search invocations", prompt)
        self.assertIn("7 total investigated source files", prompt)
        self.assertIn("Every source file actually opened", prompt)
        self.assertIn("must appear exactly once in expansion_trace", prompt)
        self.assertIn("Stop with supported_cause_found", prompt)
        self.assertIn("concrete operation, branch, state transition, boundary, or API misuse", prompt)
        self.assertIn("inference_only", prompt)
        self.assertIn("parallel in-flight requests", prompt)
        self.assertIn("Use media for WebM", prompt)
        self.assertIn("Use api only when", prompt)
        self.assertIn("expansion_trace", prompt)
        self.assertIn("Report source_search_count", prompt)

    def test_memory_query_failure_stops_the_runner(self) -> None:
        module = load_runner_module()
        request = benchmark_request(Path("/tmp"), ["/usr/bin/false"])

        with self.assertRaisesRegex(SystemExit, "Agent Memory query failed"):
            module.load_memory_context(request, Path("/tmp"))

    def test_failure_output_keeps_start_and_end(self) -> None:
        module = load_runner_module()
        value = module.failure_output("", "start-" + ("x" * 5000) + "-end")

        self.assertIn("start-", value)
        self.assertIn("-end", value)

    def test_read_only_runner_caps_unverified_claims(self) -> None:
        module = load_runner_module()

        self.assertEqual("supported", module.cap_causal_level("verified"))
        self.assertEqual("association", module.cap_causal_level("association"))

    def test_baseline_has_no_memory_context_cost(self) -> None:
        module = load_runner_module()

        self.assertEqual(
            {"memory_context_bytes": 0, "memory_context_token_estimate": 0},
            module.memory_context_metrics(None),
        )

    def test_execution_metrics_count_anchor_hits(self) -> None:
        module = load_runner_module()
        result = {
            "investigated_files": ["src/Login.ets", "src/Other.ets", "src/Login.ets"],
        }
        context = {
            "query_handoff": {
                "code_anchors": [
                    {"file_path": "src/Login.ets", "role": "primary"},
                    {"file_path": "src/Profile.ets", "role": "expansion"},
                ],
            },
        }

        self.assertEqual(
            {
                "source_file_count": 2,
                "memory_anchor_hit_count": 1,
                "primary_anchor_hit_count": 1,
                "non_anchor_file_count": 1,
            },
            module.execution_metrics(result, context),
        )

    def test_source_search_count_comes_from_completed_command_telemetry(self) -> None:
        module = load_runner_module()
        events = "\n".join([
            json.dumps({
                "type": "item.completed",
                "item": {
                    "id": "one",
                    "type": "command_execution",
                    "command": "/bin/zsh -lc 'rg -n Login src && grep -R route src'",
                },
            }),
            json.dumps({
                "type": "item.completed",
                "item": {
                    "id": "two",
                    "type": "command_execution",
                    "command": "sed -n '1,80p' src/Login.ets",
                },
            }),
        ])

        self.assertEqual(
            {"source_search_count": 2, "source_search_count_source": "runner_telemetry"},
            module.source_search_metrics(events, {"source_search_count": 9}),
        )

    def test_source_search_count_falls_back_without_command_telemetry(self) -> None:
        module = load_runner_module()

        self.assertEqual(
            {"source_search_count": 2, "source_search_count_source": "agent_reported"},
            module.source_search_metrics(
                json.dumps({"type": "turn.completed"}),
                {"source_search_count": 2},
            ),
        )

    def test_source_exploration_contract_and_gate(self) -> None:
        contract = exploration_contract()
        observation = {
            "variant": "memory",
            "exploration_metrics_reported": True,
            "source_file_count": 5,
            "source_search_count": 3,
            "primary_anchor_hit_count": 3,
            "non_anchor_file_count": 2,
            "expansion_rounds": 1,
            "expansion_reason_codes": ["missing_caller"],
            "stop_reason": "supported_cause_found",
            "evidence_basis": "direct_source_mechanism",
            "mechanism_evidence_files": ["src/Profile.ets"],
            "predicted_files": ["src/Profile.ets"],
            "investigated_files": ["src/Profile.ets", "src/Router.ets"],
        }

        self.assertEqual(3, contract["limits"]["primary"])
        self.assertTrue(source_exploration_within_budget([observation]))
        observation["source_file_count"] = 6
        self.assertFalse(source_exploration_within_budget([observation]))

    def test_output_schema_requires_exploration_audit(self) -> None:
        module = load_runner_module()
        required = set(module.output_schema()["required"])

        self.assertTrue({
            "supporting_files",
            "source_search_count",
            "expansion_trace",
            "stop_reason",
            "evidence_basis",
            "mechanism_evidence_files",
        }.issubset(required))

    def test_runner_derives_expansion_audit_from_trace(self) -> None:
        module = load_runner_module()
        result = module.normalize_exploration({
            "expansion_trace": [
                {"reason": "missing_caller", "files": ["src/A.ets", "src/B.ets"]},
                {"reason": "missing_state_owner", "files": ["src/C.ets"]},
            ],
        })

        self.assertEqual(2, result["expansion_rounds"])
        self.assertEqual(
            ["missing_caller", "missing_state_owner"],
            result["expansion_reason_codes"],
        )

    def test_file_roles_are_disjoint_and_all_investigated(self) -> None:
        module = load_runner_module()
        result = module.normalize_file_roles({
            "predicted_files": ["src/Cause.ets"],
            "supporting_files": ["src/Caller.ets", "src/Cause.ets"],
            "investigated_files": ["src/Other.ets"],
        })

        self.assertEqual(["src/Cause.ets"], result["predicted_files"])
        self.assertEqual(["src/Caller.ets"], result["supporting_files"])
        self.assertEqual(
            ["src/Other.ets", "src/Cause.ets", "src/Caller.ets"],
            result["investigated_files"],
        )

    def test_old_runner_without_exploration_metrics_remains_compatible(self) -> None:
        self.assertTrue(source_exploration_within_budget([{"variant": "memory"}]))


def benchmark_request(workspace: Path, query_command: list[str] | None = None) -> dict:
    return {
        "schema_version": "agent-benchmark-request/v1",
        "case_id": "case-1",
        "variant": "memory",
        "trial_index": 1,
        "workspace": str(workspace),
        "case": {
            "id": "case-1",
            "task_type": "diagnosis",
            "task": {"description": "Profile does not load.", "constraints": []},
        },
        "instructions": ["Inspect only the supplied workspace."],
        "memory_access": {
            "query_command": query_command or ["/usr/bin/true"],
        },
        "response_schema": {},
    }


def load_runner_module():
    spec = importlib.util.spec_from_file_location("codex_benchmark_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_codex() -> str:
    return """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]
output = Path(args[args.index("--output-last-message") + 1])
result = {
    "schema_version": "agent-benchmark-response/v1",
    "case_id": "model-value",
    "variant": "model-value",
    "root_cause_category": "state",
    "predicted_files": ["features/home/src/main/ets/pages/ProfilePage.ets"],
    "supporting_files": [],
    "investigated_files": ["features/home/src/main/ets/pages/ProfilePage.ets"],
    "causal_level": "supported",
    "verification_status": "unknown",
    "query_rounds": 1,
    "source_search_count": 1,
    "expansion_trace": [
        {"reason": "missing_state_owner", "files": ["features/home/src/main/ets/pages/ProfilePage.ets"]}
    ],
    "stop_reason": "supported_cause_found",
    "evidence_basis": "direct_source_mechanism",
    "mechanism_evidence_files": ["features/home/src/main/ets/pages/ProfilePage.ets"],
    "token_estimate": 0,
    "elapsed_ms": 0,
    "summary": "Profile state branch is incorrect."
}
output.write_text(json.dumps(result))
print(json.dumps({
    "type": "item.completed",
    "item": {
        "id": "search-1",
        "type": "command_execution",
        "command": "rg -n ProfilePage features/home/src/main/ets/pages"
    }
}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 25}}))
"""


def fake_memory_query() -> str:
    return """#!/usr/bin/env python3
import json
import sys

assert sys.argv[1] == "Profile does not load."
print(json.dumps({"summary": "Profile route context."}))
"""
