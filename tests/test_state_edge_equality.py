# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.ecma_state_access import state_accesses
D=Path(__file__).resolve().parents[1]/'docs/evidence/state-edge-equality'

class StateEqualityTests(AgentMemoryTestBase):
 def test_public_equality_is_read_not_assignment(self):
  p=json.loads((D/'protocol.json').read_text())
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'EqualityBoard.ets').write_text(p['source'])
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   syms=json.loads(self.run_memory(root,'list','--type','code-symbol','--limit','100','--json').stdout);byid={s['id']:s['qualified_name']for s in syms}
   edges=json.loads(self.run_memory(root,'list','--type','memory-edge','--limit','100','--json').stdout)
   actual={(byid[e['source_id']],e['relation'],byid[e['target_id']])for e in edges if e['source_type']=='code_symbol'and e['target_type']=='code_symbol'and e['relation']in ['reads_state','writes_state']}
   for name in p['read_only']:
    with self.subTest(name=name):self.assertEqual({(name,'reads_state','EqualityBoard.count')},{e for e in actual if e[0]==name})
   for name in p['write_only']:
    with self.subTest(name=name):self.assertEqual({(name,'writes_state','EqualityBoard.count')},{e for e in actual if e[0]==name})

class StateEqualityOperatorTests(unittest.TestCase):
 def test_whitespace_and_mixed_read_write(self):
  for op in ['==','===','!=','!==','<=']:
   for space in ['', ' ', '\n']:
    with self.subTest(op=op,space=space):
     self.assertEqual([('count','reads_state',0.9,'state read')],list(state_accesses('m() { return this.count'+space+op+'2 }',['count'])))
  for source in ['m(){ if(this.count===2){this.count=3} }','m(){ this.count=3; return this.count==2 }']:
   self.assertEqual({'reads_state','writes_state'},{r[1]for r in state_accesses(source,['count'])})

if __name__=='__main__':unittest.main()
