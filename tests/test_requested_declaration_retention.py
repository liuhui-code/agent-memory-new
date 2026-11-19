"""Explicit declarations survive an unrelated, merely bounded callable prior."""
from copy import deepcopy
import unittest
from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors

class RequestedDeclarationRetentionTests(unittest.TestCase):
    def setUp(self):
        self.anchors=[dict(file_path='Record.ts',symbol='NoticeRecord',symbol_type='class',start_line=1,end_line=3),dict(file_path='Preview.ts',symbol='NoticePreview',symbol_type='component',start_line=2,end_line=8)]
        self.evidence=dict(certainty='bounded',primary=dict(file_path='Preview.ts',symbol='build',owner_name='NoticePreview',source_range=dict(start_line=4,end_line=6)))
    def call(self,q,anchors=None,evidence=None):
        return focus_callable_anchors(self.anchors if anchors is None else anchors,self.evidence if evidence is None else evidence,False,q)
    def test_explicit_declaration_keeps_all_old_objects(self):
        for wording in ('data entity','entity definition','record definition','data model','entity fields','class declaration'):
            with self.subTest(wording=wording):
                before=deepcopy(self.anchors)
                result=self.call('Locate the NoticeRecord '+wording+' rather than the NoticePreview rendering owner.')
                self.assertIs(result,self.anchors);self.assertEqual(before,result)
    def test_interface_and_struct_declarations(self):
        for kind in ('interface','struct'):
            anchors=deepcopy(self.anchors);anchors[0]['symbol_type']=kind
            self.assertIs(anchors,self.call('Return NoticeRecord '+kind+' declaration.',anchors))
    def test_negated_quoted_comparison_and_operational_mentions_no_new_permission(self):
        for q in ('Locate the NoticePreview rendering owner rather than the NoticeRecord data entity.',
                  'Find the string "NoticeRecord data entity" in source.',
                  'Compare NoticeRecord data entity and NoticePreview.',
                  'Locate the data entity that calls NoticePreview.build.',
                  'Locate NoticeRecord.build source.',
                  'Do not return the NoticeRecord data entity.',
                  'Locate the NoticeRecord data entity rather than NoticeRecord.',
                  'Locate the NoticeRecord data entity but only its caller.'):
            with self.subTest(q=q):self.assertEqual([self.anchors[1]],self.call(q))
    def test_exact_identity_valid_range_and_unique_path_required(self):
        for change in ({'symbol':'NoticeRecordPreview'},{'symbol':'noticerecord'},{'start_line':0},{'end_line':True},{'symbol_type':'component'}):
            anchors=deepcopy(self.anchors);anchors[0].update(change)
            self.assertEqual([anchors[1]],self.call('Locate the NoticeRecord data entity.',anchors))
        anchors=self.anchors+[dict(self.anchors[0],file_path='other/Record.ts')]
        self.assertEqual([self.anchors[1]],self.call('Locate the NoticeRecord data entity.',anchors))
    def test_does_not_override_typed_or_operation_authority(self):
        for key in ('typed_contract_match','source_operation_match','target_owner_kind_match'):
            evidence=deepcopy(self.evidence);evidence['primary'][key]=True
            result=self.call('Locate the NoticeRecord data entity.',evidence=evidence)
            self.assertEqual(['Preview.ts'],[x['file_path']for x in result])
    def test_no_mutation_or_budget_override(self):
        original=deepcopy(self.evidence)
        self.call('Locate the NoticeRecord data entity.')
        self.assertEqual(original,self.evidence)
        self.assertEqual([self.anchors[1]],self.call('x'*401))

if __name__=='__main__':unittest.main()
