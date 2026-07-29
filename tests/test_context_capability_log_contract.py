# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.context_capability_eval import evaluate_context_capability


class ContextCapabilityLogContractTests(unittest.TestCase):
    def test_log_template_gate_excludes_runtime_only_observation_terms(self) -> None:
        case = {
            "id": "log-contract-case",
            "task_type": "diagnosis",
            "task": {"description": "Observed dynamic restore failure."},
            "oracle": {
                "expected_files": [],
                "forbidden_files": [],
                "context_requirements": {
                    "require_expected_anchors": False,
                    "required_log_template_literals": [
                        "RESTORE_EVENT_71A9 rejected snapshot"
                    ],
                    "runtime_observed_terms": [
                        "snapshot-44", "KV store not initialized"
                    ],
                },
            },
        }
        observation = {
            "schema_version": "agent-context-capability-observation/v1",
            "case_id": "log-contract-case",
            "context_schema_version": "agent-context-compact/v1",
            "anchor_paths": [],
            "ordered_anchor_paths": [],
            "primary_anchor_paths": [],
            "candidate_anchor_paths": [],
            "excerpt_paths": [],
            "excerpt_spans": [],
            "log_anchor_paths": ["src/RestoreCoordinator.ets"],
            "log_anchor_count": 1,
            "log_evidence_texts": [
                "RestoreCoordinator RESTORE_EVENT_71A9 rejected snapshot ${snapshotId}"
            ],
            "path_files": [],
            "path_relations": [],
            "evidence_gaps": [],
            "context_token_estimate": 320,
        }

        result = evaluate_context_capability([case], [observation])

        scored = result["cases"][0]
        self.assertEqual("pass", scored["status"])
        self.assertTrue(scored["checks"]["required_log_template_literals_recalled"])
        self.assertEqual(
            ["snapshot-44", "kv store not initialized"],
            scored["runtime_observed_terms"],
        )
        self.assertNotIn("runtime_observed_terms_recalled", scored["checks"])


if __name__ == "__main__":
    unittest.main()
