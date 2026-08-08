# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from examples.codex_benchmark_memory_telemetry import memory_query_metrics
from examples.codex_benchmark_selective import prepare_selective_query_skill
from examples.codex_benchmark_prompt import build_prompt
from tools.agent_memory_runtime.agent_benchmark_eval import evaluate_agent_benchmark
from tools.agent_memory_runtime.agent_benchmark import treatment_mode
from tools.agent_memory_runtime.agent_benchmark_cases import validate_case_pack
from tools.agent_memory_runtime.agent_benchmark_measurement import (
    memory_context_within_budget,
    measurement_contract_audit,
)
from tools.agent_memory_runtime.agent_benchmark_selective import selective_query_audit
from tools.agent_memory_runtime.agent_benchmark_protocol import runner_instructions
from tools.agent_memory_runtime.agent_benchmark_protocol import validate_observation
from tools.agent_memory_runtime.agent_benchmark_treatment import (
    SELECTIVE_TREATMENT_SCHEMA,
    SELECTIVE_TREATMENT_MODE,
    selective_treatment_metadata,
)


RUNNER = Path(__file__).resolve().parents[1] / "examples" / "codex-agent-benchmark-runner.py"


class SelectiveQueryMeasurementTests(unittest.TestCase):
    def test_selective_runner_exposes_skill_and_derives_query_usage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            (workspace / "src").mkdir(parents=True)
            (workspace / "src" / "Owner.ets").write_text(
                "export function load() { return false }\n", encoding="utf-8",
            )
            fake = root / "fake-codex"
            fake.write_text(fake_selective_codex(), encoding="utf-8")
            fake.chmod(0o755)
            request = selective_runner_request(workspace)
            environment = os.environ.copy()
            environment["AGENT_BENCHMARK_CODEX"] = str(fake)

            process = subprocess.run(
                [str(RUNNER)], input=json.dumps(request), text=True,
                capture_output=True, env=environment, check=True,
            )

            result = json.loads(process.stdout)
            self.assertEqual(1, result["memory_query_count"])
            self.assertEqual(1, result["memory_query_success_count"])
            self.assertEqual(0, result["memory_query_error_count"])
            self.assertEqual(["context"], result["memory_query_kinds"])
            self.assertEqual(1, result["memory_anchor_hit_count"])
            self.assertEqual(1, result["primary_anchor_hit_count"])
            self.assertGreater(result["memory_context_bytes"], 0)
            self.assertEqual(SELECTIVE_TREATMENT_SCHEMA, result["treatment_metadata"]["schema_version"])
            self.assertEqual("selective_query_skill/v3", result["runner_metadata"]["measurement_contract"])
            self.assertEqual("agent_selected_query_skill", result["runner_metadata"]["memory_delivery"])

    def test_selective_baseline_has_no_query_skill_or_memory_calls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            (workspace / "src").mkdir(parents=True)
            (workspace / "src" / "Owner.ets").write_text("export const ok = true\n")
            fake = root / "fake-codex"
            fake.write_text(fake_selective_baseline_codex(), encoding="utf-8")
            fake.chmod(0o755)
            request = selective_runner_request(workspace)
            request["variant"] = "baseline"
            request.pop("memory_access")
            environment = os.environ.copy()
            environment["AGENT_BENCHMARK_CODEX"] = str(fake)

            process = subprocess.run(
                [str(RUNNER)], input=json.dumps(request), text=True,
                capture_output=True, env=environment, check=True,
            )

            result = json.loads(process.stdout)
            self.assertEqual(0, result["memory_query_count"])
            self.assertEqual(0, result["memory_context_bytes"])
            self.assertFalse(result["treatment_metadata"]["query_skill_available"])

    def test_selective_runner_rejects_source_modification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            (workspace / "src").mkdir(parents=True)
            (workspace / "src" / "Owner.ets").write_text("export const ok = true\n")
            fake = root / "fake-codex"
            script = fake_selective_codex().replace(
                "output = Path(args[args.index(\"--output-last-message\") + 1])",
                "Path('src/Owner.ets').write_text('changed')\n"
                "output = Path(args[args.index(\"--output-last-message\") + 1])",
            )
            fake.write_text(script, encoding="utf-8")
            fake.chmod(0o755)
            environment = os.environ.copy()
            environment["AGENT_BENCHMARK_CODEX"] = str(fake)

            process = subprocess.run(
                [str(RUNNER)], input=json.dumps(selective_runner_request(workspace)),
                text=True, capture_output=True, env=environment, check=False,
            )

            self.assertNotEqual(0, process.returncode)
            self.assertIn("modified source", process.stderr)

    def test_selective_skill_install_uses_real_skill_with_path_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            access = {
                "query_command": [
                    "python3", "/runtime/tools/agent_memory.py", "context",
                    "--project", "/workspace", "--memory-home", "/memory",
                    "--query", "<task-description-or-agent-extracted-term>",
                    "--compact", "--json",
                ],
            }

            digest = prepare_selective_query_skill(root / "home", access, 3)

            target = root / "home" / ".agents" / "skills" / "agent-memory-query"
            skill = (target / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue((target / "references" / "incident-diagnosis.md").is_file())
            self.assertIn("# Agent Memory Query", skill)
            self.assertIn("## Benchmark Binding", skill)
            self.assertIn("/runtime/tools/agent_memory.py", skill)
            self.assertIn("<focused-query>", skill)
            self.assertIn("at most 3", skill)
            self.assertEqual(64, len(digest))

    def test_selective_prompt_is_group_blind_and_has_no_context_payload(self) -> None:
        request = {
            "case": {
                "task_type": "diagnosis",
                "task": {"description": "A request never completes."},
            },
            "instructions": ["Use available Skills only when relevant."],
            "response_schema": {},
        }

        baseline = build_prompt(request, None, SELECTIVE_TREATMENT_MODE)
        memory = build_prompt(request, None, SELECTIVE_TREATMENT_MODE)

        self.assertEqual(baseline, memory)
        self.assertIn("No Agent Memory context is preloaded", baseline)
        self.assertIn("TRIAGE -> GAP -> VERIFY -> STOP", baseline)
        self.assertNotIn("Agent Memory context payload", baseline)
        self.assertNotIn("queried once by the benchmark runner", baseline)

    def test_selective_runner_has_no_preloaded_context_contract(self) -> None:
        instructions = runner_instructions("memory", SELECTIVE_TREATMENT_MODE)

        self.assertTrue(any("No Agent Memory context is preloaded" in item for item in instructions))
        self.assertTrue(any("available Query Skill" in item for item in instructions))
        self.assertTrue(any("Never inspect Agent Memory databases" in item for item in instructions))
        self.assertFalse(any("Use preloaded Agent Memory context" in item for item in instructions))

    def test_v3_contract_exposes_only_query_skill_capability(self) -> None:
        observations = [
            selective_observation("baseline", query_count=0),
            selective_observation("memory", query_count=1),
        ]

        audit = measurement_contract_audit(observations)

        self.assertEqual("pass", audit["status"])
        self.assertTrue(audit["enforced"])
        self.assertTrue(audit["checks"]["baseline_query_skill_absent"])
        self.assertTrue(audit["checks"]["memory_query_skill_present"])
        self.assertTrue(audit["checks"]["preloaded_context_absent"])
        self.assertEqual(
            SELECTIVE_TREATMENT_SCHEMA,
            observations[1]["treatment_metadata"]["schema_version"],
        )
        self.assertEqual(
            SELECTIVE_TREATMENT_MODE,
            treatment_mode(observations, "preloaded-context"),
        )

    def test_selective_context_budget_allows_zero_activation(self) -> None:
        no_query = selective_observation("memory", 0)
        no_query.update({
            "memory_context_metrics_reported": True,
            "memory_context_token_estimate": 0,
        })
        one_query = selective_observation("memory", 1)
        one_query.update({
            "memory_context_metrics_reported": True,
            "memory_context_token_estimate": 1500,
        })

        self.assertTrue(memory_context_within_budget([no_query]))
        self.assertTrue(memory_context_within_budget([one_query]))
        one_query["memory_context_token_estimate"] = 1501
        self.assertFalse(memory_context_within_budget([one_query]))

    def test_selective_observation_normalizes_metrics_and_rejects_query_text(self) -> None:
        value = {
            **scored_selective_observation("memory", 1),
            "schema_version": "agent-benchmark-response/v1",
            "memory_query_success_count": 1,
            "memory_query_error_count": 0,
            "memory_query_total_output_bytes": 120,
            "memory_query_total_output_token_estimate": 30,
            "memory_query_kinds": ["context"],
            "memory_query_digests": ["a" * 64],
            "memory_query_anchor_paths": ["src/Owner.ets"],
            "memory_query_primary_anchor_paths": ["src/Owner.ets"],
        }

        normalized = validate_observation(value)

        self.assertEqual(1, normalized["memory_query_count"])
        self.assertEqual(120, normalized["memory_query_total_output_bytes"])
        self.assertEqual(["context"], normalized["memory_query_kinds"])
        value["memory_query_terms"] = ["private candidate"]
        with self.assertRaisesRegex(SystemExit, "query text or output"):
            validate_observation(value)

    def test_case_pack_rejects_invalid_query_skill_expectation(self) -> None:
        case = selective_eval_case("always")
        case.update({
            "task": {"description": "A request never completes."},
            "source": {"before_revision": "working-tree"},
        })
        pack = {
            "schema_version": "agent-benchmark-cases/v1",
            "suite": "development",
            "project_path": ".",
            "cases": [case],
        }

        with self.assertRaisesRegex(SystemExit, "query_skill_expectation.activation"):
            validate_case_pack(pack)

    def test_memory_query_telemetry_uses_commands_without_persisting_terms(self) -> None:
        context = json.dumps({
            "query_handoff": {
                "code_anchors": [
                    {"file_path": "src/Owner.ets", "role": "primary"},
                    {"file_path": "src/Caller.ets", "role": "expansion"},
                ],
            },
        })
        events = "\n".join([
            command_event(
                "one",
                "python3 /runtime/agent_memory.py context --query 'secret symptom' --compact --json",
                context,
                0,
            ),
            command_event(
                "two",
                "python3 /runtime/agent_memory.py search --query 'second cause' --json",
                "query failed",
                2,
            ),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10}}),
        ])

        metrics = memory_query_metrics(events)

        self.assertEqual(2, metrics["memory_query_count"])
        self.assertEqual(1, metrics["memory_query_success_count"])
        self.assertEqual(1, metrics["memory_query_error_count"])
        self.assertEqual(["context", "search"], metrics["memory_query_kinds"])
        self.assertEqual(["src/Caller.ets", "src/Owner.ets"], metrics["memory_query_anchor_paths"])
        self.assertEqual(["src/Owner.ets"], metrics["memory_query_primary_anchor_paths"])
        self.assertTrue(metrics["memory_query_metrics_reported"])
        encoded = json.dumps(metrics)
        self.assertNotIn("secret symptom", encoded)
        self.assertNotIn("second cause", encoded)
        self.assertNotIn(context, encoded)

    def test_selective_audit_reports_first_observable_activation_loss(self) -> None:
        cases = [
            selective_case("l0", "forbidden"),
            selective_case("log", "required"),
            selective_case("miss", "required"),
        ]
        observations = []
        for case_id, query_count in (("l0", 0), ("log", 1), ("miss", 0)):
            observations.extend([
                selective_observation("baseline", 0, case_id),
                selective_observation("memory", query_count, case_id),
            ])

        audit = selective_query_audit(cases, observations)

        self.assertEqual("fail", audit["status"])
        self.assertEqual(0.6667, audit["metrics"]["expectation_pass_rate"])
        by_id = {item["case_id"]: item for item in audit["cases"]}
        self.assertIsNone(by_id["l0"]["first_observable_loss"])
        self.assertIsNone(by_id["log"]["first_observable_loss"])
        self.assertEqual("skill_activation", by_id["miss"]["first_observable_loss"])

    def test_selective_protocol_failure_fails_the_quality_gate(self) -> None:
        case = selective_eval_case("required")
        observations = [
            scored_selective_observation("baseline", 0),
            scored_selective_observation("memory", 0),
        ]

        result = evaluate_agent_benchmark(
            {"suite": "development"}, [case], observations,
        )

        self.assertEqual("fail", result["selective_query"]["status"])
        self.assertFalse(result["gate_checks"]["selective_query_protocol_valid"])
        self.assertEqual("fail", result["quality_gate"])


def selective_observation(
    variant: str, query_count: int, case_id: str = "case-1",
) -> dict:
    return {
        "case_id": case_id,
        "variant": variant,
        "latency_metrics_reported": True,
        "memory_query_count": query_count,
        "memory_query_success_count": query_count,
        "memory_query_error_count": 0,
        "treatment_metadata": selective_treatment_metadata(
            variant,
            skill_digest="a" * 64 if variant == "memory" else None,
            query_limit=3,
        ),
    }


def selective_case(case_id: str, activation: str) -> dict:
    return {
        "id": case_id,
        "oracle": {
            "query_skill_expectation": {
                "activation": activation,
                "max_queries": 2,
            },
        },
    }


def selective_eval_case(activation: str) -> dict:
    return {
        **selective_case("case-1", activation),
        "task_type": "diagnosis",
        "review_status": "validated",
        "oracle": {
            **selective_case("case-1", activation)["oracle"],
            "expected_files": ["src/Owner.ets"],
            "forbidden_files": [],
            "root_cause_category": "state",
            "expected_causal_level": "supported",
        },
    }


def scored_selective_observation(variant: str, query_count: int) -> dict:
    return {
        **selective_observation(variant, query_count),
        "root_cause_category": "state",
        "predicted_files": ["src/Owner.ets"],
        "supporting_files": [],
        "investigated_files": ["src/Owner.ets"],
        "causal_level": "supported",
        "verification_status": "unknown",
        "query_rounds": 1,
        "source_search_count": 1,
        "token_estimate": 100,
        "elapsed_ms": 100,
        "memory_query_metrics_reported": True,
    }


def command_event(
    item_id: str, command: str, output: str, exit_code: int,
) -> str:
    return json.dumps({
        "type": "item.completed",
        "item": {
            "id": item_id,
            "type": "command_execution",
            "command": command,
            "aggregated_output": output,
            "exit_code": exit_code,
        },
    })


def selective_runner_request(workspace: Path) -> dict:
    return {
        "schema_version": "agent-benchmark-request/v1",
        "case_id": "case-1",
        "variant": "memory",
        "trial_index": 1,
        "treatment_mode": SELECTIVE_TREATMENT_MODE,
        "workspace": str(workspace),
        "case": {
            "id": "case-1",
            "task_type": "diagnosis",
            "task": {"description": "A request never completes.", "constraints": []},
        },
        "instructions": ["Use available Skills only when relevant."],
        "memory_access": {
            "query_command": [
                "python3", "/runtime/agent_memory.py", "context",
                "--project", str(workspace), "--memory-home", str(workspace / ".agent-memory-benchmark"),
                "--query", "<task-description-or-agent-extracted-term>",
                "--compact", "--json",
            ],
        },
        "response_schema": {},
    }


def fake_selective_codex() -> str:
    return r'''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
assert args[args.index("--sandbox") + 1] == "workspace-write"
prompt = sys.stdin.read()
assert "No Agent Memory context is preloaded" in prompt
assert "Agent Memory context payload" not in prompt
skill = Path(os.environ["HOME"]) / ".agents/skills/agent-memory-query/SKILL.md"
assert skill.is_file()
assert "## Benchmark Binding" in skill.read_text()
output = Path(args[args.index("--output-last-message") + 1])
result = {
    "schema_version": "agent-benchmark-response/v1",
    "case_id": "model-value",
    "variant": "model-value",
    "root_cause_category": "state",
    "predicted_files": ["src/Owner.ets"],
    "supporting_files": [],
    "investigated_files": ["src/Owner.ets"],
    "causal_level": "supported",
    "verification_status": "unknown",
    "query_rounds": 0,
    "source_search_count": 0,
    "expansion_trace": [],
    "stop_reason": "supported_cause_found",
    "evidence_basis": "direct_source_mechanism",
    "mechanism_evidence_files": ["src/Owner.ets"],
    "mechanism_evidence": [],
    "token_estimate": 0,
    "elapsed_ms": 0,
    "summary": "The owner returns the wrong state."
}
output.write_text(json.dumps(result))
context = json.dumps({
    "query_handoff": {"code_anchors": [{"file_path": "src/Owner.ets", "role": "primary"}]}
})
print(json.dumps({
    "type": "item.completed",
    "item": {
        "id": "memory-1",
        "type": "command_execution",
        "command": "python3 /runtime/agent_memory.py context --query 'focused cause' --compact --json",
        "aggregated_output": context,
        "exit_code": 0
    }
}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 20}}))
'''


def fake_selective_baseline_codex() -> str:
    return fake_selective_codex().replace(
        'assert skill.is_file()\nassert "## Benchmark Binding" in skill.read_text()',
        'assert not skill.exists()',
    ).replace(
        'print(json.dumps({\n    "type": "item.completed",\n    "item": {\n        "id": "memory-1",\n        "type": "command_execution",\n        "command": "python3 /runtime/agent_memory.py context --query \'focused cause\' --compact --json",\n        "aggregated_output": context,\n        "exit_code": 0\n    }\n}))\n',
        '',
    )


if __name__ == "__main__":
    unittest.main()
