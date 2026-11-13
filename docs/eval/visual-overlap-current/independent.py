# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parents[2]))
from tests.agent_memory_test_base import AgentMemoryTestBase
p=json.loads((D/'independent-protocol.json').read_text())
sources=p['sources'];queries=p['queries']
b=AgentMemoryTestBase();out=[]
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 for n,s in sources.items():(root/n).write_text(s)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 for name,q,required in queries:
  raw=json.loads(b.run_memory(root,'context','--query',q,'--json').stdout)
  compact=json.loads(b.run_memory(root,'context','--query',q,'--compact','--json').stdout)
  paths=[a['file_path'] for a in compact['query_handoff']['code_anchors']]
  out.append(dict(name=name,query=q,required=required,paths=paths,strict_pass=set(paths)==set(required),raw=raw,compact=compact));print(name,paths)
(D/'independent-current.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
