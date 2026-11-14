# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy,json,tempfile,unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_code_selection import diverse_code_matches
from tools.agent_memory_runtime.query_caller_ownership import ResolvedCallerItem
P=Path(__file__).resolve().parents[1]/'docs/eval/indirect-caller-current/protocol.json'
Q='Find both actual callers of ModalBridge.finish and ModalBridge.reset.'
def row(n,path):
 return ResolvedCallerItem(dict(id=n,kind='symbol',file_path=path,symbol='onClick',symbol_key='symbol:'+str(n),start_line=6,end_line=8,source_digest='a'*64,score=20,match_reasons=['caller_owner','graph_neighbor','graph_relation:caller_owner'],caller_relations=['calls']),Q,(20,21))
class RequestedCallerDiversityTests(AgentMemoryTestBase):
 def test_public_both_retains_both_already_admitted_callers(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for n,s in json.loads(P.read_text())['sources'].items():(root/n).write_text(s)
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   for compact in (False,True):
    args=['context','--query',Q,'--json']+(['--compact'] if compact else [])
    out=json.loads(self.run_memory(root,*args).stdout)
    paths={x['file_path'] for x in out['query_handoff']['code_anchors']}
    self.assertTrue({'ConfirmPanel.ets','ResetPanel.ets'} <= paths)
 def test_distinct_typed_callers_survive_similarity_without_changing_order(self):
  a,b=row(1,'ConfirmPanel.ets'),row(2,'ResetPanel.ets')
  self.assertEqual([a,b],diverse_code_matches([a,b],5,query=Q))
 def test_generic_single_and_plain_graph_keep_old_diversity(self):
  for query in ('Find actual callers of ModalBridge.','Find actual caller of ModalBridge.finish.'):
   a,b=row(1,'ConfirmPanel.ets'),row(2,'ResetPanel.ets')
   self.assertEqual([a],diverse_code_matches([a,b],5,query=query))
  a,b=row(1,'ConfirmPanel.ets'),row(2,'ResetPanel.ets');b['match_reasons']=['exact_symbol']
  self.assertEqual([a],diverse_code_matches([a,b],5,query=Q))
 def test_missing_or_conflicting_identity_cannot_reserve(self):
  for key in ('id','file_path','symbol_key','start_line','end_line','source_digest'):
   a,b=row(1,'ConfirmPanel.ets'),row(2,'ResetPanel.ets');b.pop(key)
   self.assertLessEqual(len(diverse_code_matches([a,b],5,query=Q)),1)
  a,b=row(1,'ConfirmPanel.ets'),row(1,'ResetPanel.ets')
  self.assertEqual([a],diverse_code_matches([a,b],5,query=Q))
 def test_projection_and_query_changes_do_not_keep_private_binding(self):
  a,b=row(1,'ConfirmPanel.ets'),row(2,'ResetPanel.ets')
  for changed in (dict(b),json.loads(json.dumps(b))):
   self.assertEqual([a],diverse_code_matches([a,changed],5,query=Q))
  self.assertEqual([a],diverse_code_matches([a,b],5,query=Q+' Find both more sources.'))
  self.assertNotIn('request_binding',json.dumps(b))
 def test_unknown_or_ambiguous_target_does_not_receive_complete_binding(self):
  from tools.agent_memory_runtime.query_caller_ownership import explicit_caller_target_ids
  rows=[dict(id=1,file_path='A.ts',owner_name='A',symbol='run'),dict(id=2,file_path='B.ts',owner_name='B',symbol='run'),dict(id=3,file_path='C.ts',owner_name='B',symbol='run')]
  for q in ('Find both actual callers of A.run and B.run.', 'Find both actual callers of A.run and C.run.', 'Find both actual callers of A.run and missing.', 'Find both actual callers of A.run and explain behavior.', 'Find both actual callers of A.run,', 'Find both actual callers of A.run and', 'Find both actual callers of A.run or B.run.', 'Find both actual callers of A.run. Explain behavior.', 'Find both actual callers of missing and actual callers of A.run.'):
   self.assertEqual([1],explicit_caller_target_ids(rows,q))
   self.assertEqual([],explicit_caller_target_ids(rows,q,require_complete=True))
 def test_complete_separator_forms_and_post_gate_transport(self):
  from tools.agent_memory_runtime.query_caller_ownership import explicit_caller_target_ids, requested_caller_identities
  rows=[dict(id=1,file_path='A.ts',owner_name='A',symbol='run'),dict(id=2,file_path='B.ts',owner_name='B',symbol='run')]
  self.assertEqual([],explicit_caller_target_ids(rows,'Find both actual callers of A.run,B.run.',require_complete=True))
  self.assertEqual([1,2],explicit_caller_target_ids(rows,'Find both actual callers of A.run, B.run.',require_complete=True))
  a,b=row(1,'ConfirmPanel.ets'),row(2,'ResetPanel.ets');qualified=requested_caller_identities([a,b],Q)
  copies=[dict(a),dict(b)]
  self.assertEqual(copies,diverse_code_matches(copies,5,query=Q,caller_identities=qualified))
  self.assertEqual([copies[0]],diverse_code_matches(copies,5,query=Q+' More.',caller_identities=qualified))
  self.assertEqual([copies[0]],diverse_code_matches(copies,5,query=Q,caller_identities=[Q,list(qualified[1])]))
  copies[1]['match_reasons']=[]
  self.assertEqual([copies[0]],diverse_code_matches(copies,5,query=Q,caller_identities=qualified))
 def test_one_caller_of_two_methods_is_not_multiplied(self):
  from tools.agent_memory_runtime.query_caller_ownership import collect_bounded_caller_owners
  from tools.agent_memory_runtime.storage import resolve_project
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);sources=json.loads(P.read_text())['sources']
   sources['ConfirmPanel.ets']=sources['ConfirmPanel.ets'].replace('this.bridge.finish()', 'this.bridge.finish(); this.bridge.reset()')
   sources.pop('ResetPanel.ets')
   for n,s in sources.items():(root/n).write_text(s)
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   rows=collect_bounded_caller_owners(resolve_project(str(root),str(self.memory_home(root))),[{'file_path':'ModalBridge.ets','score':20}],Q)
   self.assertEqual(1,len(rows));self.assertEqual('ConfirmPanel.ets',rows[0]['file_path'])
   self.assertEqual(rows,diverse_code_matches(rows,5,query=Q))
   comma_rows=collect_bounded_caller_owners(resolve_project(str(root),str(self.memory_home(root))),[{'file_path':'ModalBridge.ets','score':20}],Q.replace(' and ',','))
   self.assertTrue(comma_rows)
   self.assertTrue(all(not isinstance(r,ResolvedCallerItem) for r in comma_rows))
 def test_same_source_duplicate_and_limits_are_unchanged(self):
  a,b=row(1,'ConfirmPanel.ets'),row(2,'ResetPanel.ets')
  self.assertEqual([a,b],diverse_code_matches([a,copy.deepcopy(a),b],5,query=Q))
  self.assertEqual([a],diverse_code_matches([a,b],1,query=Q))
  b['file_path']=a['file_path']
  self.assertEqual([a],diverse_code_matches([a,b],5,max_per_file=1,query=Q))
if __name__=='__main__':unittest.main()
