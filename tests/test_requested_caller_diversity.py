# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy,json,tempfile,unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_code_selection import diverse_code_matches
P=Path(__file__).resolve().parents[1]/'docs/eval/indirect-caller-current/protocol.json'
Q='Find both actual callers of ModalBridge.finish and ModalBridge.reset.'
def row(n,path):
 return dict(id=n,kind='symbol',file_path=path,symbol='onClick',symbol_key='symbol:'+str(n),start_line=6,end_line=8,source_digest='a'*64,score=20,match_reasons=['caller_owner','graph_neighbor','graph_relation:caller_owner'],caller_relations=['calls'])
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
 def test_same_source_duplicate_and_limits_are_unchanged(self):
  a,b=row(1,'ConfirmPanel.ets'),row(2,'ResetPanel.ets')
  self.assertEqual([a,b],diverse_code_matches([a,copy.deepcopy(a),b],5,query=Q))
  self.assertEqual([a],diverse_code_matches([a,b],1,query=Q))
  b['file_path']=a['file_path']
  self.assertEqual([a],diverse_code_matches([a,b],5,max_per_file=1,query=Q))
if __name__=='__main__':unittest.main()
