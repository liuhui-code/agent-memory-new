# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_code_selection import diverse_code_matches


def code_item(path: str, score: float) -> dict[str, object]:
    return {
        "file_path": path,
        "symbol": path.rsplit("/", 1)[-1].split(".", 1)[0],
        "score": score,
        "match_reasons": ["exact_path_segment"],
    }


class QueryRoleExclusionTests(unittest.TestCase):
    def test_explicit_sample_exclusion_keeps_production_implementation(self) -> None:
        production = code_item("src/cache/ThumbnailPool.ets", 40.0)
        example = code_item("src/examples/ThumbnailPoolExample.ets", 50.0)

        selected = diverse_code_matches(
            [example, production],
            3,
            query="Return thumbnail eviction ownership; exclude sample code.",
        )

        self.assertEqual([production], selected)


if __name__ == "__main__":
    unittest.main()
