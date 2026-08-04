# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import unittest

from tools.agent_memory_runtime.agent_benchmark_schedule import (
    execution_order_audit,
    pair_schedule,
)


class AgentBenchmarkScheduleTests(unittest.TestCase):
    def test_adjacent_trials_reverse_pair_order(self) -> None:
        first = pair_schedule(1, 1)
        second = pair_schedule(1, 2)

        self.assertEqual(["baseline", "memory"], [item[0] for item in first])
        self.assertEqual(["memory", "baseline"], [item[0] for item in second])
        self.assertEqual([1, 2], [item[1]["variant_position"] for item in first])

    def test_three_cases_three_trials_are_nearly_balanced(self) -> None:
        observations = []
        for case_position in range(1, 4):
            for trial_index in range(1, 4):
                for variant, order in pair_schedule(case_position, trial_index):
                    observations.append({"variant": variant, "execution_order": order})

        audit = execution_order_audit(observations)

        self.assertEqual("pass", audit["status"])
        self.assertEqual(9, audit["pair_count"])
        self.assertEqual({"baseline": 5, "memory": 4}, audit["first_variant_counts"])

    def test_incomplete_pair_fails_audit(self) -> None:
        variant, order = pair_schedule(1, 1)[0]

        audit = execution_order_audit([{"variant": variant, "execution_order": order}])

        self.assertEqual("fail", audit["status"])
        self.assertFalse(audit["complete_pairs"])

    def test_pack_local_pair_indexes_remain_distinct_across_cases(self) -> None:
        observations = []
        for case_id, case_position in (("case-a", 1), ("case-b", 2), ("case-c", 1)):
            for variant, order in pair_schedule(case_position, 1):
                observations.append({
                    "case_id": case_id,
                    "variant": variant,
                    "execution_order": order,
                })

        audit = execution_order_audit(observations)

        self.assertEqual("pass", audit["status"])
        self.assertEqual(3, audit["pair_count"])
        self.assertEqual({"baseline": 2, "memory": 1}, audit["first_variant_counts"])


if __name__ == "__main__":
    unittest.main()
