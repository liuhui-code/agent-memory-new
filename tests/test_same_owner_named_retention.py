# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from tools.agent_memory_runtime.query_callable_passage_portfolio import build_callable_passage_portfolio
from tools.agent_memory_runtime.query_same_owner_retention import directly_named


def item(symbol, path="src/Owner.ets", owner="Owner", start=5):
    return {"file_path": path, "symbol": symbol, "owner_name": owner,
            "start_line": start, "end_line": start + 3, "reasons": ["semantic_mechanism"]}


def scenario(query="Inspect both startPreview and stopPreview.", values=None):
    values = values if values is not None else [item("startPreview"), item("stopPreview", start=19),
                                              item("unrelated", "src/Other.ets", "Other")]
    ranges = [{k: row[k] for k in ("file_path", "symbol", "start_line", "end_line")} for row in values]
    primary = {**values[0], "source_range": {"start_line": 5, "end_line": 8}}
    return {"query": query, "localization": {"callable_candidates": values, "source_ranges": ranges},
            "evidence": {"primary": primary}, "expected": "same"}


def controls():
    rows = {}
    rows["named_pair_with_other_file"] = scenario()
    rows["named_pair_with_other_file"]["expected"] = ["startPreview", "stopPreview", "unrelated"]
    rows["true_cross_file_pair"] = scenario(values=[item("startPreview"), item("stopPreview", "src/Other.ets", "Other")])
    third = scenario("Inspect both startPreview and stopPreview and finishPreview.",
                     [item("startPreview"), item("stopPreview", start=19), item("finishPreview", "src/Third.ets", "Third")])
    third["expected"] = ["startPreview", "stopPreview", "finishPreview"]
    rows["third_named_cross_file_already_selected"] = third
    rows["third_named_cross_file_not_previously_selected"] = scenario(third["query"],
        [item("startPreview"), item("stopPreview", start=19), item("x", "x", "X"), item("y", "y", "Y"), item("finishPreview", "z", "Z")])
    rows["fourth_named_candidate"] = scenario("Inspect both startPreview and stopPreview, finishPreview and flushPreview.",
        [item("startPreview"), item("stopPreview", start=19), item("finishPreview", "x", "X"), item("flushPreview", "y", "Y")])
    missing = scenario(); missing["localization"]["source_ranges"].pop(1)
    rows["named_candidate_missing_range"] = missing
    invalid = scenario(); invalid["localization"]["source_ranges"][1]["start_line"] = False
    rows["named_candidate_invalid_range"] = invalid
    other = scenario(); other["localization"]["callable_candidates"][1]["owner_name"] = "OtherOwner"
    rows["different_owner_same_file"] = other
    unknown = scenario(); unknown["evidence"]["primary"]["owner_name"] = ""
    rows["unknown_owner_or_primary_not_named"] = unknown
    rows["explicit_single"] = scenario("Find the implementation startPreview with stopPreview.")
    rows["single_and_both_conflict"] = scenario("Return only startPreview; inspect both startPreview and stopPreview.")
    rows["negative_or_comparison_name"] = scenario("Inspect both startPreview, excluding stopPreview.")
    rows["semantic_only_or_token_subset"] = scenario("Inspect both start preview and stop preview.")
    rows["complete_name_boundaries"] = scenario("Inspect both startPreviewExtra and $stopPreview.")
    duplicate = scenario(); duplicate["localization"]["callable_candidates"].append(copy.deepcopy(duplicate["localization"]["callable_candidates"][1]))
    duplicate["expected"] = ["startPreview", "stopPreview", "unrelated"]
    rows["duplicate_identity"] = duplicate
    rows["samefile_two_explicit_no_otherfile"] = scenario(values=[item("startPreview"), item("stopPreview", start=19)])
    bounded = scenario(values=[item("startPreview"), item("stopPreview", start=19), item("x", "x", "X"), item("y", "y", "Y")])
    bounded["expected"] = ["startPreview", "stopPreview", "x"]
    rows["unchanged_max_members_and_budget"] = bounded
    rows["transaction_original_control"] = scenario("Locate the commit failure path and rollback method that jointly enforce transaction compensation.",
                                                   [item("commitCheckpoint"), item("rollbackCheckpoint", start=23), item("unrelated", "x", "X")])
    return rows


class SameOwnerNamedRetentionTests(unittest.TestCase):
    def test_frozen_eighteen_control_groups(self):
        for name, case in controls().items():
            with self.subTest(control=name):
                args = [case[k] for k in ("query", "localization", "evidence")]
                with patch("tools.agent_memory_runtime.query_callable_passage_portfolio.retain_named_owner_methods",
                           side_effect=lambda q, p, c, r, e, original, limit: original):
                    original = build_callable_passage_portfolio(*args)
                actual = build_callable_passage_portfolio(*args)
                if case["expected"] == "same":
                    self.assertEqual(original, actual)
                else:
                    self.assertEqual(case["expected"], [x["symbol"] for x in actual["members"]])
                self.assertLessEqual(len(actual["members"]), 3)
                self.assertEqual(len(actual["members"]), len({(x["file_path"], x["symbol"]) for x in actual["members"]}))

    def test_identifier_boundaries_are_literal_and_unicode_aware(self):
        for text in ["fooBar", "$foo", "foo_", "éfoo", "foo中", "foo\u0301"]:
            self.assertFalse(directly_named("foo", text), text)
        for text in ["foo", "Owner.foo", "(foo)"]:
            self.assertTrue(directly_named("foo", text), text)
        self.assertTrue(directly_named("$foo", "Inspect $foo."))
        self.assertTrue(directly_named("读取", "Inspect 读取."))

    def test_named_range_and_duplicate_conflicts_never_enable_exception(self):
        cases = []
        for start, end in [(0, 22), (23, 22), ("19", 22), (19, True)]:
            case = scenario(); case["localization"]["source_ranges"][1].update(start_line=start, end_line=end); cases.append(case)
        for field, value in [("owner_name", "Other"), ("start_line", 20)]:
            case = scenario(); duplicate = dict(case["localization"]["callable_candidates"][1]); duplicate[field] = value
            case["localization"]["callable_candidates"].append(duplicate); cases.append(case)
        case = scenario(); duplicate = dict(case["localization"]["source_ranges"][1]); duplicate["end_line"] = 99
        case["localization"]["source_ranges"].append(duplicate); cases.append(case)
        for case in cases:
            args = [case[k] for k in ("query", "localization", "evidence")]
            with patch("tools.agent_memory_runtime.query_callable_passage_portfolio.retain_named_owner_methods",
                       side_effect=lambda q,p,c,r,e,original,limit: original):
                original = build_callable_passage_portfolio(*args)
            self.assertEqual(original, build_callable_passage_portfolio(*args))

    def test_named_other_owner_is_preserved_or_extension_declines(self):
        case = scenario("Inspect both startPreview and stopPreview and otherMethod.",
                        [item("startPreview"), item("stopPreview", start=19), item("otherMethod", "src/Owner.ets", "Other"), item("x", "x", "X")])
        args = [case[k] for k in ("query", "localization", "evidence")]
        with patch("tools.agent_memory_runtime.query_callable_passage_portfolio.retain_named_owner_methods",
                   side_effect=lambda q,p,c,r,e,original,limit: original):
            original = build_callable_passage_portfolio(*args)
        self.assertEqual(original, build_callable_passage_portfolio(*args))


if __name__ == "__main__":
    unittest.main()
