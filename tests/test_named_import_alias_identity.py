# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.ecma_import_alias import alias_target, alias_bindings
D=Path(__file__).resolve().parents[1]/'docs/eval/builder-call-current'
class NamedImportAliasTests(AgentMemoryTestBase):
 def public_calls(self,sources):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name,text in sources.items():(root/name).write_text(text)
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   syms=json.loads(self.run_memory(root,'list','--type','code-symbol','--limit','200','--json').stdout);byid={x['id']:x for x in syms}
   edges=json.loads(self.run_memory(root,'list','--type','memory-edge','--limit','200','--json').stdout)
   return {(byid[x['source_id']]['qualified_name'],byid[x['target_id']]['file_path'],byid[x['target_id']]['qualified_name'])for x in edges if x['relation']=='calls'and x['source_type']=='code_symbol'and x['target_type']=='code_symbol'}
 def test_public_alias_binds_original_and_preserves_nested_local_calls(self):
  p=json.loads((D/'alias-protocol.json').read_text());actual=self.public_calls(p['sources'])
  for source,target in p['required_calls']:
   self.assertTrue(any(a==source and c==target for a,b,c in actual),(source,target,actual))
  self.assertFalse(any(a=='AliasView.build'and c=='renderLine'for a,b,c in actual))
 def test_missing_remote_never_binds_other_module(self):
  sources={'Absent.ts':'export function other():void {}\n','Elsewhere.ts':'export function paintLine():void {}\n','Caller.ts':"import { paintLine as renderLine } from './Absent'\nexport function run():void { renderLine() }\n"}
  self.assertFalse(any(a=='run' for a,b,c in self.public_calls(sources)))
 def test_two_modules_same_original_name_keep_exact_destinations(self):
  sources={n+'.ts':'export function paintLine():void {}\n'for n in ['One','Two']}
  sources['Caller.ts']="import { paintLine as first } from './One'\nimport { paintLine as second } from './Two'\nexport function run():void { first(); second() }\n"
  actual=self.public_calls(sources)
  self.assertEqual({('run','One.ts','paintLine'),('run','Two.ts','paintLine')},actual)
 def test_unknown_and_shadow_not_certified(self):
  bodies=['run(){ let first,\n renderLine; renderLine() }','run(){ for (let\n renderLine of xs) { renderLine() } }','run(){ let\n renderLine; renderLine() }','run(){ const renderLine = local; renderLine() }','run(){ const { renderLine } = local; renderLine() }','run(){ function renderLine(){} renderLine() }','run(){ xs.forEach((renderLine)=>renderLine()) }','run(){ try{}catch(renderLine){renderLine()} }','run(){ obj.renderLine() }','run(){ const {\n x: renderLine\n } = local; renderLine() }','run(){ ({renderLine}=local); renderLine() }','run(){ renderLine = local; renderLine() }','run(){ return `${renderLine()}` }']
  for body in bodies:
   with self.subTest(body=body):self.assertIsNone(alias_target('renderLine','paintLine',body,'run()',{}))
  self.assertIsNone(alias_target('renderLine','paintLine','run(){renderLine()}','run(renderLine:Fn)',{}))
  self.assertIsNone(alias_target('renderLine','paintLine','run(){renderLine()}','run()',{'renderLine':object()}))

 def test_duplicate_import_alias_is_unknown(self):
  self.assertEqual({'local':None},alias_bindings([('one','local','A.ts'),('two','local','B.ts')]))
  self.assertIsNone(alias_target('local',None,'run(){local()}','run()',{}))
 def test_public_local_parameter_and_function_shadows_abstain(self):
  library='export function paintLine():void {}\nexport function renderLine():void {}\n'
  for declaration in ['run(renderLine: () => void):void { renderLine() }','run():void { function renderLine() {} renderLine() }','run():void { const {\n x: renderLine\n } = factory; renderLine() }']:
   sources={'Library.ts':library,'Caller.ts':"import { paintLine as renderLine } from './Library'\nexport class Caller {\n "+declaration+'\n}\n'}
   self.assertFalse(any(path=='Library.ts'for a,path,c in self.public_calls(sources)))
 def test_non_alias_import_context_preserved(self):
  self.assertEqual({},alias_bindings([('DefaultView','DefaultView','View.ts'),('named','named','Mod.ts')]))
