# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
D=Path(__file__).resolve().parents[1]/'docs/evidence/typed-import-alias'

class TypedImportAliasTests(AgentMemoryTestBase):
 def test_public_named_type_alias_has_exact_module_qualified_target(self):
  p=json.loads((D/'protocol.json').read_text());extra=json.loads((D/'supplemental-protocol.json').read_text());sources={**p['sources'],**extra['sources']}
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for f,s in sources.items():(root/f).write_text(s)
   self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
   symbols=json.loads(self.run_memory(root,'list','--type','code-symbol','--limit','300','--json').stdout);byid={r['id']:r for r in symbols}
   edges=json.loads(self.run_memory(root,'list','--type','memory-edge','--limit','300','--json').stdout)
   edges=[e for e in edges if e['source_type']=='code_symbol'and e['target_type']=='code_symbol']
   def targets(name,kind):return {(byid[e['target_id']]['file_path'],byid[e['target_id']]['qualified_name'])for e in edges if byid[e['source_id']]['qualified_name']==name and e['relation']==kind}
   expected={name:['Stores.ts',value]for name,value in p['expected_target'].items()};expected.update(extra['expected_target'])
   for name,target in expected.items():
    with self.subTest(name=name):self.assertEqual({tuple(target)},targets(name,'calls'))
   for name,target in extra['expected_await_target'].items():
    with self.subTest(awaited=name):self.assertEqual({tuple(target)},targets(name,'awaits'))
   for name in extra['expected_no_new_alias_binding']:
    with self.subTest(unknown=name):self.assertEqual(set(),targets(name,'calls'));self.assertEqual(set(),targets(name,'awaits'))

if __name__=='__main__':unittest.main()
