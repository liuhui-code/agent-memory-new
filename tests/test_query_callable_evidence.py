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
