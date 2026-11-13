# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tests.agent_memory_test_base import AgentMemoryTestBase
b=AgentMemoryTestBase();e=Path('docs/eval/restore-current-20261114'); protocol=json.loads((e/'protocol.json').read_text());results=[]
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'fixture';p.mkdir()
 for name,source in protocol['sources'].items(): (p/name).write_text(source)
 b.run_memory(p,'init'); b.run_memory(p,'learn-path','--path','.', '--json')
 for case in protocol['queries']:
  result=json.loads(b.run_memory(p,'context','--query',case['query'],'--compact','--json').stdout)
  paths=[a['file_path'] for a in result['query_handoff']['code_anchors']]
  results.append({'case':case,'paths':paths,'passed':case['required'] in paths and not set(paths)&set(case['excluded']),'output':result})
(e/'baseline.json').write_text(json.dumps(results,indent=2))
for r in results: print(r['passed'],r['paths'])
