# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parents[2]))
from tests.agent_memory_test_base import AgentMemoryTestBase
p=json.loads((D/'protocol.json').read_text());b=AgentMemoryTestBase();out=[]
for case in p['cases']:
 with tempfile.TemporaryDirectory() as d:
  root=Path(d)
  for name,source in case['sources'].items():(root/name).write_text(source)
  b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
  raw=json.loads(b.run_memory(root,'context','--query',case['query'],'--json').stdout)
  compact=json.loads(b.run_memory(root,'context','--query',case['query'],'--compact','--json').stdout)
  paths={x['file_path'] for x in compact['query_handoff']['code_anchors']}
  passed=set(case['required'])<=paths and not(set(case.get('forbidden',[]))&paths)
  if 'exact_paths' in case:passed=passed and paths==set(case['exact_paths'])
  out.append(dict(id=case['id'],paths=sorted(paths),passes_frozen_check=passed,raw=raw,compact=compact))
  print(case['id'],passed,sorted(paths),flush=True)
  (D/sys.argv[1]).write_text(json.dumps(out,indent=2,ensure_ascii=False))
