# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,re,tempfile,unittest
from types import SimpleNamespace
from tools.agent_memory_runtime.semantic_ecma import container_fields,FIELD_RE
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
D=Path(__file__).resolve().parents[1]/'docs/evidence/shared-field-owner'

class ContainerFieldScopeTests(AgentMemoryTestBase):
 def test_public_typed_calls_use_declared_owner_field(self):
  p=json.loads((D/'protocol.json').read_text())
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name,source in p['sources'].items():(root/name).write_text(source)
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   syms=json.loads(self.run_memory(root,'list','--type','code-symbol','--limit','300','--json').stdout);byid={s['id']:s['qualified_name']for s in syms}
   edges=json.loads(self.run_memory(root,'list','--type','memory-edge','--limit','300','--json').stdout)
   calls={(byid[e['source_id']],byid[e['target_id']])for e in edges if e['relation']=='calls'and e['source_type']=='code_symbol'and e['target_type']=='code_symbol'}
   for source,target in p['expected_target'].items():
    target_row=next(r for r in syms if r['qualified_name']==target)
    self.assertEqual((2,4) if target=='RecordStore.read' else (7,9),(target_row['start_line'],target_row['end_line']))
    self.assertTrue(target_row['symbol_key']);self.assertEqual(64,len(target_row['source_digest']))
    source_row=next(r for r in syms if r['qualified_name']==source)
    text=p['sources'][source.split('.')[0]+'.ts'].splitlines()
    self.assertEqual((next(i for i,line in enumerate(text,1)if 'collect()'in line),len(text)-1),(source_row['start_line'],source_row['end_line']))
    with self.subTest(source=source):self.assertEqual({target},{t for s,t in calls if s==source})

class ContainerFieldInputTests(unittest.TestCase):
 def fields(self,source):
  lines=source.splitlines();return container_fields(lines,SimpleNamespace(start=0,end=len(lines)-1))
 def test_noncode_nested_type_and_parameter_do_not_rebind(self):
  controls=[
   ' /*\n store: Fake\n */',
   ' note = `\n store: Fake\n `',
   ' note = "store: Fake"',
   ' run() {\n const settings: {\n store: Fake\n } = value\n }',
   ' run(\n store: Fake\n ): void {\n use(store)\n }',
   ' options: {\n store: Fake\n }',
  ]
  for extra in controls:
   with self.subTest(extra=extra):self.assertEqual('Real',self.fields('class Owner {\n store: Real\n'+extra+'\n}')['store'])
 def test_real_fields_after_nested_blocks_and_semicolon_legacy(self):
  self.assertEqual({'store':'Real','other':'Other'},self.fields('class Owner {\n run() { if(ok) { use() } }\n store: Real; ignored: Fake\n other: Other\n}'))
 def test_unknown_whole_container_is_exact_legacy_field_map(self):
  for extra in [' run() { return x / 2 }',' note = `${value}`',' note = `${ok ? `x` : ""}`',' note = "unterminated',' run() { ] }']:
   source='class Owner {\n store: Real\n /*\n store: Fake\n */\n'+extra+'\n}'
   expected={}
   for line in source.splitlines()[1:-1]:
    m=FIELD_RE.match(line)
    if m and '('not in line.split(':',1)[0]:expected[m.group(1)]=re.split(r'[<,?. ]',m.group(2).strip())[0]
   with self.subTest(extra=extra):self.assertEqual(expected,self.fields(source))

if __name__=='__main__':unittest.main()
