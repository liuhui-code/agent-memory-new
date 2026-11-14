# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from contextlib import nullcontext
from copy import copy,deepcopy
import hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime.query_render_selection import bind_render_context,render_context_view,RenderContext
from tools.agent_memory_runtime.context_compact import compact_context
Q='Return the UI rendering cleanup owner.'
BASE=json.loads((Path(__file__).parents[1]/'docs/evidence/render-expression-witness-design/protocol.json').read_text())['source_controls'][0]['source']
class RenderSelectionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);self.project=SimpleNamespace(root=root,project_id='p');self.path=root/'MessageSurface.ets';self.path.write_text(BASE)
  digest=hashlib.sha256(BASE.encode()).hexdigest();self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
  self.db.execute('CREATE TABLE code_symbols(id INTEGER, project_id TEXT,symbol_key TEXT,file_path TEXT,symbol TEXT,qualified_name TEXT,start_line INTEGER,end_line INTEGER,source_digest TEXT,index_generation INTEGER,symbol_type TEXT,owner_kind TEXT,owner_name TEXT,evidence_class TEXT,semantic_adapter TEXT)')
  for i,name,start,end,typ,owner in [(1,'MessageSurface',2,10,'component',''),(2,'build',4,6,'function','MessageSurface'),(3,'plainBody',7,9,'function','MessageSurface')]:
   self.db.execute('INSERT INTO code_symbols VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,'p',name,'MessageSurface.ets',name,'MessageSurface.'+name if owner else name,start,end,digest,1,typ,'component',owner,'static','arkts-static@1.2'))
  self.db.execute('CREATE TABLE code_files(file_path TEXT,project_id TEXT,source_digest TEXT,index_generation INTEGER)');self.db.execute('INSERT INTO code_files VALUES(?,?,?,?)',('MessageSurface.ets','p',digest,1))
  self.baseline=dict(source_freshness={},project_id='p',project_path=str(root),query=Q,wiki_matches=[],query_handoff={'code_anchors':[],'log_anchors':[],'path_context':{}},edge_matches=[])
  self.trial=deepcopy(self.baseline);self.trial['wiki_matches']=[{'file_path':'MessageSurface.ets'}]
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def bind(self):
  with patch('tools.agent_memory_runtime.query_render_selection.connect',return_value=nullcontext(self.db)):
   return bind_render_context(self.project,Q,self.baseline,self.trial)
 def test_mapping_copy_and_json_are_whole_baseline(self):
  r=self.bind();self.assertIsInstance(r,RenderContext)
  for value in [dict(r),copy(r),deepcopy(r),json.loads(json.dumps(r))]:
   self.assertEqual(value,self.baseline);self.assertIsNone(render_context_view(value)[1])
 def test_mutation_legal_query_and_members_failclosed(self):
  for mutation in [lambda r:r.update(query=Q.replace('Return','Locate')),lambda r:r._view['query_handoff']['code_anchors'].clear(),lambda r:setattr(r,'_receipts',()),lambda r:delattr(r,'_binding')]:
   r=self.bind();mutation(r);self.assertIsNone(render_context_view(r)[1])
 def test_same_snapshot_display_no_reread(self):
  r=self.bind();self.path.write_text('changed after validated snapshot')
  with patch('tools.agent_memory_runtime.context_compact.attach_source_excerpts',side_effect=AssertionError('no late read')),patch('tools.agent_memory_runtime.context_source_recovery.recover_partial_primary',side_effect=AssertionError('no late recovery')):
   out=compact_context(r)
  anchors=out['query_handoff']['code_anchors'];self.assertEqual(len(anchors),1)
  excerpts=anchors[0]['source_excerpts'];self.assertTrue(any('return this.content.replace' in e['content']for e in excerpts))
  self.assertTrue(all(e['source']=='validated_request_snapshot'for e in excerpts));self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
 def test_stale_missing_and_guard_full_fallback(self):
  self.path.write_text(BASE.replace("'<p>'","'<b>'"));self.assertIs(self.bind(),self.baseline);self.path.write_text(BASE)
  self.trial['query_handoff']['path_context']={'activated':True};self.assertIs(self.bind(),self.baseline)
  self.trial['query_handoff']['path_context']={};self.db.execute("UPDATE code_symbols SET source_digest='bad' WHERE symbol='plainBody'");self.assertIs(self.bind(),self.baseline)
 def test_no_positive_full_fallback(self):
  self.path.write_text(BASE.replace('Text(this.plainBody())','Text(this.content)'));self.assertIs(self.bind(),self.baseline)
 def test_default_disabled_and_single_records(self):
  from tools.agent_memory_runtime.query_render_recall import recall_projection
  from tools.agent_memory_runtime.query_results import limited_context
  self.assertIsNone(recall_projection(Q))
  with patch('tools.agent_memory_runtime.query_results._context_pass',side_effect=[self.baseline,self.trial])as call,patch('tools.agent_memory_runtime.query_render_selection.bind_render_context',return_value=self.baseline),patch('tools.agent_memory_runtime.query_results.record_context_use')as record,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
   self.assertIs(limited_context(self.project,Q),self.baseline)
  self.assertEqual(call.call_count,2);self.assertTrue(call.call_args.kwargs['allow_render_recall']);record.assert_called_once();miss.assert_called_once()

 def test_protected_both_contexts_fallback(self):
  for context in (self.baseline,self.trial):
   for field in ['identity_match','graph_neighbor','graph_relation','log_identity_match']:
    context['query_handoff']['code_anchors']=[{'file_path':'Protected.ets',field:True}]
    self.assertIs(self.bind(),self.baseline,field)
    context['query_handoff']['code_anchors']=[]
 def test_success_records_adopted_view_not_empty_baseline(self):
  from tools.agent_memory_runtime.query_results import limited_context
  receipt=self.bind()
  with patch('tools.agent_memory_runtime.query_results._context_pass',side_effect=[self.baseline,self.trial]),patch('tools.agent_memory_runtime.query_render_selection.bind_render_context',return_value=receipt),patch('tools.agent_memory_runtime.query_results.record_context_use')as record,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
   result=limited_context(self.project,Q)
  self.assertIs(result,receipt);record.assert_called_once();miss.assert_called_once()
  self.assertIs(record.call_args.args[1],receipt._view)
  self.assertIs(miss.call_args.args[3],receipt._view)
 def clone_owner(self,name,source=None):
  source=(source or BASE).replace('MessageSurface',name);file=name+'.ets';(self.project.root/file).write_text(source);digest=hashlib.sha256(source.encode()).hexdigest()
  rows=[dict(r)for r in self.db.execute("SELECT * FROM code_symbols WHERE file_path='MessageSurface.ets'")]
  next_id=self.db.execute('SELECT MAX(id) FROM code_symbols').fetchone()[0]+1
  for i,row in enumerate(rows):
   row.update(id=next_id+i,symbol_key=name+'.'+str(i),file_path=file,source_digest=digest)
   for key in ['symbol','qualified_name','owner_name']:row[key]=row[key].replace('MessageSurface',name)
   self.db.execute('INSERT INTO code_symbols VALUES('+','.join('?'for _ in row)+')',list(row.values()))
  self.db.execute('INSERT INTO code_files VALUES(?,?,?,?)',(file,'p',digest,1));self.trial['wiki_matches'].append({'file_path':file})
 def test_two_and_three_positive_owners_all_retained(self):
  for name in ['SecondView','ThirdView']:
   self.clone_owner(name);out=compact_context(self.bind());anchors=out['query_handoff']['code_anchors']
   self.assertEqual({a['file_path']for a in anchors},{r['file_path']for r in self.trial['wiki_matches']})
   self.assertTrue(all(len(a.get('source_excerpts',[]))==2 and all(not e['truncated']for e in a['source_excerpts'])for a in anchors))
 def test_insufficient_complete_snapshot_budget_falls_back(self):
  source=BASE.replace('Text(this.plainBody())',"Text('"+'x'*1700+"');Text(this.plainBody())")
  self.path.write_text(source);digest=hashlib.sha256(source.encode()).hexdigest()
  self.db.execute('UPDATE code_symbols SET source_digest=?',(digest,));self.db.execute('UPDATE code_files SET source_digest=?',(digest,))
  out=compact_context(self.bind());self.assertEqual(out,compact_context(self.baseline))

 def test_facade_enrichment_and_final_accounting(self):
  from tools.agent_memory_runtime.context_facade import ContextFacade
  inactive={'activated':False,'path_candidates':[],'activation_reason':'missing_log_anchor'}
  for active in [False,True]:
   receipt=self.bind();receipt._pending_accounting=True;paths=dict(inactive,activated=active)
   facade=ContextFacade(self.project,lambda p,q,i:receipt,SimpleNamespace(build=lambda q:paths))
   with patch('tools.agent_memory_runtime.context_facade.filter_fresh_path_context',side_effect=lambda p,v,f:(v,f)),patch('tools.agent_memory_runtime.query_results.record_context_use')as record,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
    result=facade.execute(Q)
   record.assert_called_once();miss.assert_called_once()
   if active:
    self.assertNotIsInstance(result,RenderContext);self.assertFalse(miss.call_args.args[3]['query_handoff']['code_anchors'])
   else:
    self.assertIsInstance(result,RenderContext);self.assertTrue(miss.call_args.args[3]['query_handoff']['code_anchors'])
    self.assertTrue(compact_context(result)['query_handoff']['code_anchors'])
 def test_enrichment_unknown_and_copy_no_permission(self):
  from tools.agent_memory_runtime.query_render_selection import enrich_render_context
  inactive={'activated':False,'path_candidates':[]}
  for path,fresh in [(dict(inactive,wrapped_log_evidence=True),{}),(dict(inactive,path_candidates=[{}]),{}),(inactive,{'status':'changed'}),({}, {})]:
   self.assertNotIsInstance(enrich_render_context(self.bind(),Q,path,fresh),RenderContext)
  self.assertNotIsInstance(enrich_render_context(dict(self.bind()),Q,inactive,{}),RenderContext)
  huge=dict(inactive,extra='x'*30000)
  self.assertNotIsInstance(enrich_render_context(self.bind(),Q,huge,{}),RenderContext)

 def test_composition_only_explicitly_defers(self):
  from tools.agent_memory_runtime.context_composition import build_context_facade
  from tools.agent_memory_runtime.query_results import limited_context
  facade=build_context_facade(self.project)
  self.assertEqual(facade.base_context.keywords,{'defer_render_accounting':True})
  receipt=self.bind()
  with patch('tools.agent_memory_runtime.query_results._context_pass',side_effect=[self.baseline,self.trial]),patch('tools.agent_memory_runtime.query_render_selection.bind_render_context',return_value=receipt),patch('tools.agent_memory_runtime.query_results.record_context_use')as record,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
   result=limited_context(self.project,Q,defer_render_accounting=True)
  self.assertIs(result,receipt);self.assertTrue(result._pending_accounting);record.assert_not_called();miss.assert_not_called()
