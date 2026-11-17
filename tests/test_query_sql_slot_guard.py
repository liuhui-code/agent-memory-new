from copy import deepcopy
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime import query_sql_slot_guard as guard

QUERY = '请返回 LIKE 参数绑定和调用 lookupNotes 后渲染 notes 的页面，不要返回 DebugConsole。'

def descriptor(query=QUERY):
    m='lookupNotes';v='notes';n='DebugConsole';lo=query.index('，不要返回 ')
    return dict(query=query,sql_kind='LIKE',method=m,state=v,excluded_owner=n,
                method_span=[query.index(m),query.index(m)+len(m)],
                state_span=[query.index(v),query.index(v)+len(v)],
                negative_span=[lo,len(query)-1],observation_span=None)

def candidate():
    return dict(file_path='src/Panel.ets',symbol='submit',owner_name='Panel',owner_kind='component',
                target_owner_kind_match=True,score=4.0,evidence_score=4,
                callable_roles=['async'],reasons=['method_evidence'],
                source_range=dict(start_line=3,end_line=5,selection_reason='callable_symbol_range'))

def evidence():
    return dict(schema_version='agent-callable-evidence/v1',certainty='bounded',primary=candidate(),
                alternatives=[],boundary='retrieval_evidence_not_root_cause')

def context():
    return dict(query=QUERY,query_handoff=dict(input_query=QUERY,callable_evidence=evidence(),
        path_context=dict(activated=False,path_candidates=[]),code_anchors=[],log_anchors=[]))

class OrdinaryCallableTests(unittest.TestCase):
    def test_ordinary_and_empty(self):
        self.assertTrue(guard.ordinary_callable(evidence()))
        e=evidence();e['primary']=None;self.assertTrue(guard.ordinary_callable(e))
    def test_unknown_keys_at_every_depth(self):
        for path in [(),('primary',),('primary','source_range')]:
            for key in ['unknown','log_anchors','path_context','log_identity_match']:
                with self.subTest(path=path,key=key):
                    e=evidence();target=e
                    for part in path:target=target[part]
                    target[key]={};self.assertFalse(guard.ordinary_callable(e))
    def test_alternative_unknown(self):
        e=evidence();e['alternatives']=[candidate()];e['alternatives'][0]['unknown']=False
        self.assertFalse(guard.ordinary_callable(e))
    def test_bad_numbers_and_shapes(self):
        for key,values in [('score',[float('nan'),float('inf'),True]),('file_structural_coverage',[-1,True]),
                           ('reasons',[{},[{}]]),('callable_roles',[{},[{}]]),('target_owner_kind_match',[1])]:
            for value in values:
                e=evidence();e['primary'][key]=value;self.assertFalse(guard.ordinary_callable(e))
        for value in [True,0,-1]:
            e=evidence();e['primary']['source_range']['start_line']=value
            self.assertFalse(guard.ordinary_callable(e))
    def test_stronger_candidate_authority_rejected(self):
        for key in ['source_operation_match','typed_contract_match','artifact_role']:
            e=evidence();e['primary'][key]=True;self.assertFalse(guard.ordinary_callable(e))
    def test_portfolio_raw_only(self):
        e=evidence();e['passage_portfolio']={'state':'inactive','members':[]}
        self.assertFalse(guard.ordinary_callable(e))

class ProtectionTests(unittest.TestCase):
    def setUp(self):
        self.d=descriptor();self.data=context();self.pool=[]
        self.mock=patch.object(guard,'_reparse_request',return_value=deepcopy(self.d));self.mock.start();self.addCleanup(self.mock.stop)
    def protected(self,**kw):return guard.protected_sql_slot(self.data,QUERY,self.pool,self.d,**kw)
    def test_basic_slots_negative_and_ordinary_graph(self):
        for symbol in ['lookupNotes','notes','DebugConsole','Other']:
            self.pool.append(dict(symbol=symbol,graph_neighbor=True,graph_relation='imports',
                                  match_reasons=['graph_neighbor','graph_relation:imports']))
        self.assertFalse(self.protected())
    def test_descriptor_tamper_cannot_project(self):
        self.d['excluded_owner']='Panel';self.assertTrue(self.protected())
    def test_forged_equal_descriptor_span_is_rejected(self):
        self.d['negative_span']=[0,5]
        with patch.object(guard,'_reparse_request',return_value=deepcopy(self.d)):
            self.assertTrue(self.protected())
    def test_invalid_request_not_rescued(self):
        with patch.object(guard,'_reparse_request',return_value=None):self.assertTrue(self.protected())
    def test_path_pending_only(self):
        del self.data['query_handoff']['path_context']
        self.assertFalse(self.protected(pending=True));self.assertTrue(self.protected())
    def test_active_path(self):
        self.data['query_handoff']['path_context']['activated']=True;self.assertTrue(self.protected())
    def test_event_matching_uses_original_query(self):
        self.data['query_handoff']['log_anchors']=[{'message_template':'ordinary'}]
        with patch('tools.agent_memory_runtime.log_event_identity.event_match',return_value={'priority':1}) as event:
            self.assertTrue(self.protected());self.assertEqual(event.call_args.args[1],QUERY)
    def test_ordinary_log_preserved_not_blanket_veto(self):
        self.data['query_handoff']['log_anchors']=[{'message_template':'unrelated background status','function':'report'}]
        before=deepcopy(self.data);self.assertFalse(self.protected());self.assertEqual(before,self.data)
    def test_explicit_identity_not_descriptor_slot(self):
        self.pool=[{'symbol':'Other','identity_match':True}];self.assertTrue(self.protected())
        self.pool=[{'symbol':'lookupNotes','identity_match':True}];self.assertFalse(self.protected())
        self.pool=[{'symbol':'lookupNotes','log_identity_match':True}];self.assertTrue(self.protected())
    def test_extra_named_candidate_in_callable(self):
        self.data['query_handoff']['callable_evidence']['primary']['symbol']='LIKE'
        self.assertTrue(self.protected())
    def test_nested_authority_or_unknown_raw_callable(self):
        for key in ['log_anchors','path_context','log_identity_match','mystery']:
            self.data=context();self.data['query_handoff']['callable_evidence']['primary'][key]={}
            self.assertTrue(self.protected())
    def test_verified_negative_identity_only(self):
        self.pool=[{'symbol':'DebugConsole','identity_match':True}]
        self.assertFalse(self.protected())
        self.pool=[{'symbol':'DebugConsoleExtra','identity_match':True}]
        self.assertTrue(self.protected())
    def test_raw_portfolio_allowed(self):
        self.data['query_handoff']['callable_evidence']['passage_portfolio']={
            'schema_version':'x','state':'composed','members':[{'file_path':'src/Panel.ets','symbol':'submit',
            'source_range':{'start_line':3,'end_line':5},'support_reasons':['query_symbol_terms']}],
            'selection_basis':['explicit_cross_file_targets'],'candidate_recall_changed':False}
        self.assertFalse(self.protected())

if __name__=='__main__':unittest.main()
