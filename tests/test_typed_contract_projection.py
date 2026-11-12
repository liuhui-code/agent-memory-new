# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import unittest
from tools.agent_memory_runtime.context_typed_contract import declaration_projection
from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors
from tools.agent_memory_runtime.query_hierarchical_localization import rank_callables, source_range
from tools.agent_memory_runtime.query_callable_evidence import certainty

class TypedContractProjectionTests(unittest.TestCase):
    def test_declaration_does_not_select_string_reference(self):
        declared={'file_path':'a.ts','symbol':'ArchiveSink','symbol_type':'interface'}
        literal={'file_path':'b.ts','symbol':'describeContract','symbol_type':'function'}
        self.assertEqual([declared],declaration_projection([literal,declared], 'Find the ArchiveSink interface declaration.',{}))
        self.assertIsNone(declaration_projection([literal,declared], 'Find the ArchiveSink interface declaration.',{'activated':True}))
    def test_typed_match_is_not_score_boost(self):
        target={'id':1,'symbol_type':'method','symbol':'flush','signature':'flush(target: ArchiveSink):void','method_evidence':'target append','start_line':1,'end_line':7}
        distractor={'id':2,'symbol_type':'method','symbol':'retry','signature':'retry():void','string_evidence':'ArchiveSink parameter callable invokes append','start_line':1,'end_line':4,'direct_score':100}
        ranked=rank_callables([distractor,target], 'Find the callable with an ArchiveSink parameter that invokes append on that parameter.')
        self.assertEqual(1,ranked[0]['id'])
        self.assertTrue(ranked[0]['typed_contract_match'])
    def test_full_signature_range_retained(self):
        value={'typed_contract_match':True,'start_line':3,'end_line':16,'mechanism_evidence':'[{"line":10,"kind":"callback_binding","terms":["callback"]}]'}
        self.assertEqual(3,source_range(value,'callback')['start_line'])
        self.assertEqual(16,source_range(value,'callback')['end_line'])
    def test_multiple_matching_contracts_are_not_certain(self):
        item={'typed_contract_match':True,'source_range':{'start_line':1,'end_line':2}}
        self.assertEqual('uncertain',certainty(item,[dict(item)]))
    def test_focus_uses_matched_callable_not_wrong_samefile_anchor(self):
        primary={'typed_contract_match':True,'file_path':'a.ts','symbol':'flush','source_range':{'start_line':8,'end_line':14}}
        evidence={'certainty':'bounded','primary':primary}
        result=focus_callable_anchors([{'file_path':'a.ts','symbol':'ArchiveSink','start_line':1,'end_line':3}],evidence,False)
        self.assertEqual('flush',result[0]['symbol'])
        self.assertEqual(8,result[0]['start_line'])
