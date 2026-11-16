from copy import copy,deepcopy
import json,tempfile,unittest
from unittest.mock import patch
from tests.command_table_test_support import prepare,ordinary,Q,P,D
from tools.agent_memory_runtime.storage import connect
from tools.agent_memory_runtime.query_command_table_selection import bind_command_table_context,CommandTableContext,command_table_receipt,compact_command_table,enrich_command_table
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist,valid_anchors
from tools.agent_memory_runtime.context_command_table_transaction import valid_component_anchors,apply_command_table_transaction

class TableSelection(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.project=prepare(self.tmp.name);self.base,self.compact,self.pool=ordinary(self.project)
 def tearDown(self):self.tmp.cleanup()
 def bind(self,pool=None,base=None):return bind_command_table_context(self.project,Q,base or self.base,self.pool if pool is None else pool)
 def test_parent_range_and_atomic_display(self):
  self.assertFalse(any(r.get('kind')=='symbol' and r.get('symbol')=='SyncMenu'for r in self.pool))
  r=self.bind();self.assertIsInstance(r,CommandTableContext);out=compact_command_table(r,self.compact)
  self.assertIsNot(out,self.compact);self.assertEqual(restore_whitelist(out,self.compact),self.compact)
  a=out['query_handoff']['code_anchors'][0];self.assertEqual((a['symbol'],a['symbol_type']),('SyncMenu','component'))
  self.assertEqual(a['source_excerpts'][0]['content'],'\n'.join(P['cohorts']['single']['sources']['SyncMenu.ets'].splitlines()[1:]))
  self.assertFalse(valid_anchors(r._anchors));self.assertTrue(valid_component_anchors(r._anchors))
 def test_each_callback_build_and_file_required(self):
  for row in self.pool:
   if row.get('file_path')=='SyncMenu.ets'and row.get('kind')in {'file','symbol'}:
    self.assertIs(self.bind([r for r in self.pool if r is not row]),self.base,str(row.get('symbol')))
 def test_pool_alias_id_and_cross_file_conflicts(self):
  for row in [r for r in self.pool if r.get('file_path')=='SyncMenu.ets']:
   for key,value in [('file_path','Alien.ets'),('index_generation',99),('source_digest','bad'),('owner_name','Alien')]:
    if key not in row:continue
    changed=deepcopy(row);changed[key]=value
    self.assertIs(self.bind([*self.pool,changed]),self.base,(row.get('kind'),key))
 def test_pool_boolean_generation_is_not_typed_integer_identity(self):
  pool=deepcopy(self.pool)
  for row in pool:
   if row.get('file_path')=='SyncMenu.ets':row['index_generation']=True
  self.assertIs(self.bind(pool),self.base)
  receipt=self.bind();fresh=deepcopy(self.base['source_freshness']);fresh['generation']=True
  self.assertNotIsInstance(enrich_command_table(receipt,Q,self.base['query_handoff']['path_context'],fresh),CommandTableContext)
 def test_owner_identity_and_callback_range_corruption(self):
  for statement in ["UPDATE code_symbols SET qualified_name='Wrong' WHERE symbol='SyncMenu'", "UPDATE code_symbols SET owner_kind='class' WHERE symbol='run'", "UPDATE code_symbols SET start_line=12 WHERE symbol='run' AND start_line=6"]:
   with connect(self.project)as c:
    rows=[dict(r)for r in c.execute('SELECT * FROM code_symbols')];c.execute(statement)
   self.assertIs(self.bind(),self.base,statement)
   with connect(self.project)as c:
    for row in rows:c.execute('UPDATE code_symbols SET '+','.join(k+'=?'for k in row if k!='id')+' WHERE id=?',[*(v for k,v in row.items()if k!='id'),row['id']])
 def test_snapshot_mutation_copy_stale(self):
  r=self.bind();self.assertIsInstance(r,CommandTableContext)
  for value in [dict(r),copy(r),deepcopy(r),json.loads(json.dumps(r))]:self.assertIsNone(command_table_receipt(value))
  r._anchors[0]['symbol']='Wrong';self.assertIsNone(command_table_receipt(r))
  r=self.bind();path=self.project.root/'SyncMenu.ets';path.write_text(path.read_text()+'\n');self.assertIsNone(command_table_receipt(r));self.assertIs(self.bind(),self.base)
 def test_outside_frame_source_is_explicitly_unverified(self):
  r=self.bind();self.assertIsInstance(r,CommandTableContext)
  path=self.project.root/'SyncWorker.ets';path.write_text('const opaque = `${unknown()}`;')
  self.assertIsNotNone(command_table_receipt(r))
  self.assertGreater(r._scope['unverified_path_count'],0)
  self.assertEqual(r._scope['certification_scope'],'non_exhaustive_recalled_component_frames')
 def test_guard_and_budget_full_fallback(self):
  for field in ['identity_match','log_identity_match','graph_neighbor','graph_relation']:
   base=deepcopy(self.base);base['query_handoff']['code_anchors'][0][field]=True
   self.assertIs(self.bind(base=base),base)
  r=self.bind();huge=deepcopy(self.compact);huge['query_handoff']['unrelated']='x'*8000
  self.assertIs(compact_command_table(r,huge),huge)
  invalid=deepcopy(r._anchors);invalid[0]['symbol_type']='function'
  self.assertFalse(valid_component_anchors(invalid));self.assertIs(apply_command_table_transaction(self.compact,invalid),self.compact)
 def test_facade_paths_and_receipt_binding(self):
  r=self.bind();path=deepcopy(self.base['query_handoff']['path_context']);fresh=self.base['source_freshness']
  self.assertIsInstance(enrich_command_table(r,Q,path,fresh),CommandTableContext)
  path['activated']=True;self.assertNotIsInstance(enrich_command_table(r,Q,path,fresh),CommandTableContext)
 def test_public_facade_accounts_once_and_direct_mode_not_deferred(self):
  from tools.agent_memory_runtime.context_composition import build_context_facade
  from tools.agent_memory_runtime.query_results import limited_context
  from tools.agent_memory_runtime.context_compact import compact_context
  for public in (True,False):
   with patch('tools.agent_memory_runtime.query_results.record_context_use')as use,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
    result=build_context_facade(self.project).execute(Q)if public else limited_context(self.project,Q)
   use.assert_called_once();miss.assert_called_once();self.assertIsInstance(result,CommandTableContext)
   if public:self.assertEqual(compact_context(result)['query_handoff']['code_anchors'][0]['symbol'],'SyncMenu')
 def test_two_tables_any_missing_member_or_changed_source_falls_back(self):
  with tempfile.TemporaryDirectory()as t:
   project=prepare(t,'two');base,compact,pool=ordinary(project);r=bind_command_table_context(project,Q,base,pool)
   self.assertIsInstance(r,CommandTableContext);out=compact_command_table(r,compact);self.assertEqual(len(out['query_handoff']['code_anchors']),2)
   incomplete=[x for x in pool if not(x.get('file_path')=='SecondMenu.ets'and x.get('symbol')=='run'and x.get('start_line')==12)]
   self.assertIs(bind_command_table_context(project,Q,base,incomplete),base)
   (project.root/'SecondMenu.ets').write_text('changed');self.assertIsNone(command_table_receipt(r));self.assertIs(bind_command_table_context(project,Q,base,pool),base)

if __name__=='__main__':unittest.main()
