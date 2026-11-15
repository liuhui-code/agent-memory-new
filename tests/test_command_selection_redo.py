# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from contextlib import nullcontext
from copy import copy,deepcopy
import hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime.query_command_selection import bind_command_context,command_context_view,CommandContext
from tools.agent_memory_runtime.context_compact import compact_context
Q='Locate the menu command binding owner for Stop sync.'
BASE=json.loads((Path(__file__).parents[1]/'docs/evidence/command-binding-redo-20261115/protocol-v2.json').read_text())['sources']['SyncMenu.ets']
class CommandSelectionRedo(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);self.project=SimpleNamespace(root=root,project_id='p');self.path=root/'SyncMenu.ets';self.path.write_text(BASE)
  digest=hashlib.sha256(BASE.encode()).hexdigest();self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
  self.db.execute('CREATE TABLE code_symbols(id INTEGER, project_id TEXT,symbol_key TEXT,file_path TEXT,symbol TEXT,qualified_name TEXT,start_line INTEGER,end_line INTEGER,source_digest TEXT,index_generation INTEGER,symbol_type TEXT,owner_kind TEXT,owner_name TEXT,evidence_class TEXT,semantic_adapter TEXT)')
  for i,name,start,end,typ,owner in [(1,'SyncMenu',2,24,'component',''),(2,'run',12,14,'function','SyncMenu')]:
   self.db.execute('INSERT INTO code_symbols VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,'p',name,'SyncMenu.ets',name,'SyncMenu.'+name+'@'+str(start) if owner else name,start,end,digest,1,typ,'component',owner,'static','arkts-static@1.2'))
  self.db.execute('CREATE TABLE code_files(file_path TEXT,project_id TEXT,source_digest TEXT,index_generation INTEGER)');self.db.execute('INSERT INTO code_files VALUES(?,?,?,?)',('SyncMenu.ets','p',digest,1))
  self.baseline=dict(source_freshness={},project_id='p',project_path=str(root),query=Q,wiki_matches=[],query_handoff={'code_anchors':[],'log_anchors':[],'path_context':{}},edge_matches=[])
  self.trial=deepcopy(self.baseline);self.trial['wiki_matches']=[{'file_path':'SyncMenu.ets'}]
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def bind(self):
  with patch('tools.agent_memory_runtime.query_command_selection.connect',return_value=nullcontext(self.db)):
   return bind_command_context(self.project,Q,self.baseline,self.trial)
 def test_mapping_copy_and_json_are_whole_baseline(self):
  r=self.bind();self.assertIsInstance(r,CommandContext)
  for value in [dict(r),copy(r),deepcopy(r),json.loads(json.dumps(r))]:
   self.assertEqual(value,self.baseline);self.assertIsNone(command_context_view(value)[1])
 def test_mutation_legal_query_and_members_failclosed(self):
  for mutation in [lambda r:r.update(query=Q.replace('Stop sync','Restart sync')),lambda r:r._view['query_handoff']['code_anchors'].clear(),lambda r:setattr(r,'_receipts',()),lambda r:delattr(r,'_binding')]:
   r=self.bind();mutation(r);self.assertIsNone(command_context_view(r)[1])
 def test_same_snapshot_display_no_reread(self):
  r=self.bind();self.path.write_text('changed after validated snapshot')
  with patch('tools.agent_memory_runtime.context_compact.attach_source_excerpts',side_effect=AssertionError('no late read')),patch('tools.agent_memory_runtime.context_source_recovery.recover_partial_primary',side_effect=AssertionError('no late recovery')):
   out=compact_context(r)
  anchors=out['query_handoff']['code_anchors'];self.assertEqual(len(anchors),1)
  excerpts=anchors[0]['source_excerpts'];self.assertTrue(any("caption: 'Stop sync'" in e['content']for e in excerpts))
  self.assertTrue(all(e['source']=='validated_request_snapshot'for e in excerpts));self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
 def test_stale_missing_and_guard_full_fallback(self):
  self.path.write_text(BASE.replace('Stop sync','Start sync'));self.assertIs(self.bind(),self.baseline);self.path.write_text(BASE)
  self.trial['query_handoff']['path_context']={'activated':True};self.assertIs(self.bind(),self.baseline)
  self.trial['query_handoff']['path_context']={};self.db.execute("UPDATE code_symbols SET source_digest='bad' WHERE symbol='run'");self.assertIs(self.bind(),self.baseline)
 def test_no_positive_full_fallback(self):
  self.path.write_text(BASE.replace("caption: 'Stop sync'","caption: 'Unknown sync'"));self.assertIs(self.bind(),self.baseline)

 def test_protected_both_contexts_fallback(self):
  for context in (self.baseline,self.trial):
   for field in ['identity_match','graph_neighbor','graph_relation','log_identity_match']:
    context['query_handoff']['code_anchors']=[{'file_path':'Protected.ets',field:True}]
    self.assertIs(self.bind(),self.baseline,field)
    context['query_handoff']['code_anchors']=[]

 def clone_owner(self,name,source=None):
  source=(source or BASE).replace('SyncMenu',name);file=name+'.ets';(self.project.root/file).write_text(source);digest=hashlib.sha256(source.encode()).hexdigest()
  rows=[dict(r)for r in self.db.execute("SELECT * FROM code_symbols WHERE file_path='SyncMenu.ets'")]
  next_id=self.db.execute('SELECT MAX(id) FROM code_symbols').fetchone()[0]+1
  for i,row in enumerate(rows):
   row.update(id=next_id+i,symbol_key=name+'.'+str(i),file_path=file,source_digest=digest)
   for key in ['symbol','qualified_name','owner_name']:row[key]=row[key].replace('SyncMenu',name)
   self.db.execute('INSERT INTO code_symbols VALUES('+','.join('?'for _ in row)+')',list(row.values()))
  self.db.execute('INSERT INTO code_files VALUES(?,?,?,?)',(file,'p',digest,1));self.trial['wiki_matches'].append({'file_path':file})

 def test_insufficient_complete_snapshot_budget_falls_back(self):
  source=BASE.replace('    Column() {','    /*'+'x'*1700+'*/ Column() {')
  from tools.agent_memory_runtime.query_command_source import command_binding
  self.assertIsNotNone(command_binding(source,'stop sync'))
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
    self.assertNotIsInstance(result,CommandContext);self.assertFalse(miss.call_args.args[3]['query_handoff']['code_anchors'])
   else:
    self.assertIsInstance(result,CommandContext);self.assertTrue(miss.call_args.args[3]['query_handoff']['code_anchors'])
    self.assertTrue(compact_context(result)['query_handoff']['code_anchors'])
 def test_enrichment_unknown_and_copy_no_permission(self):
  from tools.agent_memory_runtime.query_command_selection import enrich_command_context
  inactive={'activated':False,'path_candidates':[]}
  for path,fresh in [(dict(inactive,wrapped_log_evidence=True),{}),(dict(inactive,path_candidates=[{}]),{}),(inactive,{'status':'changed'}),({}, {})]:
   self.assertNotIsInstance(enrich_command_context(self.bind(),Q,path,fresh),CommandContext)
  self.assertNotIsInstance(enrich_command_context(dict(self.bind()),Q,inactive,{}),CommandContext)
  huge=dict(inactive,extra='x'*30000)
  self.assertNotIsInstance(enrich_command_context(self.bind(),Q,huge,{}),CommandContext)


 def test_competing_matching_owner_full_fallback(self):
  self.clone_owner('SecondMenu');self.assertIs(self.bind(),self.baseline)
 def test_missing_and_duplicate_callback_row_full_fallback(self):
  self.db.execute("UPDATE code_symbols SET qualified_name='Wrong.run@12' WHERE symbol='run'");self.assertIs(self.bind(),self.baseline)
 def test_serving_accounting_is_single_and_adopted(self):
  from tools.agent_memory_runtime.query_results import limited_context
  receipt=self.bind()
  with patch('tools.agent_memory_runtime.query_results._context_pass',return_value=self.baseline)as call,patch('tools.agent_memory_runtime.query_command_selection.bind_command_context',return_value=receipt),patch('tools.agent_memory_runtime.query_results.record_context_use')as record,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
   result=limited_context(self.project,Q)
  call.assert_called_once();record.assert_called_once();miss.assert_called_once();self.assertIs(record.call_args.args[1],receipt._view)

 def test_unrecognized_array_competitor_preserves_whole_fallback(self):
  for source in [BASE.replace("'Stop sync'","`Stop sync`"),BASE.replace("'Stop sync'","'Stop '+ 'sync'"),BASE.replace("'Stop sync'", "'Stop \\u0073ync'")]:
   # Fresh isolated table for each variant is not necessary: update same extra
   # file; unsupported parser must preserve baseline before identity use.
   name='OpaqueMenu.ets';(self.project.root/name).write_text(source.replace('SyncMenu','OpaqueMenu'))
   self.trial['wiki_matches']=[{'file_path':'SyncMenu.ets'},{'file_path':name}]
   self.assertIs(self.bind(),self.baseline)
