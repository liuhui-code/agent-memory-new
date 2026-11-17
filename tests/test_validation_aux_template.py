# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Frozen finite auxiliary template controls; component-only, never public CLI."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools'))
from agent_memory_runtime.validation_field_source import parse_validation_field_file
CONTROLS=ROOT/'docs/evidence/validation13-template-prerequisite/SOURCE-CONTROLS-DRAFT.json'
class FrozenTemplateControls(unittest.TestCase):
 def test_frozen_35(self):
  data=json.loads(CONTROLS.read_text());self.assertEqual(len(data['cases']),35)
  for case in data['cases']:
   with self.subTest(id=case['id']):
    self.assertEqual(hashlib.sha256(case['source'].encode()).hexdigest(),case['source_sha256'])
    self.assertEqual(parse_validation_field_file(case['source']),case['expected'])
class TemplateLexicalRegression(unittest.TestCase):
 def setUp(self):
  cases=json.loads(CONTROLS.read_text())['cases']
  self.base=next(c['source'] for c in cases if c['id']=='parameter-template')
  self.expected=next(c['expected'] for c in cases if c['id']=='parameter-template')
  self.literal='`Account draft dispatched ${value}`'
 def test_ordinary_token_equivalence(self):
  from agent_memory_runtime.ui_divider_source import tokenize
  from agent_memory_runtime.validation_field_lexical import tokenize_validation
  variants=[self.base.replace(self.literal,"'ordinary'"),self.base.replace(self.literal,'"fake `${value}`"'),self.base.replace(self.literal,"'ordinary'")+"/* fake `${value}` */\n// fake `bad`\n"]
  for source in variants:
   with self.subTest(source=source):self.assertEqual(tokenize_validation(source),tokenize(source,declaration_inventory=True))
 def test_original_offsets_pairs_and_line(self):
  from agent_memory_runtime.validation_field_lexical import tokenize_validation
  from agent_memory_runtime.ui_divider_source import tokenize,Unknown
  tokens,pairs=tokenize_validation(self.base)
  templates=[t for t in tokens if t.kind=='template'];self.assertEqual(len(templates),1)
  token=templates[0];self.assertEqual(self.base[token.start:token.end],self.literal)
  self.assertEqual(token.line,self.base[:token.start].count('\n')+1)
  for opening,closing in pairs.items():
   self.assertEqual(self.base[tokens[opening].start:tokens[opening].end],tokens[opening].value)
   self.assertEqual(self.base[tokens[closing].start:tokens[closing].end],tokens[closing].value)
   self.assertEqual(tokens[closing].value,{'(':')','[':']','{':'}'}[tokens[opening].value])
  with self.assertRaises(Unknown):tokenize(self.base,declaration_inventory=True)
 def test_literal_edges_and_empty_chunks(self):
  for literal in ('`${value}`','` ${value}~`','`~${value} `','`/* // ${value} */`'):
   with self.subTest(literal=literal):self.assertEqual(parse_validation_field_file(self.base.replace(self.literal,literal)),self.expected)
 def test_rejected_template_shapes(self):
  for literal in ('`x${ value}`','`x${value }`','`x${value}'+chr(127)+'`','`é${value}`','`x$${value}`','`x{${value}`','`x}${value}`','`x\\${value}`','`x${value}``','`x${value}\n`'):
   with self.subTest(literal=literal):self.assertIsNone(parse_validation_field_file(self.base.replace(self.literal,literal)))
 def test_call_single_line_and_boundaries(self):
  call='console.info('+self.literal+')'
  bad=['console\n.info('+self.literal+')','console.\ninfo('+self.literal+')','console.info(\n'+self.literal+')','console.info('+self.literal+'\n)','console/*\n*/.info('+self.literal+')','console.info('+self.literal+',)','console.info(1,'+self.literal+')',call+' console.info(1)']
  for replacement in bad:
   with self.subTest(call=replacement):self.assertIsNone(parse_validation_field_file(self.base.replace(call,replacement)))
 def test_late_shadow_and_size(self):
  source=self.base[:-2]+"  value: string = ''\n}\n"
  self.assertIsNone(parse_validation_field_file(source))
  self.assertIsNone(parse_validation_field_file(' '*(2*1024*1024+1)))

class TemplatePositionRegression(unittest.TestCase):
 setUp = TemplateLexicalRegression.setUp
 def test_valid_lexeme_forbidden_positions(self):
  ordinary=self.base.replace(self.literal,"'ordinary'")
  variants=[ordinary.replace("message: 'A value is required'","message: `${value}`"),ordinary.replace("customerCode: string = ''","customerCode: string = `${value}`"),"import { Service } from `${value}`;\n"+ordinary,ordinary.replace("console.info('ordinary')","console.info(1, `${true}`)"),ordinary.replace("console.info('ordinary')","this.dispatchDraft(`${true}`)"),ordinary.replace('export class AccountDraftPanel','export `${class}` AccountDraftPanel')]
  for source in variants:
   with self.subTest(source=source):self.assertIsNone(parse_validation_field_file(source))

if __name__=='__main__':unittest.main()
