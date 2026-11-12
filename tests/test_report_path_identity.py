# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.agent_memory_runtime import design_verification_evidence as evidence


class ReportPathIdentityTests(unittest.TestCase):
    def test_exact_stable_dedupe_strip_empty_and_legacy_unchanged(self):
        paths=["  /Case/One.json  ","", "  ","/Case/One.json","/case/one.json","/Case/Two.json"]
        with patch.object(evidence,"load_test_report",return_value=[]) as read, patch.object(evidence,"load_verification_provenance",return_value={}) as provenance:
            out=evidence.load_test_evidence(None,["  Run Test  ","run test"],paths)
        expected=["/Case/One.json","/case/one.json","/Case/Two.json"]
        self.assertEqual(expected,[call.args[0] for call in read.call_args_list])
        self.assertEqual(expected,provenance.call_args.args[2])
        self.assertEqual(1,len(out["tests"]))
        self.assertEqual("run test",out["tests"][0]["command"])

    def test_real_mixed_case_and_case_distinct_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"CaseDir";root.mkdir()
            first=root/"Report.json";second=root/"report.json"
            for path,name in [(first,"test_upper"),(second,"test_lower")]:
                path.write_text(json.dumps({"tests":[{"nodeid":name,"outcome":"passed"}]}))
            out=evidence.load_test_evidence(None,None,[str(first),str(second)])
            self.assertEqual(2,len(out["tests"]))
            self.assertEqual(["test_upper","test_lower"],[t["command"] for t in out["tests"]])
            with self.assertRaises(SystemExit):evidence.load_test_evidence(None,None,[str(root/"REPORT.json")])

    def test_twenty_distinct_limit_and_twentyone_rejection(self):
        paths=[f"/Case/report{i}.json" for i in range(20)]
        with patch.object(evidence,"load_test_report",return_value=[]) as read:
            evidence.load_test_evidence(None,None,paths+[paths[0]])
            self.assertEqual(20,read.call_count)
        with patch.object(evidence,"load_test_report",return_value=[]) as read:
            with self.assertRaisesRegex(SystemExit,"at most 20"):
                evidence.load_test_evidence(None,None,paths+["/case/report0.json"])
            self.assertEqual(0,read.call_count)


if __name__ == "__main__":unittest.main()
