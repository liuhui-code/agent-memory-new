# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,unittest
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
    with self.subTest(source=source):self.assertEqual({target},{t for s,t in calls if s==source})

if __name__=='__main__':unittest.main()
