# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,re,tempfile,unittest
from tools.agent_memory_runtime.ecma_state_access import state_accesses
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

class StateAccessFallbackTests(unittest.TestCase):
 def test_unknown_inputs_keep_complete_legacy_result(self):
  sources = [
   'm() { const r = /"/; this.count = 1; return this.count }',
   'm() { return this.count / 2 }',
   'm() { return `${this.count}` }',
   'm() { return `${ok ? `this.count=1` : ""}` }',
   'm() { const text = "unterminated; this.count = 1',
   'm() { /* unterminated this.count = 1',
  ]
  for source in sources:
   expected=[]
   if re.search(r"\bthis\.count\s*(?:=|\+=|-=|\+\+|--)",source):expected.append(('count','writes_state',0.95,'state assignment'))
   if re.search(r"\bthis\.count\b(?!\s*(?:=|\+=|-=|\+\+|--))",source):expected.append(('count','reads_state',0.9,'state read'))
   with self.subTest(source=source):self.assertEqual(expected,list(state_accesses(source,['count'])))
 def test_mask_preserves_real_suffix_and_plain_name_boundary(self):
  source = 'm() { /* this.count=5\n this.count */\n const s = "this.count"; const t = `this.count=8`; this.counter = 7; this.count = 2; return this.count }'
  self.assertEqual([('count','writes_state',0.95,'state assignment'),('count','reads_state',0.9,'state read')],list(state_accesses(source,['count'])))
  self.assertEqual([],list(state_accesses('m() { this.counter = 2; return this.counter }',['count'])))

if __name__=='__main__':unittest.main()
