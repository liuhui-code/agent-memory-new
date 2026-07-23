# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.agent_benchmark_cases import load_case_pack
from tools.agent_memory_runtime.benchmark_case_seal import (
    case_pack_seal_audit,
    seal_case_pack,
)


def reviewed_pack() -> dict:
    return {
        "schema_version": "agent-benchmark-cases/v1",
        "suite": "holdout",
        "project_path": "/path/to/project",
        "source_repository": "https://example.test/project",
        "cases": [
            {
                "id": "real-case",
                "task_type": "diagnosis",
                "review_status": "holdout",
                "task": {"description": "Locate the incorrect route owner."},
                "source": {
                    "before_revision": "a" * 40,
                    "after_revision": "b" * 40,
                    "changed_files": ["entry/src/main/ets/pages/Index.ets"],
                    "test_files": [],
                },
                "provenance": {
                    "kind": "git_history_source_reviewed",
                    "fix_commit": "b" * 40,
                    "commit_message": "fix route owner",
                },
                "oracle": {
                    "expected_files": ["entry/src/main/ets/pages/Index.ets"],
                    "forbidden_files": [],
                    "root_cause_category": "route",
                },
                "review": {"source_diff_reviewed": True},
                "leakage_guard": {
                    "hidden_fields": [
                        "oracle",
                        "source.after_revision",
                        "provenance.commit_message",
                    ]
                },
            }
        ],
    }


class BenchmarkCaseSealTests(unittest.TestCase):
    def test_seal_is_verified_when_pack_loads(self) -> None:
        sealed = seal_case_pack(reviewed_pack(), "2026-07-18T00:00:00Z")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(sealed), encoding="utf-8")
            loaded = load_case_pack(path)
        audit = case_pack_seal_audit(loaded)
        self.assertEqual("verified", audit["status"])
        self.assertEqual(1, audit["case_count"])

    def test_modified_sealed_pack_is_rejected(self) -> None:
        sealed = seal_case_pack(reviewed_pack(), "2026-07-18T00:00:00Z")
        sealed["cases"][0]["task"]["description"] = "Changed after sealing"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(sealed), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "digest mismatch"):
                load_case_pack(path)

    def test_sealing_requires_review_and_leakage_guards(self) -> None:
        pack = reviewed_pack()
        pack["cases"][0]["review"]["source_diff_reviewed"] = False
        with self.assertRaisesRegex(SystemExit, "source diff review"):
            seal_case_pack(pack, "2026-07-18T00:00:00Z")

        pack = reviewed_pack()
        pack["cases"][0]["leakage_guard"]["hidden_fields"].remove("oracle")
        with self.assertRaisesRegex(SystemExit, "hidden field"):
            seal_case_pack(pack, "2026-07-18T00:00:00Z")

    def test_required_seal_cannot_be_removed(self) -> None:
        pack = reviewed_pack()
        pack["governance"] = {"require_seal": True}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(pack), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "requires a seal"):
                load_case_pack(path)


if __name__ == "__main__":
    unittest.main()
