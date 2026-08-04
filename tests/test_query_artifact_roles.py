# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_artifact_roles import (
    IMPLEMENTATION,
    NEUTRAL,
    PRODUCTION,
    TEST,
    VALIDATION,
    annotate_artifact_roles,
    artifact_family,
    artifact_role,
    artifact_role_rank_score,
    artifact_role_shadow_priority,
    artifact_role_tiebreak,
    query_artifact_intent,
)
from tools.agent_memory_runtime.query_callable_evidence import compact_candidate


class QueryArtifactRoleTests(unittest.TestCase):
    def test_classifies_test_conventions_without_language_coupling(self) -> None:
        self.assertEqual(TEST, artifact_role("tests/cache/LeasePolicy.ets"))
        self.assertEqual(TEST, artifact_role("src/cache/LeasePolicy.spec.ts"))
        self.assertEqual(TEST, artifact_role("src/cache/LeasePolicyTest.java"))
        self.assertEqual(PRODUCTION, artifact_role("src/cache/LeasePolicy.ets"))

    def test_normalizes_production_and_test_to_same_family(self) -> None:
        expected = artifact_family("src/cache/LeasePolicy.ets")

        self.assertEqual(expected, artifact_family("tests/cache/LeasePolicy.test.ets"))
        self.assertEqual(expected, artifact_family("src/cache/LeasePolicyTest.java"))

    def test_query_intent_keeps_mixed_requests_neutral(self) -> None:
        self.assertEqual(IMPLEMENTATION, query_artifact_intent("Inspect the policy method"))
        self.assertEqual(VALIDATION, query_artifact_intent("Find the regression test"))
        self.assertEqual(NEUTRAL, query_artifact_intent("Inspect source and regression test"))

    def test_implementation_intent_reranks_only_competing_family(self) -> None:
        values = annotate_artifact_roles([
            candidate("tests/cache/LeasePolicy.test.ets", 30.0),
            candidate("src/cache/LeasePolicy.ets", 20.0),
            candidate("tests/other/CacheHarness.test.ets", 40.0),
        ], "Locate the production policy implementation")
        ranked = sorted(values, key=lambda item: (
            artifact_role_shadow_priority(item),
            -artifact_role_rank_score(item), artifact_role_tiebreak(item),
            str(item["file_path"]),
        ))

        self.assertEqual("tests/other/CacheHarness.test.ets", ranked[0]["file_path"])
        self.assertEqual("src/cache/LeasePolicy.ets", ranked[1]["file_path"])
        self.assertTrue(ranked[1]["artifact_role_competition"])
        self.assertEqual(1, values[2]["artifact_role_affinity"])
        self.assertEqual(30.0, ranked[1]["artifact_family_rank_score"])

    def test_validation_intent_prefers_test_twin(self) -> None:
        values = annotate_artifact_roles([
            candidate("src/cache/LeasePolicy.ets", 30.0),
            candidate("tests/cache/LeasePolicy.test.ets", 20.0),
        ], "Find the LeasePolicy regression test")
        ranked = sorted(values, key=lambda item: (
            artifact_role_shadow_priority(item),
            -artifact_role_rank_score(item), artifact_role_tiebreak(item),
            str(item["file_path"]),
        ))

        self.assertEqual(TEST, ranked[0]["artifact_role"])

    def test_family_representative_does_not_globally_boost_every_production_member(self) -> None:
        values = annotate_artifact_roles([
            candidate("tests/cache/LeasePolicy.test.ets", 30.0),
            candidate("src/cache/LeasePolicy.ets", 20.0),
            candidate("src/cache/LeasePolicy.ets", 10.0),
            candidate("src/other/Coordinator.ets", 25.0),
        ], "Inspect the policy implementation")
        ranked = sorted(values, key=lambda item: (
            artifact_role_shadow_priority(item),
            -artifact_role_rank_score(item), artifact_role_tiebreak(item),
            str(item["file_path"]),
        ))

        self.assertEqual(
            ["src/cache/LeasePolicy.ets", "src/other/Coordinator.ets",
             "src/cache/LeasePolicy.ets", "tests/cache/LeasePolicy.test.ets"],
            [item["file_path"] for item in ranked],
        )
        self.assertEqual(1, sum(bool(item.get("artifact_role_representative")) for item in values))

    def test_agent_evidence_omits_role_metadata_without_competition(self) -> None:
        value = compact_candidate({
            "file_path": "src/cache/LeasePolicy.ets",
            "symbol": "renew",
            "artifact_role": "production",
            "artifact_query_intent": "implementation",
        }, {})

        self.assertNotIn("artifact_role", value)

    def test_agent_evidence_explains_competing_artifact_role(self) -> None:
        value = compact_candidate({
            "file_path": "src/cache/LeasePolicy.ets",
            "symbol": "renew",
            "artifact_role": "production",
            "artifact_query_intent": "implementation",
            "artifact_role_competition": True,
            "artifact_role_representative": True,
        }, {})

        self.assertEqual("production", value["artifact_role"])
        self.assertTrue(value["artifact_role_representative"])


def candidate(path: str, score: float) -> dict[str, object]:
    return {"file_path": path, "score": score, "localization_reasons": []}
