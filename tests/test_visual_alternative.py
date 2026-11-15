# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from copy import copy, deepcopy
from contextlib import nullcontext
import hashlib, json, unittest
from pathlib import Path
from unittest.mock import patch
from test_background_selection import BackgroundSelectionTests
from tools.agent_memory_runtime.query_stacking_source import parse_stacking_source, parse_visual_alternative_source
from tools.agent_memory_runtime.query_background_source import parse_background_source
from tools.agent_memory_runtime.query_render_recall import parse_render_request, recall_projection
from tools.agent_memory_runtime.query_render_selection import bind_render_context, retain_background_candidates
from tools.agent_memory_runtime.context_compact import compact_context
D=Path(__file__).parents[1]/'docs/evidence/visual09-english-alternative-20261115'
P=json.loads((D/'union-protocol.json').read_text());Q=P['cases'][0]['query']
STACK=P['cases'][0]['sources']['LayerSurface.ets']
CALLBACK=P['cases'][4]['sources']['GestureSurface.ets']

class VisualAlternativeSourceTests(unittest.TestCase):
 def test_direct_stack_and_closed_callback(self):
  for source in [STACK,CALLBACK,CALLBACK.replace('() =>','(evt: TouchEvent) =>'),CALLBACK.replace('openPanel','arbitraryHandler'),STACK.replace('\n','\r\n'),CALLBACK.replace('this.openPanel()','this.first(); this.second()')]:
   with self.subTest(source=source):
    self.assertIsNotNone(parse_stacking_source(source));self.assertIsNotNone(parse_visual_alternative_source(source))
    self.assertIsNone(parse_background_source(source))
 def test_nonwitness_shadow_and_unsupported_remain_unknown(self):
  for source in [STACK.replace('LayerSurface','Stack'),STACK.replace("Stack() { Text('Summary') }","Column() { Text('Stack() {}') }"),STACK.replace("Stack() { Text('Summary') }","Column() {} // Stack() {}"),CALLBACK.replace('this.openPanel()','Stack() {}'),CALLBACK.replace('this.openPanel()','this.openPanel(`unknown`)'),CALLBACK.replace('this.openPanel()','if (this.ready) { this.openPanel() }'),CALLBACK.replace('() =>','(Stack) =>'),CALLBACK.replace('this.openPanel()','const Stack = this.openPanel'),CALLBACK+'\nexport class Stack {}',CALLBACK.replace('export struct','import { Stack } from "./x";\nexport struct'),CALLBACK[:-3],CALLBACK.replace('Stack()','this.Stack()')]:
   with self.subTest(source=source):self.assertIsNone(parse_stacking_source(source))
 def test_request_union_and_rejections(self):
  for q in [Q,Q.replace('stacking or background styling','background styling or stacking'),'The ribbon covers the control. '+Q,Q.replace('Return','Locate'),Q.replace('Return','Find')]:
   self.assertEqual(parse_render_request(q).capability,'visual_alternative')
   self.assertEqual(recall_projection(q,allow_render_recall=True).terms,('stack','backgroundcolor'))
  for q in [Q.replace(' or ',' and '),'Not '+Q,'"'+Q+'"',Q+' Also return helper.','The not toolbar covers footer. '+Q,'A.build covers footer. '+Q,Q+'\n','Return the stacking source.']:
   self.assertIsNone(parse_render_request(q),q)

class VisualAlternativeSelectionTests(BackgroundSelectionTests):
 # Reuse only fixture setup; inherited background tests remain unchanged controls.
 def union_trial(self):
  baseline=deepcopy(self.baseline);baseline['query']=Q
  return baseline,retain_background_candidates(Q,deepcopy(baseline),self.pool)
 def add_stack(self,name='LayerSurface',source=STACK):
  source=source.replace('LayerSurface',name);path=name+'.ets';(self.project.root/path).write_text(source)
  digest=hashlib.sha256(source.encode()).hexdigest();parsed=parse_stacking_source(source)
  next_id=self.db.execute('SELECT MAX(id) FROM code_symbols').fetchone()[0]+1
  template=dict(self.db.execute("SELECT * FROM code_symbols WHERE symbol='build'").fetchone())
  for i,(symbol,typ,start,end,owner) in enumerate([(name,'component',2,len(source.splitlines()),''),('build','function',parsed['build_start'],parsed['build_end'],name)]):
   r={**template,'id':next_id+i,'symbol_key':name+'.'+symbol,'file_path':path,'symbol':symbol,'qualified_name':name+'.'+symbol if owner else name,'symbol_type':typ,'start_line':start,'end_line':end,'owner_name':owner,'source_digest':digest}
   self.db.execute('INSERT INTO code_symbols VALUES('+','.join('?'for _ in r)+')',list(r.values()))
   if owner:self.pool.append(dict(r,kind='symbol',method_evidence='stack'))
  self.db.execute('INSERT INTO code_files VALUES(?,?,?,?)',(path,'p',digest,1))
 def bind_union(self,baseline,trial):
  with patch('tools.agent_memory_runtime.query_render_selection.connect',return_value=nullcontext(self.db)):
   return bind_render_context(self.project,Q,baseline,trial)
 def test_union_all_positive_complete_or_fallback(self):
  self.add_stack();baseline,trial=self.union_trial();out=compact_context(self.bind_union(baseline,trial))
  self.assertEqual({a['file_path']for a in out['query_handoff']['code_anchors']},{'AmountSurface.ets','LayerSurface.ets'})
  self.assertTrue(all(not e['truncated']for a in out['query_handoff']['code_anchors']for e in a['source_excerpts']))
  self.add_stack('SecondLayer');baseline,trial=self.union_trial();out=compact_context(self.bind_union(baseline,trial))
  self.assertEqual(len(out['query_handoff']['code_anchors']),3)
  self.add_stack('ThirdLayer');baseline,trial=self.union_trial();self.assertIs(self.bind_union(baseline,trial),baseline)
 def test_union_copy_mutation_stale_span_and_budget(self):
  self.add_stack();baseline,trial=self.union_trial()
  for bad in [copy(trial),deepcopy(trial)]:self.assertIs(self.bind_union(baseline,bad),baseline)
  trial._pool[0]['id']=-1;self.assertIs(self.bind_union(baseline,trial),baseline)
  baseline,trial=self.union_trial();self.db.execute("UPDATE code_symbols SET end_line=end_line-1 WHERE file_path='LayerSurface.ets' AND symbol='build'")
  self.assertIs(self.bind_union(baseline,trial),baseline)
  self.db.execute("UPDATE code_symbols SET end_line=end_line+1 WHERE file_path='LayerSurface.ets' AND symbol='build'")
  (self.project.root/'LayerSurface.ets').write_text(STACK+'// stale')
  self.assertIs(self.bind_union(baseline,trial),baseline)
 def test_union_large_positive_cannot_be_partially_dropped(self):
  self.add_stack(source=STACK.replace('Summary','x'*7000));baseline,trial=self.union_trial()
  self.assertIs(self.bind_union(baseline,trial),baseline)
