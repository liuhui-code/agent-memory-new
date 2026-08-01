# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_callable_evidence import callable_evidence


class CallableEvidenceTests(unittest.TestCase):
    def test_bounded_primary_keeps_diverse_alternatives(self) -> None:
        evidence = callable_evidence({
            "callable_candidates": [
                candidate("src/profile/ProfileViewModel.ets", "save", "viewmodel", 16.0),
                candidate("src/data/ProfileStore.ets", "save", "store", 12.0),
                candidate("src/profile/ProfileViewModel.ets", "load", "viewmodel", 11.0),
            ],
            "source_ranges": [{
                "file_path": "src/profile/ProfileViewModel.ets",
                "symbol": "save",
                "start_line": 20,
                "end_line": 31,
                "selection_reason": "callable_mechanism_window",
            }],
        })

        self.assertEqual("bounded", evidence["certainty"])
        self.assertEqual("save", evidence["primary"]["symbol"])
        self.assertEqual("store", evidence["alternatives"][0]["owner_kind"])
        self.assertEqual("retrieval_evidence_not_root_cause", evidence["boundary"])

    def test_missing_source_range_is_explicitly_uncertain(self) -> None:
        evidence = callable_evidence({
            "callable_candidates": [candidate("src/Task.ets", "run", "service", 14.0)],
            "source_ranges": [],
        })

        self.assertEqual("uncertain", evidence["certainty"])
        self.assertNotIn("source_range", evidence["primary"])

    def test_unique_structured_owner_match_is_bounded_without_score_gap(self) -> None:
        primary = candidate("src/policy/SizePolicy.ets", "resolve", "policy", 12.0)
        primary["reasons"] = ["structured_owner_kind"]
        evidence = callable_evidence({
            "callable_candidates": [
                primary,
                candidate("src/logging/Reporter.ets", "report", "class", 15.0),
            ],
            "source_ranges": [{
                "file_path": "src/policy/SizePolicy.ets",
                "symbol": "resolve",
                "start_line": 3,
                "end_line": 12,
                "selection_reason": "callable_symbol_range",
            }],
        })

        self.assertEqual("bounded", evidence["certainty"])

    def test_first_stage_prior_cannot_create_bounded_certainty_by_itself(self) -> None:
        primary = candidate("src/First.ets", "run", "class", 18.0)
        primary["evidence_score"] = 6.0
        alternative = candidate("src/Second.ets", "apply", "class", 12.0)
        alternative["evidence_score"] = 6.0
        evidence = callable_evidence({
            "callable_candidates": [primary, alternative],
            "source_ranges": [{
                "file_path": "src/First.ets",
                "symbol": "run",
                "start_line": 3,
                "end_line": 8,
                "selection_reason": "callable_symbol_range",
            }],
        })

        self.assertEqual("uncertain", evidence["certainty"])


def candidate(path: str, symbol: str, owner_kind: str, score: float) -> dict[str, object]:
    return {
        "file_path": path,
        "symbol": symbol,
        "owner_kind": owner_kind,
        "owner_name": path.rsplit("/", 1)[-1].split(".", 1)[0],
        "callable_roles": ["guard"],
        "score": score,
        "reasons": ["semantic_mechanism"],
    }


if __name__ == "__main__":
    unittest.main()
