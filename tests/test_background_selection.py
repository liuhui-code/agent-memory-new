# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from contextlib import nullcontext
from copy import copy,deepcopy
import hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from test_background_source import SOURCE,Q
from tools.agent_memory_runtime.query_render_selection import (bind_render_context,render_context_view,RenderContext,retain_background_candidates)
from tools.agent_memory_runtime.context_compact import compact_context
class BackgroundSelectionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);self.project=SimpleNamespace(root=root,project_id='p');self.path=root/'AmountSurface.ets';self.path.write_text(SOURCE)
  digest=hashlib.sha256(SOURCE.encode()).hexdigest();self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
  self.db.execute('CREATE TABLE code_symbols(id INTEGER,project_id TEXT,symbol_key TEXT,file_path TEXT,symbol TEXT,qualified_name TEXT,start_line INTEGER,end_line INTEGER,source_digest TEXT,index_generation INTEGER,symbol_type TEXT,owner_kind TEXT,owner_name TEXT,evidence_class TEXT,semantic_adapter TEXT)')
  for i,name,start,end,typ,owner in [(1,'AmountSurface',2,11,'component',''),(2,'build',3,10,'function','AmountSurface')]:
   self.db.execute('INSERT INTO code_symbols VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,'p',name,'AmountSurface.ets',name,'AmountSurface.'+name if owner else name,start,end,digest,1,typ,'component',owner,'static','arkts-static@1.2'))
  self.db.execute('CREATE TABLE code_files(file_path TEXT,project_id TEXT,source_digest TEXT,index_generation INTEGER)');self.db.execute('INSERT INTO code_files VALUES(?,?,?,?)',('AmountSurface.ets','p',digest,1))
  self.pool=[dict(r,kind='symbol',method_evidence='backgroundcolor')for r in self.db.execute("SELECT * FROM code_symbols WHERE symbol='build'")]
  self.baseline=dict(source_freshness={},project_id='p',project_path=str(root),query=Q,wiki_matches=[],query_handoff={'code_anchors':[],'log_anchors':[],'path_context':{}},edge_matches=[])
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def trial(self):return retain_background_candidates(Q,deepcopy(self.baseline),self.pool)
 def bind(self,trial=None):
  with patch('tools.agent_memory_runtime.query_render_selection.connect',return_value=nullcontext(self.db)):
   return bind_render_context(self.project,Q,self.baseline,trial if trial is not None else self.trial())
 def test_retained_before_focus_and_full_snapshot(self):
  r=self.bind();self.assertIsInstance(r,RenderContext)
  out=compact_context(r);anchors=out['query_handoff']['code_anchors'];self.assertEqual(len(anchors),1)
  self.assertEqual(anchors[0]['file_path'],'AmountSurface.ets');self.assertFalse(anchors[0]['source_excerpts'][0]['truncated']);self.assertEqual(anchors[0]['source_excerpts'][0]['content'],'\n'.join(SOURCE.splitlines()[2:10]));self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
  self.assertEqual(out['query_handoff']['callable_evidence']['certainty'],'uncertain')
 def test_trial_copy_mutation_or_foreign_query_has_no_permission(self):
  for mode in ['copy','deepcopy','dict','query','pool','row_id']:
   t=self.trial()
   if mode in ['copy','deepcopy','dict']:t={'copy':copy,'deepcopy':deepcopy,'dict':dict}[mode](t)
   elif mode=='query':t['query']='other'
   elif mode=='pool':t._pool[0]['source_digest']='0'*64
   else:self.db.execute('UPDATE code_symbols SET id=99 WHERE id=2')
   self.assertIs(self.bind(t),self.baseline,mode)
 def test_missing_pool_symbol_digest_generation_and_range_failclosed(self):
  for column,value in [('source_digest','0'*64),('index_generation',2),('end_line',9),('symbol_key','other')]:
   self.db.execute('SAVEPOINT control');self.db.execute(f'UPDATE code_symbols SET {column}=? WHERE id=2',(value,));self.assertIs(self.bind(),self.baseline,column);self.db.execute('ROLLBACK TO control')
 def test_protected_path_and_identities(self):
  for field in ['identity_match','graph_neighbor','graph_relation','log_identity_match']:
   self.baseline['query_handoff']['code_anchors']=[{'file_path':'Other.ets',field:True}];self.assertIs(self.bind(),self.baseline)
  self.baseline['query_handoff']['code_anchors']=[];self.baseline['query_handoff']['path_context']={'activated':True};self.assertIs(self.bind(),self.baseline)
 def test_stale_and_unknown(self):
  for source in [SOURCE.replace('Color.White','Color.Black'),SOURCE.replace('.backgroundColor(Color.White)','')]:
   self.path.write_text(source);self.assertIs(self.bind(),self.baseline)
 def test_whole_fallback_when_complete_excerpt_does_not_fit(self):
  source=SOURCE.replace("'Amount'","'"+'x'*4000+"'");self.path.write_text(source);digest=hashlib.sha256(source.encode()).hexdigest()
  self.db.execute('UPDATE code_symbols SET source_digest=?',(digest,));self.db.execute('UPDATE code_files SET source_digest=?',(digest,));self.pool[0]['source_digest']=digest
  self.assertIs(self.bind(),self.baseline)
 def test_multiple_positive_owners_are_not_claimed_exclusive(self):
  name='OtherSurface';source=SOURCE.replace('AmountSurface',name);(self.project.root/(name+'.ets')).write_text(source);digest=hashlib.sha256(source.encode()).hexdigest()
  for row in [dict(r)for r in self.db.execute('SELECT * FROM code_symbols')]:
   row.update(id=row['id']+10,file_path=name+'.ets',source_digest=digest,symbol_key=name+row['symbol_key'])
   for key in ['symbol','qualified_name','owner_name']:row[key]=row[key].replace('AmountSurface',name)
   self.db.execute('INSERT INTO code_symbols VALUES('+','.join('?'for _ in row)+')',list(row.values()))
   if row['symbol']=='build':self.pool.append(dict(row,kind='symbol',method_evidence='backgroundcolor'))
  self.db.execute('INSERT INTO code_files VALUES(?,?,?,?)',(name+'.ets','p',digest,1))
  r=self.bind();self.assertIsInstance(r,RenderContext);self.assertEqual({a['file_path']for a in compact_context(r)['query_handoff']['code_anchors']},{'AmountSurface.ets',name+'.ets'})
 def test_after_binding_no_late_source_read_and_serialization_loses_authority(self):
  r=self.bind();self.path.write_text('changed')
  with patch('tools.agent_memory_runtime.context_compact.attach_source_excerpts',side_effect=AssertionError('late source read')):self.assertTrue(compact_context(r)['query_handoff']['code_anchors'])
  for result in [dict(r),copy(r),deepcopy(r),json.loads(json.dumps(r))]:self.assertIsNone(render_context_view(result)[1])
