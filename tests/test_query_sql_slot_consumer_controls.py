"""Supplement #1: real issued receipt/consumer controls, not CLI acceptance.

BindingTests supplies setup/bind only (no duplicated inherited tests). Its DB adapter fixture
uses project_rows stub; receipt issuance/validation and compact consumer are real.
No receipt, guard, event matcher, transaction or consumer is mocked here.
"""
import copy
import unittest
from tests import test_query_sql_slot_selection as fixtures
from tests.test_query_sql_slot_guard import candidate
from tools.agent_memory_runtime import query_sql_slot_selection as sel
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.log_event_identity import event_match


class ConsumerSupplementTests(unittest.TestCase):
    setUp = fixtures.BindingTests.setUp
    bind = fixtures.BindingTests.bind
    def ordinary_baseline(self):
        b=copy.deepcopy(self.base)
        e=b['query_handoff']['callable_evidence']
        e.update(certainty='bounded',primary=candidate(),alternatives=[candidate()])
        return b

    def assert_rejected(self, mutate):
        data=self.bind()
        self.assertIsInstance(data,sel.SqlSlotContext)
        self.assertIsNotNone(sel.sql_slot_receipt(data))
        baseline=self.ordinary_baseline(); mutate(baseline)
        before=copy.deepcopy(baseline)
        result=sel.compact_sql_slot(data,baseline)
        self.assertIs(result,baseline)
        # NaN cannot use ordinary equality across fresh copies. The consumer's
        # same-object assertion is definitive; repr additionally guards writes.
        self.assertEqual(repr(baseline),repr(before))

    def test_P09_bool_candidate_allowed_through_consumer(self):
        for flag in (False,True):
            with self.subTest(flag=flag):
                data=self.bind(); baseline=self.ordinary_baseline()
                baseline['query_handoff']['callable_evidence']['primary']['target_owner_kind_match']=flag
                result=sel.compact_sql_slot(data,baseline)
                self.assertIsNot(result,baseline)
                self.assertEqual(len(result['query_handoff']['code_anchors']),3)
                self.assertEqual(restore_whitelist(result,baseline),baseline)

    def test_P11_T12_nested_noncode_restore(self):
        data=self.bind(); baseline=copy.deepcopy(self.base)
        nested={'opaque':[{'payload':{'flag':False,'items':[1,None,'kept']}}]}
        for target in (baseline['query_handoff'],baseline['sufficiency'],baseline['output_budget']):
            target['custom_noncode']=copy.deepcopy(nested)
        baseline['memory']=copy.deepcopy(nested)
        result=sel.compact_sql_slot(data,baseline)
        self.assertIsNot(result,baseline)
        self.assertEqual(len(result['query_handoff']['code_anchors']),3)
        self.assertEqual(restore_whitelist(result,baseline),baseline)

    def test_P04_real_event_match_conflict(self):
        data=self.bind(); baseline=copy.deepcopy(self.base)
        log={'message_template':self.query,'function':'emitStatus','file_path':'src/Telemetry.ets'}
        self.assertGreater(event_match(log,self.query)['priority'],0)
        baseline['query_handoff']['log_anchors']=[log]
        self.assertIs(sel.compact_sql_slot(data,baseline),baseline)

    def test_T07_truncated_true_preserved_on_success(self):
        data=self.bind(); baseline=copy.deepcopy(self.base)
        baseline['output_budget']['truncated']=True
        result=sel.compact_sql_slot(data,baseline)
        self.assertIsNot(result,baseline)
        self.assertIs(result['output_budget']['truncated'],True)
        self.assertEqual(restore_whitelist(result,baseline),baseline)

    def test_T08b_same_line_count_excerpt_corruption(self):
        data=self.bind(); self.assertIsNotNone(sel.sql_slot_receipt(data))
        excerpt=data._qualified['anchors'][0]['source_excerpts'][0]
        original=excerpt['content']; changed=original.replace('return','returX',1)
        self.assertNotEqual(changed,original)
        self.assertEqual(len(changed.splitlines()),len(original.splitlines()))
        self.assertEqual(len(changed),len(original))
        excerpt['content']=changed
        self.assertIs(sel.compact_sql_slot(data,self.base),self.base)


def callable_target(b,path):
    target=b['query_handoff']['callable_evidence']
    for part in path: target=target[part]
    return target


def install(name,path,key,value):
    def test(self):
        self.assert_rejected(lambda b:callable_target(b,path).__setitem__(key,copy.deepcopy(value)))
    setattr(ConsumerSupplementTests,'test_'+name,test)

# P05/P06 primary and alternative independently, including both range descendants.
for label,path in [('primary',('primary',)),('alternative',('alternatives',0)),
                   ('primary_range',('primary','source_range')),('alternative_range',('alternatives',0,'source_range'))]:
    install('P05_P06_unknown_'+label,path,'unknown',{'nested':[{'authority':'retained'}]})
# P07 malformed list containers and elements, both candidate branches.
for label,path in [('primary',('primary',)),('alternative',('alternatives',0))]:
    for key in ('reasons','callable_roles'):
        for shape,value in [('dict',{}),('nested_list',[{}])]:
            install('P07_'+label+'_'+key+'_'+shape,path,key,value)
# P08 every authority key at top, primary, alternative and both source ranges.
for label,path in [('top',()),('primary',('primary',)),('alternative',('alternatives',0)),
                   ('primary_range',('primary','source_range')),('alternative_range',('alternatives',0,'source_range'))]:
    for key in ('log_anchors','path_context','log_identity_match'):
        install('P08_'+label+'_'+key,path,key,{'nested':['authority']})
# P10 finite-number and strict integer boundaries through actual consumer.
for label,path in [('primary',('primary',)),('alternative',('alternatives',0))]:
    for key in ('score','evidence_score'):
        for tag,value in [('nan',float('nan')),('inf',float('inf')),('bool',True)]:
            install('P10_'+label+'_'+key+'_'+tag,path,key,value)
    for key in ('start_line','end_line'):
        install('P10_'+label+'_'+key+'_bool',path+('source_range',),key,True)
