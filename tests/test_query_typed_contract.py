# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest
from tools.agent_memory_runtime.query_typed_contract import classify_contract, match_candidate


def candidate(signature="flush(records: string[], target: ArchiveSink):void", **extra):
    return {"symbol": "flush", "symbol_type": "function", "signature": signature,
            "method_evidence": "records foreach target append", **extra}


class TypedContractTests(unittest.TestCase):
    def test_explicit_relations(self):
        for query, kind in [
            ("Find the callable with an ArchiveSink parameter that invokes append on that parameter.", "parameter"),
            ("Find the callable that returns ArchiveSink.", "return"),
            ("Find the callable that returns the string literal ArchiveSink.", "literal"),
            ("Find the ArchiveSink interface declaration.", "declaration"),
        ]:
            self.assertEqual(classify_contract(query)["kind"], kind)

    def test_ambiguous_and_natural_queries_are_not_reinterpreted(self):
        for query in [
            "Find the callable that binds native runtime observer callbacks to the host ResultListener failure contract.",
            "Find the callable that sends records to ArchiveSink.",
            "Find ArchiveSink and OtherSink parameters",
            "Find a String parameter", "Find an ArchiveSink parameter that returns ArchiveSink",
            "Find a callable that does not return ArchiveSink",
            "Find a callable that returns ArchiveSink[]",
            "Find a callable that returns ArchiveSink.ets",
        ]:
            self.assertIsNone(classify_contract(query))

    def test_signature_parameter_not_literal_or_return(self):
        d = {"kind": "parameter", "identifier": "ArchiveSink"}
        self.assertTrue(match_candidate(candidate(), d))
        self.assertFalse(match_candidate(candidate("flush():ArchiveSink"), d))
        self.assertFalse(match_candidate(candidate("flush():void", string_evidence="ArchiveSink"), d))
        self.assertFalse(match_candidate(candidate("flush(x: ArchiveSinkExtra):void"), d))

    def test_return_does_not_accept_parameter_or_nested_return(self):
        d = {"kind": "return", "identifier": "ArchiveSink"}
        self.assertTrue(match_candidate(candidate("flush():ArchiveSink"), d))
        self.assertFalse(match_candidate(candidate(), d))
        self.assertFalse(match_candidate(candidate("flush():Promise<ArchiveSink>"), d))

    def test_string_evidence_not_comments_or_signature(self):
        d = {"kind": "literal", "identifier": "ArchiveSink"}
        self.assertTrue(match_candidate(candidate(string_evidence="ArchiveSink"), d))
        self.assertTrue(match_candidate(candidate(string_evidence="archivesink archive sink"), d))
        self.assertFalse(match_candidate(candidate(method_evidence="ArchiveSink"), d))
        self.assertFalse(match_candidate(candidate(string_evidence="ArchiveSinkExtra"), d))

    def test_declaration_is_not_a_callable_reference(self):
        d = {"kind": "declaration", "identifier": "ArchiveSink"}
        self.assertTrue(match_candidate({"symbol": "ArchiveSink", "symbol_type": "interface"}, d))
        self.assertFalse(match_candidate(candidate(), d))

    def test_receiver_operation_is_lexical_evidence_only(self):
        d = {"kind": "parameter", "identifier": "ArchiveSink", "operation": "append"}
        self.assertTrue(match_candidate(candidate(), d))
        self.assertFalse(match_candidate(candidate(method_evidence="target clear"), d))
        self.assertFalse(match_candidate(candidate(method_evidence="other append"), d))

    def test_nonuse_cannot_be_proven_by_missing_tokens(self):
        d = classify_contract("Find the callable that accepts ArchiveSink without using the parameter.")
        self.assertTrue(d["unused"])
        self.assertFalse(match_candidate(candidate(method_evidence="queue clear"), d))

    def test_nested_generics_and_multiple_typed_parameters(self):
        d = {"kind": "parameter", "identifier": "ArchiveSink"}
        self.assertTrue(match_candidate(candidate("flush(map: Map<string, Box<number>>, target: ArchiveSink):void"), d))
        for signature in ["flush(x: Box<ArchiveSink>):void", "flush(x: ArchiveSink | OtherSink):void",
                          "flush(x: ArchiveSink[]):void", "flush(x: ArchiveSink, y: ArchiveSink):void"]:
            self.assertFalse(match_candidate(candidate(signature), d))

    def test_unsupported_or_spoofed_signatures_fail_closed(self):
        d = {"kind": "parameter", "identifier": "ArchiveSink"}
        for signature in ["flush(x: string = 'ArchiveSink'):void", "flush(x: string /* ArchiveSink */):void",
                          "flush(cb: (x: ArchiveSink) => void):void", "flush(x: Map<ArchiveSink):void",
                          "other(x: ArchiveSink):void", "callback flush@12"]:
            self.assertFalse(match_candidate(candidate(signature), d))
        self.assertFalse(match_candidate(candidate(), {"kind": "parameter", "identifier": "UnknownSink"}))


if __name__ == "__main__":
    unittest.main()
