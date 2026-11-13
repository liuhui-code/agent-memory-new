# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors

class ExplicitCrossFileNarrowingGuardTests(unittest.TestCase):
    def setUp(self):
        self.anchors=[{'file_path':'a.ts','start_line':1,'end_line':9}, {'file_path':'b.ts','start_line':2,'end_line':5}]
        self.first={'file_path':'a.ts','owner_name':'Alpha','symbol':'stop','source_range':{'start_line':3,'end_line':7}}
        self.second={'file_path':'b.ts','owner_name':'Beta','symbol':'stop','source_range':{'start_line':2,'end_line':5}}
        self.evidence={'certainty':'bounded','primary':self.first,'alternatives':[self.second]}
    def test_two_exact_covered_targets_decline_narrowing(self):
        self.assertEqual(self.anchors,focus_callable_anchors(self.anchors,self.evidence,False,'Return Alpha.stop and Beta.stop.'))
    def test_single_target_keeps_single_focus(self):
        self.assertEqual(self.anchors[:1],focus_callable_anchors(self.anchors,self.evidence,False,'Return Alpha.stop.'))
    def test_does_not_materialize_missing_second_target(self):
        self.assertEqual(self.anchors[:1],focus_callable_anchors(self.anchors[:1],self.evidence,False,'Return Alpha.stop and Beta.stop.'))
    def test_out_of_range_cannot_enable_guard(self):
        self.second['source_range']['end_line']=99
        self.assertEqual(self.anchors[:1],focus_callable_anchors(self.anchors,self.evidence,False,'Return Alpha.stop and Beta.stop.'))
    def test_prefix_does_not_enable_guard(self):
        self.assertEqual(self.anchors[:1],focus_callable_anchors(self.anchors,self.evidence,False,'Return Alpha.stop and Beta.stopLater.'))
    def test_same_file_does_not_grant_cross_file_retention(self):
        self.second['file_path']='a.ts'
        self.assertEqual(self.anchors[:1],focus_callable_anchors(self.anchors,self.evidence,False,'Return Alpha.stop and Beta.stop.'))
    def test_uncertified_portfolio_still_cannot_project(self):
        self.evidence['passage_portfolio']={'state':'composed','selection_basis':['indexed_explicit_owner_methods'],'members':[{'file_path':'unseen.ts'}]}
        self.assertEqual(self.anchors,focus_callable_anchors(self.anchors,self.evidence,False,'Return Alpha.stop and Beta.stop.'))
