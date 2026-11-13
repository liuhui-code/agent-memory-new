# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
D=Path(__file__).resolve().parents[1]/'docs/evidence/validation-mechanism'

class ValidationMarkerLexicalTests(AgentMemoryTestBase):
 def test_public_synthetic_markers_require_executable_lexical_text(self):
  p=json.loads((D/'supported-protocol.json').read_text())
  with tempfile.TemporaryDirectory()as d:
   root=Path(d)
   for f,s in p['sources'].items():(root/f).write_text(s)
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   rows=json.loads(self.run_memory(root,'list','--type','code-symbol','--limit','100','--json').stdout)
   actual={r['qualified_name']:r for r in rows if r.get('qualified_name')}
   ranges={'literal':(3,5),'comment':(6,9),'template':(10,12),'actual':(13,16),'mixed':(17,21),'interpolationUnknown':(22,24)}
   for name,span in ranges.items():
    row=actual['ValidationSamples.'+name];self.assertEqual(span,(row['start_line'],row['end_line']));self.assertTrue(row['symbol_key']);self.assertEqual(64,len(row['source_digest']))
   for name in p['real_markers']:
    self.assertTrue(set(p['synthetic_markers'])<=set(actual[name]['method_evidence'].split()))
   self.assertIn('statewrite',actual['ValidationSamples.interpolationUnknown']['method_evidence'].split())
   for name in p['no_markers']:
    with self.subTest(name=name):self.assertFalse(set(p['synthetic_markers'])&set(actual[name]['method_evidence'].split()))

if __name__=='__main__':unittest.main()
