# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime.ecma_callback_mask import callback_mask_lines
from tools.agent_memory_runtime.ecma_typed_import_alias import typed_alias_bindings,aliased_field_relations
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
D=Path(__file__).resolve().parents[1]/'docs/evidence/typed-import-alias'

class TypedImportAliasTests(AgentMemoryTestBase):
 def test_public_named_type_alias_has_exact_module_qualified_target(self):
  p=json.loads((D/'protocol.json').read_text());extra=json.loads((D/'review-negative-protocol.json').read_text());sources={**p['sources'],**extra['sources']}
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
    with self.subTest(name=name):
     self.assertEqual({tuple(target)},targets(name,'calls'))
     row=next(r for r in symbols if (r['file_path'],r['qualified_name'])==tuple(target))
     expected_range=(2,2) if target[0]=='MoreStores.ts' else ((2,4) if target[1]=='ActualStore.read' else (7,9))
     self.assertEqual(expected_range,(row['start_line'],row['end_line']))
     self.assertTrue(row['symbol_key']);self.assertEqual(64,len(row['source_digest']))
   for name,target in extra['expected_await_target'].items():
    with self.subTest(awaited=name):self.assertEqual({tuple(target)},targets(name,'awaits'))
   for name in extra['expected_no_new_alias_binding']:
    with self.subTest(unknown=name):self.assertEqual(set(),targets(name,'calls'));self.assertEqual(set(),targets(name,'awaits'))

class TypedAliasBoundedWorkTests(unittest.TestCase):
 def fixture(self):
  lines=['class Owner {',' store: LocalStore']
  blocks=[]
  for i in range(12):
   start=len(lines);lines.extend([' read'+str(i)+'() {',' return this.store.read()',' }'])
   blocks.append(SimpleNamespace(owner='Owner',start=start,end=len(lines)-1,entity=SimpleNamespace(key='method'+str(i))))
  lines.append('}')
  owner=SimpleNamespace(name='Owner',kind='class',start=0,end=len(lines)-1)
  return lines,owner,blocks
 def test_file_mask_once_and_bodies_only_per_callable(self):
  lines,owner,blocks=self.fixture()
  with patch('tools.agent_memory_runtime.ecma_typed_import_alias.callback_mask_lines',wraps=callback_mask_lines)as mask:
   fields=typed_alias_bindings(lines,[owner],{'Owner':{'store':'LocalStore'}},[('ActualStore','LocalStore','Stores.ts')])
   context=SimpleNamespace(typed_alias_fields=fields)
   for block in blocks:self.assertEqual(1,len(aliased_field_relations(lines,block,context)))
  self.assertEqual(13,mask.call_count)
  self.assertEqual(1,sum(len(call.args[0])==len(lines)for call in mask.call_args_list))
 def test_no_alias_no_scan_and_duplicate_owner_unknown(self):
  lines,owner,blocks=self.fixture()
  with patch('tools.agent_memory_runtime.ecma_typed_import_alias.callback_mask_lines',wraps=callback_mask_lines)as mask:
   self.assertEqual({},typed_alias_bindings(lines,[owner],{},[]))
   self.assertEqual([],aliased_field_relations(lines,blocks[0],SimpleNamespace(typed_alias_fields={})))
  self.assertEqual(0,mask.call_count)
  self.assertEqual({},typed_alias_bindings(lines,[owner,owner],{'Owner':{'store':'LocalStore'}},[('ActualStore','LocalStore','Stores.ts')]))

if __name__=='__main__':unittest.main()
