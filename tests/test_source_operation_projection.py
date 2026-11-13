# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy
import unittest
from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors

class SourceOperationProjectionTests(unittest.TestCase):
    def setUp(self):
        self.anchor={'source':'wiki','record_id':8,'file_path':'Owner.ts','symbol':'label','start_line':9,'end_line':11}
        self.primary={'file_path':'Owner.ts','symbol':'unpack','source_operation_match':True,'source_range':{'start_line':3,'end_line':8}}
        self.evidence={'certainty':'bounded','primary':self.primary}
    def test_replaces_disjoint_method_identity_not_only_label(self):
        out=focus_callable_anchors([self.anchor],self.evidence,False)
        self.assertEqual('unpack',out[0]['symbol'])
        self.assertEqual((3,8),(out[0]['start_line'],out[0]['end_line']))
        self.assertNotIn('record_id',out[0])
        self.assertEqual('callable_evidence',out[0]['source'])
        self.assertEqual('label',self.anchor['symbol'])
    def test_without_certificate_does_not_project_unproved_symbol(self):
        self.primary.pop('source_operation_match')
        self.assertEqual([self.anchor],focus_callable_anchors([self.anchor],self.evidence,False))
    def test_exclusive_path_and_log_identity_protection(self):
        for path in (True,{'activated':True,'wrapped_log_evidence':True},{'activated':True,'path_candidates':[{'complete':True}]}):
            self.assertEqual([self.anchor],focus_callable_anchors([self.anchor],self.evidence,path))
        self.anchor['log_identity_match']=True
        self.assertEqual([self.anchor],focus_callable_anchors([self.anchor],self.evidence,False))
