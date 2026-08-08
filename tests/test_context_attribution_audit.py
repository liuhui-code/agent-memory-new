from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.context_attribution_audit import (
    build_context_attribution_audit,
)


class ContextAttributionAuditTests(unittest.TestCase):
    def test_classifies_layers_without_authorizing_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack_a = write_json(root / "a-pack.json", case_pack("case-a", "https://example/a", "a"))
            pack_b = write_json(root / "b-pack.json", case_pack("case-b", "https://example/b", "b"))
            result_a = write_json(root / "a-result.json", context_result("case-a", "fail", False, False))
            result_b = write_json(root / "b-result.json", context_result("case-b", "fail", True, False))

            audit = build_context_attribution_audit([result_a, result_b], [pack_a, pack_b])

        self.assertEqual(["candidate_recall", "localizer_projection"], [
            item["observed_layer"] for item in audit["cases"]
        ])
        self.assertFalse(audit["policy"]["serving_change_authorized"])
        self.assertFalse(audit["policy"]["architecture_change_authorized"])
        self.assertTrue(all(not item["repair_contract_authorized"]
                            for item in audit["cross_case"]["boundary_hypotheses"]))

    def test_marks_primary_funnel_signal_non_gating_when_context_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = write_json(root / "pack.json", case_pack("case-a", "https://example/a", "a"))
            result = write_json(root / "result.json", context_result("case-a", "pass", True, True))

            audit = build_context_attribution_audit([result], [pack])

        self.assertEqual("non_gating_evidence_observation", audit["cases"][0]["observed_layer"])
        self.assertEqual("funnel_primary_is_not_a_context_gate", audit["cases"][0]["reason_codes"][0])

    def test_agent_result_is_unbound_without_context_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = write_json(root / "pack.json", case_pack("case-a", "https://example/a", "a"))
            result = write_json(root / "result.json", context_result("case-a", "fail", False, False))
            agent = write_json(root / "agent.json", {
                "schema_version": "agent-benchmark-result/v1",
                "cases": [{"case_id": "case-a", "trial_non_regression_rate": 0.5,
                           "variants": {"memory": {"memory_context_bytes": 42,
                                                       "memory_anchor_hit_count": 1}}}],
            })

            audit = build_context_attribution_audit([result], [pack], agent)

        utilization = audit["cases"][0]["agent_utilization"]
        self.assertEqual("unresolved_unbound", utilization["status"])
        self.assertTrue(utilization["memory_context_present"])

    def test_incomplete_oracle_review_does_not_enter_retrieval_hypotheses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = case_pack("case-a", "https://example/a", "a")
            pack["cases"][0]["review"] = {"source_diff_reviewed": True}
            pack_path = write_json(root / "pack.json", pack)
            result = write_json(root / "result.json", context_result("case-a", "fail", False, False))

            audit = build_context_attribution_audit([result], [pack_path])

        self.assertEqual("oracle_evidence_insufficient", audit["cases"][0]["observed_layer"])
        self.assertEqual([], audit["cross_case"]["boundary_hypotheses"])

    def test_rejects_result_case_without_case_pack_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = write_json(root / "pack.json", case_pack("case-a", "https://example/a", "a"))
            result = write_json(root / "result.json", context_result("case-b", "fail", False, False))

            with self.assertRaisesRegex(SystemExit, "no supplied case-pack provenance"):
                build_context_attribution_audit([result], [pack])


def case_pack(case_id: str, repository: str, family: str) -> dict:
    return {
        "source_repository": repository,
        "cases": [{
            "id": case_id,
            "source": {"before_revision": "a" * 40},
            "provenance": {"source_family": family},
            "review": {"source_diff_reviewed": True, "symptom_source_reviewed": True},
        }],
    }


def context_result(case_id: str, status: str, candidate: bool, localizer: bool) -> dict:
    return {
        "schema_version": "agent-context-capability-result/v1",
        "cases": [{
            "case_id": case_id,
            "scenario_id": case_id,
            "status": status,
            "checks": {"expected_anchors_recalled": candidate and localizer},
            "missing_expected_anchors": [] if candidate and localizer else ["src/Missing.ets"],
            "evidence_funnel": {"first_loss": "evidence_primary",
                                "stages": {"candidate_file": candidate,
                                           "localizer_file": localizer,
                                           "compact_primary": localizer,
                                           "compact_anchor": localizer,
                                           "evidence_primary": False}},
        }],
    }


def write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
