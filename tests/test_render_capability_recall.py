# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from copy import copy,deepcopy
from dataclasses import replace
import json,sqlite3,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime import query_render_recall as r
from tools.agent_memory_runtime.query_method_evidence import qualifying_method_evidence_ids,method_evidence_focus_terms
def enabled_projection(q,custom_port=None):
 return r.recall_projection(q,custom_port,allow_render_recall=True)

Q='Return the UI rendering cleanup owner.'
class RenderRecallTests(unittest.TestCase):
 def test_frozen_requests(self):
  p=json.loads((Path(__file__).parents[1]/'docs/evidence/render-expression-witness-design/protocol.json').read_text())
  for family in p['families']:
   for c in family['queries']:
    expected=c['id'] in {'generic','head-only','discarded-return'}
    self.assertEqual(r.parse_render_request(c['query']) is not None,expected,c['id'])
 def test_ast_binding_and_copies(self):
  a='Locate the UI rendering cleanup owner rather than the message data entity.'
  b=a.replace('message','product');p=enabled_projection(a)
  self.assertEqual(p.request.exclusion,'message')
  self.assertTrue(p.valid_for(p.retrieval,a));self.assertFalse(p.valid_for(p.retrieval,b))
  for bad in [copy(p),deepcopy(p),replace(p,issuer=object()),replace(p,terms=('text',))]:self.assertFalse(bad.valid_for(p.retrieval,a))
  self.assertEqual(r.projected_method_terms(Q,{}),method_evidence_focus_terms(Q))
 def test_grammar_limits(self):
  for q in [Q+' extra',Q+'\n',Q.replace('UI','Uı'),Q.replace('Return','Return  '),Q.replace('owner','owner and model'), 'Not '+Q,'"'+Q+'"']:
   self.assertIsNone(r.parse_render_request(q),q)
 def test_custom_and_capacity(self):
  self.assertIsNone(enabled_projection(Q,object()))
  with patch.object(r,'method_evidence_focus_terms',return_value=[str(i)for i in range(16)]):self.assertIsNone(enabled_projection(Q))
 def test_old_two_term_lane(self):
  c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;c.execute('CREATE TABLE code_symbols(id INTEGER,project_id TEXT,method_evidence TEXT)')
  c.executemany('INSERT INTO code_symbols VALUES(?,?,?)',[(i,'p',v)for i,v in enumerate(['column text','row text','column row','text','replace','unrelated literal'])])
  p=enabled_projection(Q);self.assertEqual(qualifying_method_evidence_ids(c,SimpleNamespace(project_id='p'),list(range(6)),r.projected_method_terms(Q,p,Q)),[0,1,2]);c.close()
 def test_score_and_exact_not_granted(self):
  p=enabled_projection(Q)
  score,reasons=r.score_projected_code(p,{},Q,Q,[],set(),[('method_evidence','column text',.75)],[('exact_symbol','text',12)])
  self.assertEqual(score,1.5);self.assertEqual(set(reasons),{'expanded_query:method_evidence','expanded_render_capability:column','expanded_render_capability:text'})
 def test_excluded_old_contribution_only(self):
  q='Locate the UI rendering cleanup owner rather than the message data entity.';p=enabled_projection(q);row={'file_path':'MessageData.ets','owner_name':'MessageData'}
  self.assertTrue(p.excludes(row));self.assertEqual(r.projected_method_terms(p.retrieval,p,q,row),method_evidence_focus_terms(p.retrieval))
  self.assertEqual(r.score_projected_code(p,row,q,p.retrieval,[],set(),[('method_evidence','column text',.75)],[]),(0.0,[]))
 def test_builder_dispatch_exact(self):
  q='请返回设置内边距和背景颜色的 Builder 源码。';p=enabled_projection(q);b=r.builder.recall_projection(q)
  self.assertEqual(p,b);self.assertEqual(r.projected_method_terms(q,p,q),r.builder.projected_method_terms(q,b,q))
 def test_localization_transport(self):
  from tools.agent_memory_runtime.query_results import localization_input
  q='Locate the UI rendering cleanup owner rather than the message data entity.'
  matches={'wiki_matches':[{'file_path':'View.ets'},{'file_path':'MessageData.ets'}],'code_log_matches':[{'message':'retained'}]};saved=deepcopy(matches)
  with patch('tools.agent_memory_runtime.query_results.collect_matches_with_audit')as collect,patch('tools.agent_memory_runtime.query_results.gate_matches_by_intent',side_effect=lambda p,q,m:{'matches':m}):
   got,safe=localization_input(object(),q,matches,allow_render_recall=True)
  collect.assert_not_called();self.assertTrue(safe);self.assertEqual(matches,saved);self.assertEqual(got['wiki_matches'],matches['wiki_matches'][:1]);self.assertEqual(got['code_log_matches'],matches['code_log_matches'])
