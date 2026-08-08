# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class SelectiveQueryBenchmarkCliTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "project"
        (self.project / "src").mkdir(parents=True)
        (self.project / "src" / "RequestOwner.ets").write_text(
            "export function completeRequest(): boolean { return false }\n",
            encoding="utf-8",
        )
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_public_facade_runs_agent_selected_query_treatment(self) -> None:
        cases = Path(self.temp_dir.name) / "cases.json"
        responses = Path(self.temp_dir.name) / "responses.json"
        runner = Path(self.temp_dir.name) / "selective-runner"
        cases.write_text(json.dumps(case_pack(self.project), indent=2) + "\n")
        runner.write_text(selective_runner_script(), encoding="utf-8")
        runner.chmod(0o755)

        process = self.run_memory(
            self.project,
            "eval-agent-benchmark",
            "--cases", str(cases),
            "--runner", str(runner),
            "--treatment-mode", "selective-query-skill",
            "--output-responses", str(responses),
            "--json",
        )

        result = json.loads(process.stdout)
        observations = json.loads(responses.read_text())["observations"]
        self.assertEqual("selective-query-skill", result["treatment_mode"])
        self.assertEqual("pass", result["selective_query"]["status"])
        self.assertEqual("pass", result["quality_gate"])
        self.assertEqual(["baseline", "memory"], [item["variant"] for item in observations])
        self.assertEqual([0, 1], [item["memory_query_count"] for item in observations])


def case_pack(project: Path) -> dict:
    return {
        "schema_version": "agent-benchmark-cases/v1",
        "suite": "development",
        "project_path": str(project),
        "cases": [{
            "id": "selective-required",
            "task_type": "diagnosis",
            "review_status": "validated",
            "evaluation_role": "protocol_calibration",
            "task": {"description": "A background request never completes."},
            "source": {"before_revision": "working-tree"},
            "provenance": {"kind": "generated_protocol_fixture"},
            "oracle": {
                "expected_files": ["src/RequestOwner.ets"],
                "forbidden_files": [],
                "root_cause_category": "state",
                "expected_causal_level": "supported",
                "query_skill_expectation": {
                    "activation": "required",
                    "max_queries": 2,
                },
            },
        }],
    }


def selective_runner_script() -> str:
    return r'''#!/usr/bin/env python3
import json
import subprocess
import sys

request = json.load(sys.stdin)
assert request["treatment_mode"] == "selective-query-skill"
memory = request["variant"] == "memory"
if memory:
    access = request["memory_access"]
    assert access["isolated"] is True
    assert access["memory_home"].endswith("/.agent-memory-benchmark")
    command = [
        "request timeout" if item in {
            "<task-description>", "<task-description-or-agent-extracted-term>"
        } else item
        for item in access["query_command"]
    ]
    queried = subprocess.run(
        command, cwd=request["workspace"], text=True,
        capture_output=True, check=True,
    )
    context = json.loads(queried.stdout)
    assert "query_handoff" in context
query_count = 1 if memory else 0
metadata = {
    "schema_version": "agent-benchmark-treatment/v3",
    "variant": request["variant"],
    "context_present": False,
    "preloaded_context": False,
    "memory_delivery": "agent_selected_query_skill",
    "query_skill_available": memory,
    "query_skill_digest": "a" * 64 if memory else None,
    "query_limit": 3,
    "investigation_contract_digest": "shared-contract",
}
result = {
    "schema_version": "agent-benchmark-response/v1",
    "case_id": request["case_id"],
    "variant": request["variant"],
    "trial_index": request.get("trial_index", 1),
    "root_cause_category": "state",
    "predicted_files": ["src/RequestOwner.ets"],
    "supporting_files": [],
    "investigated_files": ["src/RequestOwner.ets"],
    "causal_level": "supported",
    "verification_status": "unknown",
    "query_rounds": query_count,
    "source_search_count": 1,
    "token_estimate": 100,
    "elapsed_ms": 100,
    "latency_metrics_reported": True,
    "memory_context_bytes": 400 if memory else 0,
    "memory_context_token_estimate": 100 if memory else 0,
    "memory_query_count": query_count,
    "memory_query_success_count": query_count,
    "memory_query_error_count": 0,
    "memory_query_metrics_reported": True,
    "treatment_metadata": metadata,
    "summary": "The request owner keeps the incomplete state."
}
json.dump(result, sys.stdout)
'''
