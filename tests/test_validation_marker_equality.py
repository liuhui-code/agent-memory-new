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

class ValidationWriteOperatorTests(unittest.TestCase):
 def hints(self,source,path='Source.ts'):
  return callable_behavior_hints(SimpleNamespace(name='sample',file_path=path),source)
 def test_existing_read_comparisons_and_arrow_are_not_assignment(self):
  for op in ['==','===','!=','!==','<=','>=','=>']:
   for space in ['', ' ', '\n']:
    with self.subTest(op=op,space=space):self.assertNotIn('statewrite',self.hints('sample(){return this.count'+space+op+'2}'))
 def test_true_assignment_arrow_value_and_mixed_operation_survive(self):
  for source in ['sample(){ this.callback = () => run() }','sample(){if(this.count===2){this.count=3}}','sample(){this.count += 1}','sample(){this.count--}']:
   self.assertIn('statewrite',self.hints(source))
 def test_unknown_lexical_source_still_uses_operator_boundary_without_proof(self):
  self.assertNotIn("statewrite",self.hints('sample(){const p=/"/; return this.count===2}'))
  self.assertIn("statewrite",self.hints('sample(){const p=/"/; this.count=2}'))
  self.assertIn("statewrite",self.hints("sample(){return /this.count=2/}"))
 def test_ascii_field_recognition_is_not_expanded(self):
  for field in ["café","a变量"]:
   self.assertNotIn("statewrite",self.hints("sample(){this."+field+"=2}"))
 def test_unvalidated_languages_keep_their_old_comparison_hint(self):
  for suffix in ['.py','.cpp','.java','.js','']:
   self.assertIn('statewrite',self.hints('sample(){return this.count==2}','Other'+suffix))

if __name__=='__main__':unittest.main()
