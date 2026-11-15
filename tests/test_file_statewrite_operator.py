import json,tempfile,unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.arkts_behavior_markers import extract_arkts_behavior_markers,STATE_WRITE_RE
D=Path(__file__).resolve().parents[1]/'docs/evidence/statewrite-file-operator'

class FileStatewriteOperatorPublic(AgentMemoryTestBase):
 def test_comparison_only_file_is_not_marked_write(self):
  p=json.loads((D/'protocol.json').read_text())
  with tempfile.TemporaryDirectory()as d:
   root=Path(d)
   for n,s in p['sources'].items():(root/n).write_text(s)
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   rows=json.loads(self.run_memory(root,'list','--type','code-file','--limit','100','--json').stdout);rows={r['file_path']:r for r in rows}
   for n in p['absent']:
    with self.subTest(file=n):self.assertNotIn('statewrite',rows[n]['summary'])
   for n in p['present']:
    with self.subTest(file=n):self.assertIn('statewrite',rows[n]['summary'])

class FileStatewriteOperatorBoundaries(unittest.TestCase):
 def test_comparison_and_arrow_token_boundaries(self):
  # => after a member is a token-boundary control, not a valid-program fixture.
  for op in ['==','===','!=','!==','<=','>=','=>']:
   for space in ['', ' ', '\n']:
    with self.subTest(op=op,space=space):self.assertNotIn('statewrite',extract_arkts_behavior_markers('return this.count'+space+op+'2;'))
 def test_original_write_family_and_arrow_value(self):
  for expr in ['this.count=2','this.count+=2','this.count-=2','this.count++','this.count--','this.callback = () => run()','if(this.count===2){this.count=3;}']:
   with self.subTest(expr=expr):self.assertIn('statewrite',extract_arkts_behavior_markers(expr))
 def test_unknown_raw_text_uses_corrected_operator_without_lexical_proof(self):
  for expr in ['const p=/x/;return this.count===2;', 'return `this.count==2 ${value}`;']:
   self.assertNotIn('statewrite',extract_arkts_behavior_markers(expr))
  self.assertIn('statewrite',extract_arkts_behavior_markers('return /this.count=2/;'))
 def test_ascii_domain_and_operator_family_not_expanded(self):
  for field in ['café','a变量']:
   self.assertNotIn('statewrite',extract_arkts_behavior_markers('this.'+field+'=2;'))
  for op in ['*=','/=','%=','**=','&&=','||=','??=']:
   self.assertNotIn('statewrite',extract_arkts_behavior_markers('this.count'+op+'2;'))
 def test_shared_statehandoff_regex_stays_legacy(self):
  self.assertIsNotNone(STATE_WRITE_RE.search('this.count===2;'))
