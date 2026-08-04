# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors
from tools.agent_memory_runtime.query_callable_passage_portfolio import (
    build_callable_passage_portfolio,
)


class CallablePassagePortfolioTests(unittest.TestCase):
    def test_composes_query_supported_ranges_within_primary_owner(self) -> None:
        localization = fixture_localization([
            candidate("startPreview", 5, 13, ["exact_symbol", "semantic_mechanism"]),
            candidate("stopPreview", 19, 23, ["exact_symbol"]),
            candidate("unrelated", 25, 28, []),
        ])
        primary = evidence_primary("startPreview", 5, 13)

        result = build_callable_passage_portfolio(
            "Inspect both startPreview and stopPreview.",
            localization,
            {"primary": primary},
        )

        self.assertEqual("composed", result["state"])
        self.assertEqual(["startPreview", "stopPreview"], [
            item["symbol"] for item in result["members"]
        ])
        self.assertFalse(result["candidate_recall_changed"])

    def test_does_not_compose_different_owner_or_unsupported_range(self) -> None:
        values = [
            candidate("commit", 5, 12, ["semantic_mechanism"]),
            {**candidate("rollback", 14, 16, ["exact_symbol"]), "owner_name": "Other"},
        ]
        result = build_callable_passage_portfolio(
            "Inspect commit and rollback.",
            fixture_localization(values),
            {"primary": evidence_primary("commit", 5, 12)},
        )

        self.assertEqual("inactive", result["state"])

    def test_does_not_compose_from_semantic_mechanisms_without_explicit_methods(self) -> None:
        values = [
            candidate("start", 5, 12, ["semantic_mechanism"]),
            candidate("stop", 14, 16, ["semantic_mechanism"]),
        ]
        result = build_callable_passage_portfolio(
            "A lifecycle operation races with resource cleanup.",
            fixture_localization(values),
            {"primary": evidence_primary("start", 5, 12)},
        )

        self.assertEqual("inactive", result["state"])

    def test_composes_multi_target_structural_ranges_within_one_owner(self) -> None:
        support = ["salient_query_evidence", "multi_term_method_evidence"]
        values = [
            candidate("startWithDeadline", 5, 14, support),
            candidate("initializeWorkspace", 16, 26, support),
        ]

        result = build_callable_passage_portfolio(
            "Return the timeout race and cancelled checks.",
            fixture_localization(values),
            {"primary": evidence_primary("startWithDeadline", 5, 14)},
        )

        self.assertEqual("composed", result["state"])
        self.assertIn("structural_query_support", result["selection_basis"])

    def test_explicit_multi_target_composes_supported_cross_file_ranges(self) -> None:
        first = candidate("preservePending", 5, 10, ["semantic_mechanism"])
        second = {
            **candidate("activatePending", 6, 12, ["semantic_mechanism"]),
            "file_path": "src/Activation.ets",
            "owner_name": "Activation",
        }

        result = build_callable_passage_portfolio(
            "Trace both owners that preserve and activate the pending signal.",
            fixture_localization([first, second]),
            {"primary": evidence_primary("preservePending", 5, 10)},
        )

        self.assertEqual("composed", result["state"])
        self.assertEqual(
            ["src/Owner.ets", "src/Activation.ets"],
            [item["file_path"] for item in result["members"]],
        )
        self.assertIn("explicit_cross_file_targets", result["selection_basis"])

    def test_conjoined_criteria_do_not_authorize_cross_file_projection(self) -> None:
        first = candidate("orderDeadline", 5, 10, ["semantic_mechanism"])
        second = {
            **candidate("recordSequence", 6, 12, ["semantic_mechanism"]),
            "file_path": "src/Metrics.ets",
            "owner_name": "Metrics",
        }

        result = build_callable_passage_portfolio(
            "Locate logic that orders deadline and then insertion sequence.",
            fixture_localization([first, second]),
            {"primary": evidence_primary("orderDeadline", 5, 10)},
        )

        self.assertEqual("inactive", result["state"])

    def test_focus_projects_portfolio_as_same_file_anchor_ranges(self) -> None:
        evidence = {
            "certainty": "bounded",
            "primary": evidence_primary("commit", 5, 12),
            "passage_portfolio": {
                "state": "composed",
                "members": [
                    evidence_primary("commit", 5, 12),
                    evidence_primary("rollback", 14, 16),
                ],
            },
        }

        result = focus_callable_anchors([], evidence, False)

        self.assertEqual(["commit", "rollback"], [item["symbol"] for item in result])


def candidate(symbol: str, start: int, end: int, reasons: list[str]) -> dict[str, object]:
    return {
        "file_path": "src/Owner.ets",
        "symbol": symbol,
        "owner_name": "Owner",
        "start_line": start,
        "end_line": end,
        "reasons": reasons,
    }


def evidence_primary(symbol: str, start: int, end: int) -> dict[str, object]:
    return {
        "file_path": "src/Owner.ets",
        "symbol": symbol,
        "owner_name": "Owner",
        "source_range": {"start_line": start, "end_line": end},
    }


def fixture_localization(items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "callable_candidates": items,
        "source_ranges": [
            {
                "file_path": item["file_path"],
                "symbol": item["symbol"],
                "start_line": item["start_line"],
                "end_line": item["end_line"],
                "selection_reason": "callable_symbol_range",
            }
            for item in items
        ],
    }


if __name__ == "__main__":
    unittest.main()
