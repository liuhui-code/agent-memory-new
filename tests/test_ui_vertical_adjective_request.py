"""Direct request/guard units only; synthetic rows are not public CLI evidence."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime.query_ui_vertical_request import vertical_request, vertical_identity_query
from tools.agent_memory_runtime.query_ui_vertical_guard import protected_vertical
from tools.agent_memory_runtime.query_record_loop_selection import protected_record_loop
from tools.agent_memory_runtime.log_event_identity import event_match

Q='The viewport clips cedar records and the vertical layout does not move. Return the current code owner.'
HEAD='Locate the cedar vertical layout source.'
OBS='Cedar records cannot scroll when their content fills the viewport. Locate the vertical layout owner.'
GUARD='tools.agent_memory_runtime.query_ui_vertical_guard.'

def baseline():
    return {'query_handoff':{'path_context':{'activated':False,'path_candidates':[]},'code_anchors':[],'log_anchors':[]}}

def log_row():
    return {'record_id':7,'file_path':'StatusReporter.ts','function':'report','level':'error','logger':'console',
            'message_template':'Return the current code owner','raw_statement':"console.error('Return the current code owner')",'match_reasons':[]}

class VerticalAdjectiveRequestTests(unittest.TestCase):
    def test_exact_fixed_slot_preserves_every_other_character(self):
        projected=vertical_identity_query(Q);start=Q.index('current')
        self.assertEqual(projected,Q[:start]+' '*7+Q[start+7:])
        self.assertEqual(len(projected),len(Q));self.assertEqual(projected.encode()[:start],Q.encode()[:start])
        self.assertEqual(projected[start+7:],Q[start+7:]);self.assertEqual(vertical_request(Q),'cedar')
        self.assertEqual([i for i,(a,b)in enumerate(zip(Q,projected))if a!=b],list(range(start,start+7)))
    def test_other_two_families_unchanged(self):
        for query in (HEAD,OBS):
            self.assertEqual(vertical_identity_query(query),query);self.assertEqual(vertical_request(query),'cedar')
    def test_unsupported_queries_never_project(self):
        for query in ('"'+Q+'"','`'+Q+'`',Q+' Also current.',Q.replace('Return','Do not return'),Q+' '+HEAD,Q.replace('cedar','current'),Q.replace('current code','current current code'),Q.replace('current','Current'),Q+'\n',Q.replace('cedar','cedar or maple')):
            with self.subTest(query=query):
                self.assertIsNone(vertical_request(query));self.assertEqual(vertical_identity_query(query),query)
    def test_current_reserved_in_all_families(self):
        for query in (HEAD.replace('cedar','current'),OBS.replace('Cedar','Current'),Q.replace('cedar','current')):
            self.assertIsNone(vertical_request(query));self.assertEqual(vertical_identity_query(query),query)
    def test_real_other_name_not_exempted(self):
        data=baseline()
        self.assertTrue(protected_record_loop(data,Q,[{'symbol':'current'}]))
        self.assertFalse(protected_vertical(data,Q,[{'symbol':'current'}]))
        for field,value in (('symbol','code'),('owner_name','owner'),('qualified_name','cedar'),('file_path','viewport')):
            self.assertTrue(protected_vertical(data,Q,[{field:value}]))
        for query in (HEAD,OBS):
            self.assertTrue(protected_vertical(data,query,[{'symbol':'vertical'}]))
    def test_identity_graph_flags_all_retained(self):
        for flag in ('identity_match','log_identity_match','graph_neighbor','graph_relation'):
            data=baseline();data['query_handoff']['code_anchors']=[{flag:True}]
            self.assertTrue(protected_vertical(data,Q,[]))
            self.assertTrue(protected_vertical(baseline(),Q,[{'symbol':'current',flag:True}]))
    def test_active_path_and_seeds_retained(self):
        for key,value in (('activated',True),('path_candidates',[{}]),('wrapped_log_evidence',[{}]),('seeds',[{}])):
            data=baseline();data['query_handoff']['path_context'][key]=value
            self.assertTrue(protected_vertical(data,Q,[]))
    def test_malformed_anchor_and_path_lists_fail_closed(self):
        for key in ('code_anchors','log_anchors'):
            for value in (None,{},'text',[None]):
                data=baseline();data['query_handoff'][key]=value
                with self.subTest(key=key,value=value):self.assertTrue(protected_vertical(data,Q,[]))
        for value in (None,{},[],{'activated':0,'path_candidates':[]},{'activated':False,'path_candidates':{}}):
            data=baseline();data['query_handoff']['path_context']=value
            self.assertTrue(protected_vertical(data,Q,[]))
    def test_full_original_event_actual_match_restored(self):
        data=baseline();row=log_row();data['query_handoff']['log_anchors']=[row]
        self.assertGreater(event_match(row,Q)['priority'],0)
        self.assertEqual(event_match(row,vertical_identity_query(Q))['priority'],0)
        self.assertFalse(protected_record_loop(data,vertical_identity_query(Q),[]))
        self.assertTrue(protected_vertical(data,Q,[]))
    def test_full_original_named_owner_callback(self):
        data=baseline();row=log_row();data['query_handoff']['log_anchors']=[row]
        # Instrumentation-only: independently assert restoration argument, not real recall.
        with patch(GUARD+'protected_record_loop',return_value=False),patch(GUARD+'event_match',return_value={'priority':0}),patch(GUARD+'independently_named_log_owner',return_value=True) as named:
            self.assertTrue(protected_vertical(data,Q,[]));named.assert_called_once_with(row,Q)
    def test_projected_guard_receives_only_projection_and_pending(self):
        data=baseline();pool=[{'symbol':'unrelated'}];original=deepcopy(data)
        with patch(GUARD+'protected_record_loop',return_value=False) as shared:
            self.assertFalse(protected_vertical(data,Q,pool,pending=True))
            shared.assert_called_once_with(data,vertical_identity_query(Q),pool,pending=True)
        self.assertEqual(data,original)
