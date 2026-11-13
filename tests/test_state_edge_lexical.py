# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
D=Path(__file__).resolve().parents[1]/'docs/evidence/state-edge-lexical'

class StateEdgeLexicalTests(AgentMemoryTestBase):
 def test_public_state_edges_exclude_noncode_but_keep_real_identity(self):
  p=json.loads((D/'protocol.json').read_text())
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'CounterBoard.ets').write_text(p['source'])
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   symbols=json.loads(self.run_memory(root,'list','--type','code-symbol','--limit','300','--json').stdout)
   edges=json.loads(self.run_memory(root,'list','--type','memory-edge','--limit','300','--json').stdout)
   byid={r['id']:r['qualified_name']for r in symbols}
   actual={(byid[e['source_id']],e['relation'],byid[e['target_id']])for e in edges if e['source_type']=='code_symbol' and e['target_type']=='code_symbol' and e['relation']in {'reads_state','writes_state'}}
   for edge in p['expected_edges']:self.assertIn(tuple(edge),actual)
   for owner in ['CounterBoard','OtherBoard']:
    for s,r,t in actual:
     if s.startswith(owner+'.'):self.assertEqual(owner+'.count',t)
   for name in p['expected_no_state_edges']:
    with self.subTest(name=name):self.assertFalse(any(s==name for s,r,t in actual))
   # These existing unsupported operations remain legacy, not absence claims.
   for triple in [('CounterBoard.nestedUnknown','writes_state','CounterBoard.count'),('CounterBoard.interpolationUnknown','reads_state','CounterBoard.count'),('CounterBoard.slashUnknown','reads_state','CounterBoard.count')]:self.assertIn(triple,actual)

if __name__=='__main__':unittest.main()
