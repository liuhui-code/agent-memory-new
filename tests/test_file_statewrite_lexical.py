import json,tempfile,unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.arkts_behavior_markers import extract_arkts_behavior_markers
D=Path(__file__).resolve().parents[1]/'docs/evidence/statewrite-file-lexical'

class FileStatewritePublic(AgentMemoryTestBase):
 def test_known_noncode_public_file_summary(self):
  p=json.loads((D/'protocol.json').read_text())
  with tempfile.TemporaryDirectory()as d:
   root=Path(d)
   for n,s in p['sources'].items():(root/n).write_text(s)
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   rows=json.loads(self.run_memory(root,'list','--type','code-file','--limit','100','--json').stdout);rows={r['file_path']:r for r in rows}
   for n in p['absent']:
    with self.subTest(file=n):self.assertNotIn('statewrite',rows[n]['summary'])
   # Equality was intentionally legacy-positive only at the lexical stage.
   # The independently frozen file operator repair now removes that false hint.
   self.assertNotIn('statewrite',rows['Equality.ets']['summary'])
   for n in [name for name in p['present'] if name != 'Equality.ets']:
    with self.subTest(file=n):self.assertIn('statewrite',rows[n]['summary'])

class FileStatewriteBoundaries(unittest.TestCase):
 def test_known_literals_and_real_writes(self):
  for s in ['return "this.count = 3";','return `this.count += 2`;','// this.count++;','/* this.count = 3 */','return "say \\"this.count = 2\\"";']:
   with self.subTest(source=s):self.assertNotIn('statewrite',extract_arkts_behavior_markers(s))
  for s in ["this.name = 'ready';",'this.count+=1;', 'const note=`this.fake=3`;this.count=2;',"class A {m(){this.count=2;}} class B {m(){this.count=3;}}"]:
   with self.subTest(source=s):self.assertIn('statewrite',extract_arkts_behavior_markers(s))
 def test_unknown_lexical_assignment_keeps_legacy(self):
  for s in ['return `this.count=2 ${value}`;', 'const x=/a/; return "this.count=2";', 'return "this.count=2;']:
   with self.subTest(source=s):self.assertIn('statewrite',extract_arkts_behavior_markers(s))
 def test_original_marker_contract_is_not_broadened(self):
  self.assertNotIn('statewrite',extract_arkts_behavior_markers('const count=2;'))
  self.assertNotIn('statewrite',extract_arkts_behavior_markers('this.count;'))
