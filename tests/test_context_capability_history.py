# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.agent_memory_runtime.context_capability_governance import (
    context_capability_summary,
)


class ContextCapabilityHistoryTests(unittest.TestCase):
    def test_governance_summary_aggregates_latest_real_project_observations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            observations = [
                observation("/tmp/gramony", "gramony.json", "fail", 3, 1, None),
                observation("/tmp/gramony", "gramony.json", "pass", 3, 3, None),
                observation("/tmp/jingmo", "jingmo.json", "fail", 10, 1, "verified"),
                observation(
                    "/repo/docs/eval/fixtures/system-capability",
                    "system-capability-cases.json",
                    "pass",
                    45,
                    45,
                    "unsealed",
                ),
            ]
            (runtime / "context_capability_history.jsonl").write_text(
                "".join(json.dumps(item) + "\n" for item in observations),
                encoding="utf-8",
            )
            (runtime / "last_context_capability.json").write_text(
                json.dumps(observations[-1]), encoding="utf-8"
            )

            summary = context_capability_summary(SimpleNamespace(runtime_dir=runtime))

        cross_project = summary["cross_project_history"]
        self.assertEqual("available", cross_project["status"])
        self.assertEqual(2, cross_project["source_project_count"])
        self.assertEqual(2, cross_project["observation_count"])
        self.assertEqual(13, cross_project["case_observation_count"])
        self.assertEqual(1, cross_project["sealed_observation_count"])
        self.assertEqual(1, cross_project["gate_pass_count"])
        self.assertEqual(1, cross_project["gate_fail_count"])


def observation(
    source_project: str,
    case_file: str,
    gate: str,
    case_count: int,
    passed_count: int,
    seal_status: str | None,
) -> dict:
    return {
        "source_project": source_project,
        "case_file": case_file,
        "system_context_gate": gate,
        "summary": {
            "case_count": case_count,
            "passed_case_count": passed_count,
            "failed_case_count": case_count - passed_count,
            "average_context_tokens": 500,
        },
        "capability_profile": {
            "code_locator": {"anchor_recall": passed_count / case_count},
        },
        "case_seal": {"status": seal_status} if seal_status else {},
    }


if __name__ == "__main__":
    unittest.main()
