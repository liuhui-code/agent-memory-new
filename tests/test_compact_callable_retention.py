# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.context_budget import enforce_budget


class CompactCallableRetentionTests(unittest.TestCase):
    def test_budget_keeps_locatable_callable_primary(self) -> None:
        primary = callable_item("src/proto_guard.ets", "hasOwnKey")
        payload = compact_payload(primary)

        enforce_budget(payload, token_budget=1500)

        retained = payload["query_handoff"]["callable_evidence"]
        self.assertEqual("hasOwnKey", retained["primary"]["symbol"])
        self.assertEqual("src/proto_guard.ets", retained["primary"]["file_path"])
        self.assertEqual([], retained["alternatives"])


def compact_payload(primary: dict[str, object]) -> dict[str, object]:
    alternatives = [
        callable_item(f"src/noise-{index}.ets", f"noiseCallable{index}")
        for index in range(4)
    ]
    return {
        "query_handoff": {
            "log_keywords": [{"keyword": "performance"}] * 12,
            "log_anchors": [],
            "code_anchors": [],
            "callable_evidence": {
                "schema_version": "agent-callable-evidence/v1",
                "certainty": "uncertain",
                "primary": primary,
                "alternatives": alternatives,
            },
            "path_context": {"path_candidates": []},
            "relation_hints": [],
            "experience_refs": [],
            "semantic_refs": [],
        },
        "blocked_memory_notes": [],
        "conflict_notes": [],
        "semantic_patch_notes": [],
    }


def callable_item(file_path: str, symbol: str) -> dict[str, object]:
    return {
        "file_path": file_path,
        "symbol": symbol,
        "owner_kind": "module",
        "score": 42.0,
        "evidence_score": 42.0,
        "reasons": ["expanded_query:semantic_mechanism"] * 96,
        "source_range": {"start_line": 12, "end_line": 24},
    }


if __name__ == "__main__":
    unittest.main()
