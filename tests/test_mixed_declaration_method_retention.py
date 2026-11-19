from copy import deepcopy
import unittest
from tools.agent_memory_runtime.context_callable_focus import multiple_requested_anchors_present as guard

class MixedDeclarationMethodTests(unittest.TestCase):
    def setUp(self):
        self.a=[dict(file_path='Model.ts',symbol='ParcelRecord',symbol_type='class',start_line=1,end_line=3),dict(file_path='View.ts',symbol='ParcelView',symbol_type='component',start_line=2,end_line=12)]
        self.e=dict(primary=dict(file_path='View.ts',symbol='renderBody',owner_name='ParcelView',source_range=dict(start_line=4,end_line=8)),alternatives=[])
        self.q='Locate both ParcelRecord and ParcelView.renderBody source.'
    def test_distinct_mixed_existing_sources(self):
        self.assertTrue(guard(self.a,self.e,self.q))
        e=deepcopy(self.e);e['alternatives']=[e.pop('primary')]
        self.assertTrue(guard(self.a,e,self.q))
    def test_negative_comparison_quoted_and_single_target_unchanged(self):
        for q in ('Locate ParcelView.renderBody rather than ParcelRecord.',
                  'Locate ParcelView.renderBody compared with ParcelRecord.',
                  'Find the string "ParcelRecord and ParcelView.renderBody".',
                  'Locate ParcelView.renderBody source.',
                  'Locate both ParcelRecord and missing source.'):
            self.assertFalse(guard(self.a,self.e,q),q)
    def test_declaration_identity_range_and_unique_path(self):
        for patch in ({'symbol':'ParcelRecordPreview'},{'symbol':'parcelrecord'},{'start_line':0},{'end_line':False}):
            a=deepcopy(self.a);a[0].update(patch);self.assertFalse(guard(a,self.e,self.q))
        a=self.a+[dict(self.a[0],file_path='other/Model.ts')]
        self.assertFalse(guard(a,self.e,self.q))
    def test_callable_range_must_be_covered_and_sources_distinct(self):
        for span in ({'start_line':1,'end_line':8},{'start_line':4,'end_line':20},{'start_line':True,'end_line':8}):
            e=deepcopy(self.e);e['primary']['source_range']=span;self.assertFalse(guard(self.a,e,self.q))
        a=deepcopy(self.a);a[0]['file_path']='View.ts';self.assertFalse(guard(a,self.e,self.q))
    def test_mixed_method_ambiguity_and_explicit_exclusion(self):
        q=self.q+' Exclude ParcelView.renderBody.'
        self.assertFalse(guard(self.a,self.e,q))
        a=self.a
        e=deepcopy(self.e);e['alternatives']=[dict(e['primary'],file_path='other/View.ts')]
        self.assertFalse(guard(a,e,self.q))
    def test_retention_never_mutates_or_invents_source(self):
        a,e=deepcopy(self.a),deepcopy(self.e);self.assertTrue(guard(a,e,self.q));self.assertEqual(self.a,a);self.assertEqual(self.e,e)
        self.assertFalse(guard(self.a[:1],self.e,self.q))

if __name__=='__main__':unittest.main()
