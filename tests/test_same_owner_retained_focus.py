# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations
import copy
import unittest
from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors


def member(symbol, start, path="src/Owner.ets", owner="Owner"):
    return {"file_path": path, "owner_name": owner, "symbol": symbol,
            "source_range": {"start_line": start, "end_line": start+3}}


def fixture():
    first, second, extra = member("startPreview",5), member("stopPreview",19), member("finish",5,"src/Other.ets","Other")
    return {"anchors": [{"file_path":first["file_path"],"symbol":"startPreview","start_line":5,"end_line":8,
                         "record_id":17,"source":"wiki","symbol_type":"function","summary":"start summary"}],
            "evidence":{"certainty":"bounded","primary":first,"passage_portfolio":{"state":"composed",
            "selection_basis":["same_owner_named_retention","explicit_cross_file_targets"],"members":[first,second,extra]}},
            "path_activated":{"activated":False},"expected":"same"}


def controls():
    rows={}
    for name in ["marked_pair_with_crossfile_filler","true_third_crossfile_target","marker_absent","portfolio_inactive",
                 "single_valid_identity","primary_not_in_subset","unknown_owner","samefile_other_owner","invalid_range",
                 "duplicate_identity","exclusive_path","log_identity","uncertain_primary","activated_nonexclusive_path",
                 "graph_competition_veto","unmarked_samefile_portfolio","nonmutation","malformed_primary_or_evidence"]:
        rows[name]=fixture()
    for n in ["marked_pair_with_crossfile_filler","true_third_crossfile_target","duplicate_identity","nonmutation"]:rows[n]["expected"]="pair"
    rows["marker_absent"]["evidence"]["passage_portfolio"]["selection_basis"].remove("same_owner_named_retention")
    rows["portfolio_inactive"]["evidence"]["passage_portfolio"]["state"]="inactive"
    rows["single_valid_identity"]["evidence"]["passage_portfolio"]["members"].pop(1)
    rows["primary_not_in_subset"]["evidence"]["primary"] = member("otherPrimary",29)
    rows["unknown_owner"]["evidence"]["primary"]["owner_name"]=""
    rows["samefile_other_owner"]["evidence"]["passage_portfolio"]["members"][1]["owner_name"]="Other"
    rows["invalid_range"]["evidence"]["passage_portfolio"]["members"][1]["source_range"]["start_line"]=False
    rows["duplicate_identity"]["evidence"]["passage_portfolio"]["members"].append(member("stopPreview",19))
    rows["exclusive_path"]["path_activated"]={"activated":True,"wrapped_log_evidence":True}
    rows["log_identity"]["anchors"][0]["log_identity_match"]=True
    rows["uncertain_primary"]["evidence"]["certainty"]="uncertain"
    rows["activated_nonexclusive_path"]["path_activated"]={"activated":True}
    rows["graph_competition_veto"]["anchors"][0]["graph_neighbor"]=True
    rows["unmarked_samefile_portfolio"]["evidence"]["passage_portfolio"]["selection_basis"]=[]
    rows["unmarked_samefile_portfolio"]["evidence"]["passage_portfolio"]["members"].pop()
    rows["malformed_primary_or_evidence"]["evidence"]={}
    return rows


def evaluate(case):
    return focus_callable_anchors(case["anchors"],case["evidence"],case["path_activated"])


class SameOwnerRetainedFocusTests(unittest.TestCase):
    def test_positive_pair_is_source_bound_and_does_not_inherit_other_symbol_record(self):
        case=fixture();before=copy.deepcopy(case);out=evaluate(case)
        self.assertEqual(before,case)
        self.assertEqual(["startPreview","stopPreview"],[x["symbol"] for x in out])
        self.assertEqual(17,out[0]["record_id"])
        self.assertNotIn("record_id",out[1]);self.assertNotIn("summary",out[1])
        self.assertEqual("callable_evidence",out[1]["source"])
        self.assertEqual("method",out[1]["symbol_type"])
        self.assertEqual((19,22),(out[1]["start_line"],out[1]["end_line"]))

    def test_exact_identity_required_to_reuse_metadata(self):
        for field,value in [("symbol","other"),("start_line",4),("end_line",9)]:
            case=fixture();case["anchors"][0][field]=value;out=evaluate(case)
            self.assertTrue(all("record_id" not in x and "summary" not in x for x in out))
        case=fixture();case["anchors"].append({"file_path":"src/Owner.ets","symbol":"stopPreview","start_line":19,"end_line":22,"record_id":21})
        self.assertEqual(21,evaluate(case)[1]["record_id"])

    def test_invalid_ranges_duplicates_and_missing_primary_refuse_extension(self):
        for start,end in [(False,22),(0,22),(23,22),("19",22),(19,True)]:
            case=fixture();case["evidence"]["passage_portfolio"]["members"][1]["source_range"]={"start_line":start,"end_line":end}
            self.assertEqual(case["anchors"],evaluate(case))
        case=fixture();case["evidence"]["passage_portfolio"]["members"].append(member("stopPreview",20))
        self.assertEqual(case["anchors"],evaluate(case))
        case=fixture();case["evidence"]["passage_portfolio"]["members"][1]["source_range"]={"start_line":5,"end_line":8}
        self.assertEqual(case["anchors"],evaluate(case))

    def test_frozen_control_inputs_do_not_mutate(self):
        for name,case in controls().items():
            with self.subTest(control=name):
                before=copy.deepcopy(case);actual=evaluate(case);self.assertEqual(before,case)
                if case["expected"]=="pair":
                    self.assertEqual(["startPreview","stopPreview"],[x["symbol"] for x in actual])
                    self.assertTrue(all(x["file_path"]=="src/Owner.ets" for x in actual))


if __name__ == "__main__":unittest.main()
