# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.callable_behavior_hints import callable_behavior_hints
D=Path(__file__).resolve().parents[1]/'docs/evidence/validation-marker-equality'

class ValidationMarkerEqualityTests(AgentMemoryTestBase):
 def test_public_comparison_is_not_a_synthesized_write(self):
  p=json.loads((D/'protocol.json').read_text())
  with tempfile.TemporaryDirectory()as d:
   root=Path(d)
   for f,s in p['sources'].items():(root/f).write_text(s)
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   rows=json.loads(self.run_memory(root,'list','--type','code-symbol','--limit','100','--json').stdout);actual={r['qualified_name']:r for r in rows if r.get('qualified_name')}
   for name in p['statewrite']:self.assertIn('statewrite',actual[name]['method_evidence'].split())
   for name in p['no_statewrite']:
    with self.subTest(name=name):
     row=actual[name];self.assertTrue(row['symbol_key']);self.assertEqual(3,row['end_line']-row['start_line']+1)
     self.assertNotIn('statewrite',row['method_evidence'].split());self.assertIn('stateread',row['method_evidence'].split())

if __name__=='__main__':unittest.main()
