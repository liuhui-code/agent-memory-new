# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.prospective_cohort_metrics import (
    build_cohort_report,
    sanitize_benchmark_result,
)


class ProspectiveCohortMetricsTests(unittest.TestCase):
    def test_single_case_v3_result_is_sanitized_and_preserves_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            value = benchmark_result()
            value["private_task"] = "SECRET_TASK_TEXT"
            path.write_text(json.dumps(value), encoding="utf-8")

            result = sanitize_benchmark_result(path, "case-1", paired_replay())

        self.assertEqual("pass", result["quality_gate"])
        self.assertEqual([1], result["query_counts"])
        self.assertEqual(0.2, result["outcome_delta"])
        self.assertNotIn("SECRET_TASK_TEXT", json.dumps(result))

    def test_result_must_be_selective_single_case_with_valid_measurement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            value = benchmark_result()
            value["selected_case_ids"] = ["case-1", "case-2"]
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "exactly the linked case"):
                sanitize_benchmark_result(path, "case-1", paired_replay())

            value = benchmark_result()
            value["measurement_contract"]["status"] = "fail"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "measurement contract"):
                sanitize_benchmark_result(path, "case-1", paired_replay())

    def test_task_source_and_memory_misbinding_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            for key in ("task_digest", "source_identity_digest", "memory_snapshot_digest"):
                value = benchmark_result()
                value["paired_replay_attestation"][key] = "f" * 64
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaisesRegex(SystemExit, "attestation does not match"):
                    sanitize_benchmark_result(path, "case-1", paired_replay())

    def test_legacy_v3_result_cannot_create_a_paired_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_text(json.dumps(benchmark_result()), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "no enrolled paired replay package"):
                sanitize_benchmark_result(path, "case-1", {"status": "not_selected"})

    def test_report_separates_outcome_diagnostics_and_guardrails(self) -> None:
        benchmark = sanitize_from_value(benchmark_result())
        cohort = {
            "cohort_id": "cohort-v1",
            "status": "completed",
            "protocol_digest": "a" * 64,
            "target_presented_tasks": 1,
            "protocol": verified_real_protocol(),
        }
        tasks = [{
            "sequence_no": 1,
            "eligibility": "eligible",
            "opportunity": "present",
            "status": "completed",
            "outcome": "pass",
            "verification": "test",
            "replay_eligible": True,
            "exclusion_reason": None,
            "usage_metrics": {"reported": True, "query_count": 1, "query_error_count": 0},
            "benchmark_metrics": benchmark,
        }]

        report = build_cohort_report(cohort, tasks, True)

        natural = report["segments"]["natural"]
        self.assertEqual("pass", report["data_quality"]["status"])
        self.assertEqual("prospective_development", report["evidence_level"])
        self.assertFalse(report["promotion_eligible"])
        self.assertEqual(1.0, natural["verified_success_rate"])
        self.assertEqual(0.2, natural["average_outcome_delta"])
        self.assertEqual(0.2, natural["average_token_overhead_ratio"])
        self.assertEqual(-1.0, natural["average_source_search_delta"])
        self.assertEqual({"none": 1}, natural["first_observable_losses"])

    def test_legacy_real_cohort_report_is_labeled_without_a_claim(self) -> None:
        cohort = {
            "cohort_id": "legacy-v1", "status": "registered", "protocol_digest": "a" * 64,
            "target_presented_tasks": 1,
            "protocol": {"evidence_origin": "prospective_real_tasks"},
        }

        report = build_cohort_report(cohort, [], True)

        self.assertEqual("unverified_campaign_input", report["campaign_input"]["status"])
        self.assertEqual("unverified_campaign_input", report["data_quality"]["status"])
        self.assertEqual("unverified_campaign_input", report["capability_claim"])
        self.assertEqual("not_permitted", report["interpretation"]["efficiency_claim"])
        self.assertFalse(report["promotion_eligible"])


def sanitize_from_value(value: dict) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "result.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        result = sanitize_benchmark_result(path, "case-1", paired_replay())
    return result


def benchmark_result() -> dict:
    value = {
        "schema_version": "agent-benchmark-result/v1",
        "treatment_mode": "selective-query-skill",
        "selected_case_ids": ["case-1"],
        "quality_gate": "pass",
        "efficiency_gate": "pass",
        "promotion_gate": "fail",
        "measurement_contract": {"status": "pass", "mode": "selective_query_skill"},
        "selective_query": {
            "cases": [{
                "case_id": "case-1",
                "activation_expectation": "required",
                "expectation_met": True,
                "memory_query_counts": [1],
                "first_observable_loss": None,
            }]
        },
        "cases": [{
            "case_id": "case-1",
            "context_outcome_delta": 0.2,
            "variants": {
                "baseline": {
                    "agent_outcome_score": 0.7,
                    "source_search_count": 2,
                    "source_read_count": 2,
                    "token_estimate": 100,
                    "elapsed_ms": 1000,
                    "memory_anchor_hit_count": 0,
                },
                "memory": {
                    "agent_outcome_score": 0.9,
                    "source_search_count": 1,
                    "source_read_count": 1,
                    "token_estimate": 120,
                    "elapsed_ms": 1100,
                    "memory_anchor_hit_count": 1,
                },
            },
        }],
    }
    value["paired_replay_attestation"] = {
        "package_digest": "a" * 64,
        "task_digest": "b" * 64,
        "source_identity_digest": "c" * 64,
        "memory_snapshot_digest": "d" * 64,
        "skill_contract_digest": "e" * 64,
        "runner_digest": "f" * 64,
        "environment_digest": "1" * 64,
        "case_pack_digest": "2" * 64,
    }
    return value


def paired_replay() -> dict:
    return {
        "status": "ready", "package_digest": "a" * 64, "task_digest": "b" * 64,
        "source_identity_digest": "c" * 64, "memory_snapshot_digest": "d" * 64,
    }


def verified_real_protocol() -> dict:
    return {
        "evidence_origin": "prospective_real_tasks",
        "campaign_input": {
            "schema_version": "campaign-input-binding/v1",
            "status": "verified",
            "manifest_digest": "a" * 64,
            "campaign_id_digest": "b" * 64,
        },
    }


if __name__ == "__main__":
    unittest.main()
