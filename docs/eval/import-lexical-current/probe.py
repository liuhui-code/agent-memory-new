# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parents[2]))
from tests.agent_memory_test_base import AgentMemoryTestBase
p=json.loads((D/'protocol.json').read_text()); sources=p['sources']
b=AgentMemoryTestBase()
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 for name,s in sources.items():(root/name).write_text(s)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 symbols=json.loads(b.run_memory(root,'list','--type','code-symbol','--limit','100','--json').stdout)
 edges=json.loads(b.run_memory(root,'list','--type','memory-edge','--limit','100','--json').stdout)
 raw=json.loads(b.run_memory(root,'context','--query',p['query'],'--json').stdout)
 byid={s['id']:s for s in symbols}
 calls=[{'source':byid[e['source_id']]['qualified_name'],'target':byid[e['target_id']]['qualified_name'],'edge':e} for e in edges if e['relation']=='calls' and e['source_type']=='code_symbol' and e['target_type']=='code_symbol']
 (D/sys.argv[1]).write_text(json.dumps(dict(symbols=symbols,edges=edges,calls=calls,raw=raw),indent=2))
 print([(e['source'],e['target']) for e in calls])
