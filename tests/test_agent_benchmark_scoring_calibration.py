# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import unittest

from tools.agent_memory_runtime.agent_benchmark_eval import score_observation


class AgentBenchmarkScoringCalibrationTests(unittest.TestCase):
    def test_controlled_response_ordering_is_explicit(self) -> None:
        case = benchmark_case(["src/Owner.ets"])
        fully_correct = score_observation(case, observation("route", ["src/Owner.ets"]))
        overpredicted = score_observation(case, observation(
            "route", ["src/Owner.ets", "src/A.ets", "src/B.ets"]
        ))
        wrong_category = score_observation(case, observation("resource", ["src/Owner.ets"]))
        unsupported = score_observation(case, observation("unknown", [], "association"))

        self.assertEqual(1.0, fully_correct["agent_outcome_score"])
        self.assertGreater(fully_correct["agent_outcome_score"], overpredicted["agent_outcome_score"])
        self.assertGreater(overpredicted["agent_outcome_score"], wrong_category["agent_outcome_score"])
        self.assertGreater(wrong_category["agent_outcome_score"], unsupported["agent_outcome_score"])

    def test_partial_expected_files_are_not_scored_as_complete(self) -> None:
        case = benchmark_case(["src/Owner.ets", "src/Helper.ets"])

        partial = score_observation(case, observation("route", ["src/Owner.ets"]))
        complete = score_observation(case, observation(
            "route", ["src/Owner.ets", "src/Helper.ets"]
        ))

        self.assertEqual(0.5, partial["expected_file_recall"])
        self.assertLess(partial["agent_outcome_score"], complete["agent_outcome_score"])


def benchmark_case(expected_files: list[str]) -> dict:
    return {"oracle": {
        "expected_files": expected_files,
        "forbidden_files": [],
        "root_cause_category": "route",
        "expected_causal_level": "supported",
    }}


def observation(category: str, files: list[str], causal_level: str = "supported") -> dict:
    return {
        "root_cause_category": category,
        "predicted_files": files,
        "causal_level": causal_level,
        "verification_status": "unknown",
        "query_rounds": 1,
        "token_estimate": 100,
        "elapsed_ms": 100,
    }


if __name__ == "__main__":
    unittest.main()
