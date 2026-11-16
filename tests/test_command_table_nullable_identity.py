"""A missing key is not an identity; legacy nonframe rows still have real IDs."""
from copy import deepcopy
import tempfile,unittest
from tests.command_table_test_support import prepare,ordinary,P
from tools.agent_memory_runtime.query_command_table_scope import metadata_frames
from tools.agent_memory_runtime.query_command_table_selection import bind_command_table_context,CommandTableContext
from tools.agent_memory_runtime.storage import connect
Q='Return the UI action-to-method dispatch table.'
VIEW="""@Component
export struct DispatchActionView {
  @Prop caption: string
  @Event dispatch: () => void

  build() {
    Row() {
      Text(this.caption)
      SymbolGlyph($r('sys.symbol.play'))
    }.onClick(() => this.dispatch())
  }
}
"""
class NullableIdentity(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();sources=dict(P['cohorts']['single']['sources']);sources['DispatchActionView.ets']=VIEW
  self.project=prepare(self.tmp.name,sources=sources);self.base,self.compact,self.pool=ordinary(self.project,Q)
 def tearDown(self):self.tmp.cleanup()
 def test_unique_real_ids_with_missing_keys_are_not_aliases(self):
  nulls=[r for r in self.pool if r['kind']=='symbol'and r.get('symbol_key')is None]
  self.assertEqual({r['symbol_type']for r in nulls},{'event','resource'})
  self.assertEqual(len({r['id']for r in nulls}),2)
  frames=metadata_frames(self.project,self.pool);self.assertIsNotNone(frames)
  self.assertEqual(len(frames['frames']),1)
  result=bind_command_table_context(self.project,Q,self.base,self.pool);self.assertIsInstance(result,CommandTableContext)
  self.assertGreater(result._scope['unverified_path_count'],0)
 def test_conflicting_pool_ids_or_nonempty_keys_still_fallback(self):
  callback=next(r for r in self.pool if r.get('signature','')and r['signature'].startswith('callback'))
  legacy=next(r for r in self.pool if r['kind']=='symbol'and r.get('symbol_key')is None)
  cases=[]
  changed=deepcopy(legacy);changed['signature']='invented';cases.append([*self.pool,changed])
  changed=deepcopy(callback);changed['symbol_key']=None;cases.append([changed if r is callback else r for r in self.pool])
  changed=deepcopy(legacy);changed['symbol_key']=callback['symbol_key'];cases.append([changed if r is legacy else r for r in self.pool])
  changed=deepcopy(callback);changed['id']=True;cases.append([changed if r is callback else r for r in self.pool])
  for pool in cases:self.assertIsNone(metadata_frames(self.project,pool))
 def test_database_nonempty_key_alias_conflict_remains_unknown(self):
  callback=next(r for r in self.pool if r.get('signature','')and r['signature'].startswith('callback'))
  legacy=next(r for r in self.pool if r['kind']=='symbol'and r.get('symbol_key')is None)
  with connect(self.project)as db:db.execute('UPDATE code_symbols SET symbol_key=? WHERE id=?',(callback['symbol_key'],legacy['id']))
  self.assertIsNone(metadata_frames(self.project,self.pool))

if __name__=='__main__':unittest.main()
