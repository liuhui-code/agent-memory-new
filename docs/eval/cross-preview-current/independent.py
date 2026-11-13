# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parents[2]))
from tests.agent_memory_test_base import AgentMemoryTestBase
p=json.loads((D/'independent-protocol.json').read_text());b=AgentMemoryTestBase();out={}
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)
 for name,text in p['sources'].items():(root/name).write_text(text)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 out['symbols']=json.loads(b.run_memory(root,'list','--type','code-symbol','--limit','100','--json').stdout)
 out['edges']=json.loads(b.run_memory(root,'list','--type','memory-edge','--limit','100','--json').stdout)
 out['queries']=[]
 for q in p['queries']:
  row=dict(query=q)
  for mode,flags in [('raw',[]),('compact',['--compact'])]:row[mode]=json.loads(b.run_memory(root,'context','--query',q['text'],*flags,'--json').stdout)
  paths=[a['file_path'] for a in row['compact']['query_handoff']['code_anchors']];row['paths']=paths;row['required_retained']=set(q['required'])<=set(paths);out['queries'].append(row);print(q['id'],paths,row['required_retained'])
(D/'independent-before.json').write_text(json.dumps(out,indent=2))
