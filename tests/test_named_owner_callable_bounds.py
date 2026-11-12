# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations
import copy
import unittest
from tools.agent_memory_runtime.query_callable_passage_portfolio import build_callable_passage_portfolio
from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors


def fixture():
    candidates = [
        {"file_path":"owner.ts","symbol":"startPreview","owner_name":"Owner","start_line":5,"end_line":13,"reasons":["exact_symbol"]},
        {"file_path":"owner.ts","symbol":"stopPreview","owner_name":"Owner","start_line":20,"end_line":24,"reasons":["exact_symbol"]},
        {"file_path":"other.ts","symbol":"finish","owner_name":"Other","start_line":4,"end_line":8,"reasons":["semantic_mechanism"]}]
    ranges = [{"file_path":x["file_path"],"symbol":x["symbol"],"start_line":x["start_line"],"end_line":x["end_line"],
               "callable_start_line":x["start_line"],"callable_end_line":x["end_line"],"selection_reason":"callable_symbol_range"} for x in candidates]
    ranges[0].update(start_line=6,end_line=10,selection_reason="semantic_mechanism_window",mechanism_kind="guard",mechanism_terms=["guard"])
    primary={"file_path":"owner.ts","symbol":"startPreview","owner_name":"Owner","source_range":{"start_line":6,"end_line":10}}
    return {"query":"Inspect both startPreview and stopPreview.","localization":{"callable_candidates":candidates,"source_ranges":ranges},
            "evidence":{"certainty":"bounded","primary":primary},"anchors":[{"file_path":"owner.ts","symbol":"startPreview","start_line":5,"end_line":13,"record_id":17,"summary":"whole start"}],
            "path_activated":False,"expected":"expand"}


def evaluate(case):
    evidence=copy.deepcopy(case["evidence"])
    portfolio=build_callable_passage_portfolio(case["query"],case["localization"],evidence)
    evidence["passage_portfolio"]=portfolio
    return {"portfolio":portfolio,"anchors":focus_callable_anchors(case["anchors"],evidence,case["path_activated"])}


def controls():
    names=["typed_pair","missing_full_bounds","invalid_full_bounds","window_outside_callable","candidate_bounds_mismatch","conflicting_duplicate_full_bounds",
           "identity_or_owner_mismatch","one_member_missing_bounds","no_marker_or_no_exception","crossfile_member","semantic_type_preserved","exact_expanded_identity_metadata",
           "inputs_not_mutated","veto_controls","no_budget_changes","existing_single_method"]
    rows={name:fixture() for name in names}
    for n in names[1:9]:rows[n]["expected"]="same"
    rows["missing_full_bounds"]["localization"]["source_ranges"][0].pop("callable_start_line")
    rows["invalid_full_bounds"]["localization"]["source_ranges"][0]["callable_start_line"]=True
    rows["window_outside_callable"]["localization"]["source_ranges"][0]["start_line"]=4
    rows["candidate_bounds_mismatch"]["localization"]["callable_candidates"][0]["end_line"]=14
    duplicate=copy.deepcopy(rows["conflicting_duplicate_full_bounds"]["localization"]["source_ranges"][0]);duplicate["callable_end_line"]=14
    rows["conflicting_duplicate_full_bounds"]["localization"]["source_ranges"].append(duplicate)
    rows["identity_or_owner_mismatch"]["localization"]["callable_candidates"][1]["owner_name"]="OtherOwner"
    rows["one_member_missing_bounds"]["localization"]["source_ranges"][1].pop("callable_end_line")
    rows["no_marker_or_no_exception"]["query"]="Inspect both start preview and stop preview."
    rows["exact_expanded_identity_metadata"]["anchors"][0].update(start_line=6,end_line=10)
    rows["veto_controls"]["anchors"][0]["log_identity_match"]=True
    rows["veto_controls"]["expected"]="anchors_same"
    rows["existing_single_method"]["query"]="Find the implementation startPreview."
    rows["existing_single_method"]["expected"]="same"
    return rows


class NamedOwnerCallableBoundsTests(unittest.TestCase):
    def test_typed_window_remains_separate_and_complete_projection_has_exact_metadata(self):
        case=fixture();before=copy.deepcopy(case);out=evaluate(case);self.assertEqual(before,case)
        first=out["portfolio"]["members"][0]["source_range"]
        self.assertEqual((6,10),(first["start_line"],first["end_line"]))
        self.assertEqual("semantic_mechanism_window",first["selection_reason"])
        self.assertEqual((5,13),(first["callable_start_line"],first["callable_end_line"]))
        self.assertEqual([(5,13),(20,24)],[(x["start_line"],x["end_line"]) for x in out["anchors"]])
        self.assertEqual(17,out["anchors"][0]["record_id"]);self.assertNotIn("record_id",out["anchors"][1])
        self.assertNotIn("callable_start_line",out["portfolio"]["members"][2]["source_range"])
        case["anchors"][0].update(start_line=6,end_line=10)
        self.assertNotIn("record_id",evaluate(case)["anchors"][0])

    def test_bad_full_bounds_are_atomic_v2_fallback(self):
        for lo,hi in [(0,13),(14,13),("5",13),(False,13),(5,True)]:
            case=fixture();case["localization"]["source_ranges"][0].update(callable_start_line=lo,callable_end_line=hi)
            out=evaluate(case)
            self.assertEqual([(6,10),(20,24)],[(x["start_line"],x["end_line"]) for x in out["anchors"]])
            self.assertTrue(all("callable_start_line" not in x["source_range"] for x in out["portfolio"]["members"]))

    def test_frozen_controls_do_not_mutate_inputs(self):
        for name,case in controls().items():
            with self.subTest(control=name):
                before=copy.deepcopy(case);out=evaluate(case);self.assertEqual(before,case)
                if case["expected"]=="expand":self.assertEqual([(5,13),(20,24)],[(x["start_line"],x["end_line"]) for x in out["anchors"]])


if __name__ == "__main__":unittest.main()
