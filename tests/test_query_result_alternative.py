# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
import unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_runtime_capability_public import FILES
from tools.agent_memory_runtime.query_language import (
    result_alternative_query, positive_retrieval_query, excluded_result_roles,
    excluded_result_identifiers, excluded_code_candidate,
)

class ResultAlternativeTests(unittest.TestCase):
    def test_explicit_result_alternative_matches_existing_rather_than_contract(self):
        for query in ['Find executable source instead of metadata.',
                      'Runtime failed; locate the bundle capability query instead of settings text.',
                      'RETURN SOURCE, INSTEAD OF METADATA.',
                      'Find ExtensionSettings.build instead of ExtensionInspector.inspectInstalled.',
                      'Find implementation instead of sample code.']:
            expected=query.replace('instead of','rather than').replace('INSTEAD OF','rather than').replace(', rather than',' rather than')
            self.assertEqual(positive_retrieval_query(expected),positive_retrieval_query(query),query)
            self.assertEqual(excluded_result_roles(expected),excluded_result_roles(query),query)
            self.assertEqual(excluded_result_identifiers(expected),excluded_result_identifiers(query),query)
        self.assertTrue(excluded_code_candidate('Find implementation instead of SampleOwner.',{'owner_name':'SampleOwner'}))
    def test_operation_comparison_and_ambiguous_naked_targets_unchanged(self):
        for query in ['find code that uses X instead of Y',
                      'convert A to B instead of C',
                      'Find source that uses old method instead of new method.',
                      'Find implementation using an old source instead of a new source.',
                      'Return A instead of B', 'instead of metadata',
                      'Search original text: return source instead of metadata.',
                      'Find source; instead of metadata.',
                      'Find the original text containing source instead of metadata.']:
            self.assertEqual(query,result_alternative_query(query))
    def test_quoted_original_text_and_literal_are_not_rewritten(self):
        for query in ['Find literal "return source instead of metadata".',
                      "Find text 'return source instead of metadata'.",
                      'Find `return source instead of metadata`.',
                      'Find literal "line; return source instead of metadata".']:
            self.assertEqual(query,result_alternative_query(query))
    def test_missing_positive_target_preserves_existing_fallback(self):
        self.assertEqual('instead of settings text',positive_retrieval_query('instead of settings text'))
        self.assertEqual('exclude metadata',positive_retrieval_query('exclude metadata'))

class ResultAlternativePublicTests(AgentMemoryTestBase):
    def test_source_and_text_targets_keep_direction_and_real_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name,text in FILES.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            def context(query):
                return json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)['query_handoff']
            query='Runtime capability inspection is unavailable; find the executable source instead of manifest metadata or settings text.'
            h=context(query)
            self.assertEqual({'src/runtime/ExtensionInspector.ets'},{a['file_path'] for a in h['code_anchors']})
            body=' '.join(e['content'] for a in h['code_anchors'] for e in a.get('source_excerpts',[]))
            self.assertIn('bundleManager.getBundleInfoForSelf',body)
            other=context(query.replace('instead of','rather than'))
            self.assertEqual([a['file_path'] for a in h['code_anchors']],[a['file_path'] for a in other['code_anchors']])
            h=context('Find runtime capability manifest metadata instead of executable source.')
            self.assertFalse(h.get('callable_evidence',{}).get('primary',{}).get('source_operation_match'))
            h=context('Locate ExtensionSettings.build instead of ExtensionInspector.inspectInstalled.')
            self.assertEqual({'src/ui/ExtensionSettings.ets'},{a['file_path'] for a in h['code_anchors']})
            h=context('Find both ExtensionInspector.inspectInstalled and ExtensionSettings.build source.')
            self.assertTrue({'src/runtime/ExtensionInspector.ets','src/ui/ExtensionSettings.ets'} <= {a['file_path'] for a in h['code_anchors']})
