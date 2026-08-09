# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.prospective_cohort_contract import (
    validate_enrollment,
    validate_protocol,
)


class ProspectiveCohortContractTests(unittest.TestCase):
    def test_protocol_freezes_consecutive_fixed_stop_and_privacy(self) -> None:
        value = validate_protocol(protocol())

        self.assertEqual("prospective-agent-cohort/v1", value["schema_version"])
        self.assertEqual("consecutive", value["enrollment"]["mode"])
        self.assertEqual(2, value["target_presented_tasks"])
        self.assertFalse(value["stop_rule"]["optional_stopping"])
        self.assertTrue(all(not flag for flag in value["data_policy"].values()))

    def test_protocol_rejects_optional_stopping(self) -> None:
        value = protocol()
        value["stop_rule"]["optional_stopping"] = True

        with self.assertRaisesRegex(SystemExit, "optional stopping"):
            validate_protocol(value)

    def test_protocol_requires_declared_evidence_origin(self) -> None:
        value = protocol()
        value.pop("evidence_origin")

        with self.assertRaisesRegex(SystemExit, "evidence_origin"):
            validate_protocol(value)

    def test_protocol_rejects_raw_data_persistence(self) -> None:
        value = protocol()
        value["data_policy"]["persist_raw_query"] = True

        with self.assertRaisesRegex(SystemExit, "raw cohort data"):
            validate_protocol(value)

    def test_protocol_freezes_bounded_paired_replay_selection(self) -> None:
        value = protocol()
        value["paired_replay"] = {
            "mode": "first_eligible", "max_candidates": 1,
            "max_snapshot_bytes": 2_000_000, "retention_days": 14,
        }
        normalized = validate_protocol(value)
        self.assertEqual("first_eligible", normalized["paired_replay"]["mode"])
        value["paired_replay"]["max_candidates"] = 0
        with self.assertRaisesRegex(SystemExit, "max_candidates"):
            validate_protocol(value)

    def test_excluded_task_requires_preregistered_reason(self) -> None:
        with self.assertRaisesRegex(SystemExit, "preregistered exclusion"):
            validate_enrollment(
                protocol(), "excluded", "unknown", [], "new_reason"
            )

    def test_memory_opportunity_requires_typed_evidence(self) -> None:
        with self.assertRaisesRegex(SystemExit, "evidence reference"):
            validate_enrollment(protocol(), "eligible", "present", [], None)
        value = validate_enrollment(
            protocol(), "eligible", "present", ["semantic:3"], None
        )
        self.assertEqual([{"record_type": "semantic", "record_id": 3}], value["evidence_refs"])

    def test_absent_opportunity_rejects_evidence(self) -> None:
        with self.assertRaisesRegex(SystemExit, "cannot include evidence"):
            validate_enrollment(
                protocol(), "eligible", "absent", ["reflection:1"], None
            )


def protocol(evidence_origin: str = "generated_protocol_calibration") -> dict:
    return {
        "schema_version": "prospective-agent-cohort/v1",
        "cohort_id": "cohort-v1",
        "title": "Consecutive diagnosis tasks",
        "evidence_origin": evidence_origin,
        "task_type": "diagnosis",
        "target_presented_tasks": 2,
        "enrollment": {
            "mode": "consecutive",
            "source_scope": "one-real-project",
            "allowed_exclusion_reasons": ["not_diagnosis", "duplicate_task"],
        },
        "hypothesis": {
            "primary": "Selective Query Skill improves verified outcomes.",
            "treatment_mode": "selective-query-skill",
        },
        "metrics": {
            "overall": ["verified_task_success"],
            "diagnostic": ["activation", "anchor_utilization"],
            "guardrails": ["token_cost", "latency", "query_errors"],
        },
        "stop_rule": {
            "type": "fixed_presented_count",
            "optional_stopping": False,
        },
        "data_policy": {
            "persist_raw_task": False,
            "persist_raw_query": False,
            "persist_raw_logs": False,
            "persist_reasoning": False,
        },
    }


if __name__ == "__main__":
    unittest.main()
