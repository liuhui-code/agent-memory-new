# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.semantic_callable_profile import (
    matching_owner_kind,
    matching_target_owner_kind,
    owner_kind,
    requested_owner_kinds,
)


class SemanticCallableProfileTests(unittest.TestCase):
    def test_boundary_and_policy_are_first_class_owner_kinds(self) -> None:
        self.assertEqual(
            "boundary",
            owner_kind("NativeResultBoundary", "class", "src/adapters/NativeResultBoundary.ets"),
        )
        self.assertEqual(
            "policy",
            owner_kind("DeferredSizePolicy", "class", "src/measurement/DeferredSizePolicy.ets"),
        )

    def test_owner_kind_matches_english_and_chinese_role_requests(self) -> None:
        self.assertTrue(matching_owner_kind("locate the adapter boundary", "boundary"))
        self.assertTrue(matching_owner_kind("定位尺寸策略", "policy"))
        self.assertFalse(matching_owner_kind("locate retry service", "policy"))

    def test_target_clause_role_overrides_problem_context_role(self) -> None:
        query = (
            "The transport service opens too early. "
            "Return the coordinator that validates the activation grant."
        )

        self.assertEqual({"coordinator"}, requested_owner_kinds(query))
        self.assertTrue(matching_owner_kind(query, "coordinator"))
        self.assertFalse(matching_owner_kind(query, "service"))
        self.assertEqual(
            {"component"},
            requested_owner_kinds("请定位清洗正文的 view，不要返回 record。"),
        )
        self.assertEqual(
            {"component"},
            requested_owner_kinds("Return the reusable list Builder, not a card model."),
        )

    def test_coordinator_is_a_first_class_owner_kind(self) -> None:
        self.assertEqual(
            "coordinator",
            owner_kind(
                "TransportActivationCoordinator",
                "class",
                "src/runtime/TransportActivationCoordinator.ets",
            ),
        )

    def test_only_a_singular_target_role_can_override_context_projection(self) -> None:
        self.assertTrue(matching_target_owner_kind(
            "Return the coordinator that validates activation.", "coordinator",
        ))
        self.assertFalse(matching_target_owner_kind(
            "Locate the component flow from list to row.", "component",
        ))
        self.assertFalse(matching_target_owner_kind(
            "Locate repository selection and the synchronization trigger.", "repository",
        ))
        self.assertFalse(matching_target_owner_kind(
            "请返回两个组件源码。", "component",
        ))
        self.assertTrue(matching_owner_kind(
            "The repository fallback remains active.", "repository",
        ))


if __name__ == "__main__":
    unittest.main()
