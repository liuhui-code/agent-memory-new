# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Named focus must use the same positive query projection as retrieval."""
import unittest

from tools.agent_memory_runtime.query_code_focus import named_identity_candidates


class PositiveNamedFocusTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"file_path": "src/AlphaService.ts", "symbol": "stop"},
            {"file_path": "src/BetaService.ts", "symbol": "stop"},
        ]

    def test_positive_pair_is_retained(self):
        self.assertEqual(self.rows, named_identity_candidates(
            self.rows, "Locate AlphaService.stop and BetaService.stop."))

    def test_comparison_does_not_grant_positive_pair_focus(self):
        self.assertEqual([], named_identity_candidates(
            self.rows, "Locate AlphaService.stop compared with BetaService.stop."))

    def test_exclusion_does_not_grant_positive_pair_focus(self):
        self.assertEqual([], named_identity_candidates(
            self.rows, "Locate AlphaService.stop; exclude BetaService.stop."))

    def test_positive_pair_survives_unrelated_exclusion(self):
        self.assertEqual(self.rows, named_identity_candidates(
            self.rows, "Locate AlphaService.stop and BetaService.stop; exclude MissingService."))

    def test_code_markup_does_not_hide_positive_pair(self):
        self.assertEqual(self.rows, named_identity_candidates(
            self.rows, "Locate `AlphaService.stop` and `BetaService.stop`."))

    def test_single_name_does_not_add_focus_authority(self):
        self.assertEqual([], named_identity_candidates(
            self.rows, "Locate AlphaService.stop."))

    def test_positive_pair_with_comparison_keeps_only_positive_owners(self):
        third = {"file_path": "src/ThirdService.ts", "symbol": "stop"}
        self.assertEqual(self.rows, named_identity_candidates(
            [*self.rows, third],
            "Locate AlphaService.stop and BetaService.stop compared with ThirdService.stop."))


if __name__ == "__main__":
    unittest.main()
