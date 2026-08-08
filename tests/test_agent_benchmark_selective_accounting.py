# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.agent_benchmark_selective import selective_query_audit
from tools.agent_memory_runtime.agent_benchmark_treatment import (
    selective_treatment_metadata,
)


class SelectiveQueryAccountingTests(unittest.TestCase):
    def test_incomplete_query_outcome_accounting_fails_closed(self) -> None:
        cases = [{
            "id": "case-1",
            "oracle": {
                "query_skill_expectation": {"activation": "required", "max_queries": 2}
            },
        }]
        baseline = observation("baseline", 0, 0, 0)
        memory = observation("memory", 2, 1, 0)

        result = selective_query_audit(cases, [baseline, memory])

        self.assertEqual("fail", result["status"])
        self.assertFalse(result["checks"]["query_outcomes_accounted"])
        self.assertEqual(
            "telemetry_accounting", result["cases"][0]["first_observable_loss"]
        )


def observation(variant: str, count: int, success: int, errors: int) -> dict:
    digest = "a" * 64 if variant == "memory" else None
    return {
        "case_id": "case-1",
        "variant": variant,
        "memory_query_count": count,
        "memory_query_success_count": success,
        "memory_query_error_count": errors,
        "memory_query_metrics_reported": True,
        "treatment_metadata": selective_treatment_metadata(variant, digest, 3),
    }


if __name__ == "__main__":
    unittest.main()
