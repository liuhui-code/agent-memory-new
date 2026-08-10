# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_definition_identity import (
    explicit_definition_identity,
    explicit_owner_identity_match,
)
from tools.agent_memory_runtime.query_localization_file_candidates import (
    select_file_candidates,
)


class QueryDefinitionIdentityTests(unittest.TestCase):
    def test_type_declaration_is_distinct_from_callable_reference(self) -> None:
        declaration = item("src/ZRules.ets", "class", ["exact_symbol"], 2.0)
        reference = item("src/APage.ets", "method", ["exact_symbol"], 20.0)

        self.assertTrue(explicit_definition_identity(declaration))
        self.assertFalse(explicit_definition_identity(reference))

    def test_owner_identity_requires_a_whole_query_token(self) -> None:
        self.assertTrue(explicit_owner_identity_match(
            "Inspect FullPlayerPagerSpec paneCount", "FullPlayerPagerSpec",
        ))
        self.assertFalse(explicit_owner_identity_match(
            "Inspect FullPlayerPagerSpecification", "FullPlayerPagerSpec",
        ))

    def test_owner_identity_rejects_a_file_path_token_fragment(self) -> None:
        self.assertFalse(explicit_owner_identity_match(
            "resource-provider getArktsDiagnostics", "Resource",
        ))

    def test_owner_identity_rejects_a_generic_business_word(self) -> None:
        self.assertFalse(explicit_owner_identity_match(
            "Invalid resource scope", "Resource",
        ))

    def test_definition_lane_bypasses_dense_directory_limit(self) -> None:
        values = [
            item("src/layout/APage.ets", "method", ["exact_symbol"], 30.0),
            item("src/layout/BPanel.ets", "method", ["exact_symbol"], 29.0),
            item("src/layout/CHost.ets", "method", ["exact_symbol"], 28.0),
            item("src/layout/ZRules.ets", "class", ["exact_symbol"], 5.0),
        ]

        selected = select_file_candidates(
            values, 3, "Inspect FullPlayerPagerSpec paneCount",
        )

        self.assertIn("src/layout/ZRules.ets", [value["file_path"] for value in selected])


def item(
    path: str, symbol_type: str, reasons: list[str], score: float,
) -> dict[str, object]:
    return {
        "id": int(score * 10),
        "kind": "symbol",
        "file_path": path,
        "symbol_type": symbol_type,
        "score": score,
        "match_reasons": reasons,
        "recall_lanes": ["fts"],
    }
