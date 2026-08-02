# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.agent_benchmark_longitudinal import (
    evaluate_longitudinal_value,
    validate_longitudinal_cases,
)
from tools.agent_memory_runtime.agent_benchmark_protocol import run_benchmark_agent
from tools.agent_memory_runtime.benchmark_context_setup import context_setup_audit


class AgentBenchmarkLongitudinalTests(unittest.TestCase):
    def test_group_requires_all_stages_with_same_task_source_and_oracle(self) -> None:
        cases = longitudinal_cases()
        groups = validate_longitudinal_cases(cases)

        self.assertEqual(
            ["agent_memory", "ideal_memory", "structural_context"],
            sorted(groups["incident-a"]),
        )
        with self.assertRaisesRegex(SystemExit, "missing stages"):
            validate_longitudinal_cases(cases[:2])
        cases[2]["task"] = {"description": "different task"}
        with self.assertRaisesRegex(SystemExit, "must share task"):
            validate_longitudinal_cases(cases)

    def test_value_report_attributes_agent_history_interference(self) -> None:
        cases = longitudinal_cases()
        deltas = {
            "structural_context": 0.2,
            "agent_memory": 0.1,
            "ideal_memory": 0.3,
        }
        result_cases = []
        observations = []
        for case in cases:
            stage = case["longitudinal"]["stage"]
            result_cases.append({
                "case_id": case["id"],
                "context_outcome_delta": deltas[stage],
                "variants": {
                    "baseline": {"agent_outcome_score": 0.5},
                    "memory": {
                        "agent_outcome_score": 0.5 + deltas[stage],
                        "memory_anchor_hit_count": 1,
                        "memory_context_token_estimate": 400,
                    },
                },
            })
            observations.append({
                "case_id": case["id"],
                "variant": "memory",
                "trial_index": 1,
                "memory_setup": context_setup_audit(case.get("context_setup")),
            })

        report = evaluate_longitudinal_value(
            cases,
            observations,
            {"cases": result_cases},
        )

        self.assertIsNotNone(report)
        group = report["groups"][0]
        self.assertEqual(
            "agent_memory_interference",
            group["observed_first_value_loss"]["layer"],
        )
        self.assertEqual(-0.1, group["comparisons"]["agent_memory_increment_over_structural"])
        self.assertTrue(group["stages"]["agent_memory"]["setup_verified"])

    def test_runner_receives_injected_history_without_payload_disclosure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            source = project / "src" / "Profile.ets"
            source.parent.mkdir()
            source.write_text("export function loadProfile(): void {}\n", encoding="utf-8")
            runner = root / "runner"
            runner.write_text(runner_script(), encoding="utf-8")
            runner.chmod(0o755)
            case = base_case("agent")
            case["context_setup"] = reflection_setup("profile load failure")

            observation = run_benchmark_agent(
                project,
                case,
                "memory",
                str(runner),
                60,
            )

        self.assertEqual(1, observation["memory_setup"]["reflection_count"])
        self.assertEqual(
            context_setup_audit(case["context_setup"]),
            observation["memory_setup"],
        )


def longitudinal_cases() -> list[dict]:
    cases = []
    for stage, setup in (
        ("structural_context", None),
        ("agent_memory", reflection_setup("agent prior task")),
        ("ideal_memory", reflection_setup("reviewed prior task")),
    ):
        case = base_case(stage)
        case["longitudinal"] = {
            "schema_version": "agent-memory-longitudinal-stage/v1",
            "group_id": "incident-a",
            "stage": stage,
            "history_cutoff": "revision-a",
            "setup_origin": stage,
            "ideal_pre_target_frozen": True,
        }
        if setup is not None:
            case["context_setup"] = setup
        cases.append(case)
    return cases


def base_case(case_id: str) -> dict:
    return {
        "id": case_id,
        "task_type": "diagnosis",
        "review_status": "validated",
        "task": {"description": "Profile load fails after session refresh."},
        "source": {"before_revision": "working-tree"},
        "oracle": {
            "expected_files": ["src/Profile.ets"],
            "forbidden_files": [],
            "root_cause_category": "state",
            "expected_causal_level": "supported",
        },
    }


def reflection_setup(task: str) -> dict:
    return {
        "reflections": [{
            "experience_type": "procedure_experience",
            "task": task,
            "summary": "Inspect the session state before retrying.",
            "lesson": "Use one bounded refresh and verify the resulting session.",
            "trigger_condition": "profile load fails after session refresh",
            "repair_action": "inspect status and verify one refresh",
            "anti_pattern": "retry every failure",
            "verification_method": "review current session contract",
            "source_cases": ["prior-task:session-refresh"],
            "confidence": 0.9,
        }]
    }


def runner_script() -> str:
    return """#!/usr/bin/env python3
import json
import subprocess
import sys

request = json.load(sys.stdin)
assert "context_setup" not in request["case"]
memory = request["memory_access"]
process = subprocess.run([
    sys.executable, memory["runtime"], "list",
    "--project", memory["project"],
    "--memory-home", memory["memory_home"],
    "--type", "reflection", "--json",
], text=True, capture_output=True, check=True)
records = json.loads(process.stdout)
assert len(records) == 1
result = {
    "schema_version": "agent-benchmark-response/v1",
    "case_id": request["case_id"],
    "variant": request["variant"],
    "trial_index": request.get("trial_index", 1),
    "root_cause_category": "state",
    "predicted_files": ["src/Profile.ets"],
    "investigated_files": ["src/Profile.ets"],
    "causal_level": "supported",
    "verification_status": "unknown",
    "summary": "bounded result",
}
json.dump(result, sys.stdout)
"""


if __name__ == "__main__":
    unittest.main()
