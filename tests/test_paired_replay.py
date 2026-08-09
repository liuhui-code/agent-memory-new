# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3
import subprocess
import tempfile
import unittest
import json
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.paired_replay import (
    create_package,
    load_package,
    prepare_replay_memory,
    validate_case,
)
from tools.agent_memory_runtime.storage import connect, ensure_initialized, resolve_project
from tools.agent_memory_runtime.prospective_cohort_snapshot import source_snapshot


class PairedReplayTests(AgentMemoryTestBase):
    def test_snapshot_is_bounded_readonly_and_rebinds_task_start_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            workspace = Path(directory) / "workspace"
            root.mkdir()
            workspace.mkdir()
            project = resolve_project(str(root), str(self.memory_home(root)))
            ensure_initialized(project)
            with connect(project) as conn:
                conn.execute(
                    "INSERT INTO semantic_facts(project_id, fact, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (project.project_id, "task-start marker", "test", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
                )
                conn.commit()
                state = create_package(
                    project, conn, cohort(), task(), source(), "m" * 64, True,
                )
            self.assertEqual("ready", state["status"])
            manifest = next((project.runtime_dir / "paired-replay").glob("*/manifest.json"))
            package = load_package(manifest)
            snapshot = Path(package["snapshot_path"])
            self.assertFalse(snapshot.stat().st_mode & 0o200)

            access = prepare_replay_memory(
                workspace, workspace / ".agent-memory-benchmark", package, "diagnosis",
            )
            target = resolve_project(str(workspace), str(workspace / ".agent-memory-benchmark"))
            with sqlite3.connect(target.db_path) as conn:
                facts = conn.execute("SELECT fact FROM semantic_facts WHERE project_id = ?", (target.project_id,)).fetchall()
            self.assertEqual([("task-start marker",)], facts)
            self.assertTrue(access["readonly_source_snapshot"])

    def test_case_binding_rejects_task_and_source_mismatch(self) -> None:
        package = {
            "task_id": "case-1", "task_digest": "t" * 64,
            "source_revision": "r" * 40,
        }
        case = {
            "id": "case-1", "paired_replay_binding": {"task_digest": "t" * 64},
            "source": {"before_revision": "r" * 40},
        }
        validate_case(package, case)
        case["paired_replay_binding"]["task_digest"] = "x" * 64
        with self.assertRaisesRegex(SystemExit, "task digest"):
            validate_case(package, case)
        case["paired_replay_binding"]["task_digest"] = "t" * 64
        case["source"]["before_revision"] = "y" * 40
        with self.assertRaisesRegex(SystemExit, "source revision"):
            validate_case(package, case)

    def test_benchmark_attests_a_frozen_package_before_cohort_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            (root / "src").mkdir(parents=True)
            (root / "src" / "RequestOwner.ets").write_text("export const owner = true\n")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "initial"], cwd=root, check=True)
            revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
            project = resolve_project(str(root), str(self.memory_home(root)))
            ensure_initialized(project)
            with connect(project) as conn:
                state = create_package(project, conn, cohort(), task(), source_snapshot(root), "m" * 64, True)
            package_path = next((project.runtime_dir / "paired-replay").glob("*/manifest.json"))
            package = load_package(package_path)
            case_file = Path(directory) / "cases.json"
            case_file.write_text(json.dumps(case_pack(root, revision, state["task_digest"])), encoding="utf-8")
            runner = Path(directory) / "runner"
            runner.write_text(runner_script(), encoding="utf-8")
            runner.chmod(0o755)

            result = self.json_command(
                root, "eval-agent-benchmark", "--cases", str(case_file), "--runner", str(runner),
                "--paired-replay-package", str(package_path), "--treatment-mode", "selective-query-skill", "--json",
            )
            attestation = result["paired_replay_attestation"]
            self.assertEqual(package["package_digest"], attestation["package_digest"])
            self.assertEqual(package["memory_snapshot_digest"], attestation["memory_snapshot_digest"])
            self.assertEqual(64, len(attestation["runner_digest"]))

    def json_command(self, root: Path, *args: str) -> dict:
        return json.loads(self.run_memory(root, *args).stdout)


def cohort() -> dict:
    return {
        "cohort_id": "cohort-v1", "protocol_digest": "p" * 64,
        "protocol": {"paired_replay": {"mode": "first_eligible", "max_candidates": 1,
                                        "max_snapshot_bytes": 2_000_000, "retention_days": 7}},
    }


def task() -> dict:
    return {"sequence_no": 1, "task_id": "case-1", "task_digest": "t" * 64}


def source() -> dict:
    return {"replay_eligible": True, "identity_digest": "i" * 64,
            "revision": "r" * 40, "tree_digest": "g" * 40}


def case_pack(root: Path, revision: str, task_digest: str) -> dict:
    return {
        "schema_version": "agent-benchmark-cases/v1", "suite": "development", "project_path": str(root),
        "cases": [{
            "id": "case-1", "task_type": "diagnosis", "review_status": "validated",
            "task": {"description": "Request owner is stuck."},
            "source": {"before_revision": revision},
            "paired_replay_binding": {"task_digest": task_digest},
            "oracle": {"expected_files": ["src/RequestOwner.ets"], "forbidden_files": [],
                       "root_cause_category": "state", "expected_causal_level": "supported",
                       "query_skill_expectation": {"activation": "required", "max_queries": 2}},
        }],
    }


def runner_script() -> str:
    return r'''#!/usr/bin/env python3
import json
import subprocess
import sys

request = json.load(sys.stdin)
memory = request["variant"] == "memory"
if memory:
    assert request["memory_access"]["readonly_source_snapshot"] is True
    command = ["request owner" if item.startswith("<task") else item for item in request["memory_access"]["query_command"]]
    subprocess.run(command, cwd=request["workspace"], text=True, capture_output=True, check=True)
queries = 1 if memory else 0
result = {
  "schema_version": "agent-benchmark-response/v1", "case_id": request["case_id"],
  "variant": request["variant"], "trial_index": request.get("trial_index", 1),
  "root_cause_category": "state", "predicted_files": ["src/RequestOwner.ets"],
  "investigated_files": ["src/RequestOwner.ets"], "causal_level": "supported",
  "verification_status": "unknown", "query_rounds": queries, "source_search_count": 1,
  "token_estimate": 100, "elapsed_ms": 100, "latency_metrics_reported": True,
  "memory_context_bytes": 10 if memory else 0, "memory_context_token_estimate": 2 if memory else 0,
  "memory_query_count": queries, "memory_query_success_count": queries,
  "memory_query_error_count": 0, "memory_query_metrics_reported": True,
  "treatment_metadata": {"schema_version": "agent-benchmark-treatment/v3", "variant": request["variant"],
    "context_present": False, "preloaded_context": False, "memory_delivery": "agent_selected_query_skill",
    "query_skill_available": memory, "query_skill_digest": "a" * 64 if memory else None,
    "query_limit": 3, "investigation_contract_digest": "shared-contract"},
  "summary": "bounded result"
}
json.dump(result, sys.stdout)
'''


if __name__ == "__main__":
    unittest.main()
