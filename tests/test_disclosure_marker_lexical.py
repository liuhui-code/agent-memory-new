import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.arkts_behavior_markers import extract_arkts_behavior_markers
D=Path(__file__).resolve().parents[1]/'docs/evidence/disclosure-lexical'

class DisclosureMarkerPublic(AgentMemoryTestBase):
 def test_public_summary_noncode_not_disclosure(self):
  p=json.loads((D/'controls.json').read_text())
  with tempfile.TemporaryDirectory()as d:
   root=Path(d)
   for n,s in p['sources'].items():(root/n).write_text(s)
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   rows=json.loads(self.run_memory(root,'list','--type','code-file','--limit','100','--json').stdout)
   actual={r['file_path']:r['summary']for r in rows}
   for f in p['absent']:
    with self.subTest(file=f):self.assertNotIn('disclosurestate',actual[f])
   for f in p['present']:
    with self.subTest(file=f):self.assertIn('disclosurestate',actual[f])

class DisclosureMarkerCompatibility(unittest.TestCase):
 def test_quotes_templates_and_comments(self):
  op="SymbolGlyph('arrow').rotate({ angle: this.opened ? 0 : 180 }); this.opened = !this.opened;"
  for s in ['return "'+op+'";', 'return `'+op+'`;', '/* '+op+' */']:
   with self.subTest(source=s):self.assertNotIn('disclosurestate',extract_arkts_behavior_markers(s))
  self.assertIn('disclosurestate',extract_arkts_behavior_markers(op))
  self.assertIn('disclosurestate',extract_arkts_behavior_markers('const note = `'+op+'`;\n'+op))
 def test_one_fake_operation_cannot_complete_pair(self):
  rotation="SymbolGlyph('arrow').rotate({angle:this.a?0:180});"
  toggle="this.a=!this.a;"
  for source in [rotation+' return "'+toggle+'";', 'const note="'+rotation+'"; '+toggle]:
   with self.subTest(source=source):self.assertNotIn('disclosurestate',extract_arkts_behavior_markers(source))
 def test_cross_owner_legacy_scope_not_strengthened(self):
  source="class Read { m(){ SymbolGlyph('arrow').rotate({angle:this.a?0:180}); }} class Write { m(){this.a=!this.a;} }"
  self.assertIn('disclosurestate',extract_arkts_behavior_markers(source))
 def test_other_markers_and_unknown_equal_legacy(self):
  # A wrapper around mask helper is introduced by the tiny candidate; patch the
  # existing helper module so this test is valid before and after production edit.
  p=json.loads((D/'controls.json').read_text());sources=list(p['sources'].values())
  unknown=["const p=/x/; SymbolGlyph('arrow').rotate({angle:this.a?0:180});this.a=!this.a;", "return `SymbolGlyph('arrow').rotate({angle:this.a?0:180});this.a=!this.a; ${value}`;", "return \"arrow .rotate({angle:this.a?0:180}); this.a=!this.a;"]
  for s in sources+unknown:
   with patch('tools.agent_memory_runtime.ecma_callback_mask.callback_mask_lines',return_value=None):old=extract_arkts_behavior_markers(s)
   now=extract_arkts_behavior_markers(s)
   self.assertEqual([x for x in old if x!='disclosurestate'],[x for x in now if x!='disclosurestate'])
   if s in unknown:self.assertEqual(old,now)
