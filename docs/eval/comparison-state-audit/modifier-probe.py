# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tests.agent_memory_test_base import AgentMemoryTestBase
p=Path('docs/eval/comparison-state-audit');protocol=json.loads((p/'modifier-protocol.json').read_text());b=AgentMemoryTestBase();results=[]
for modifier,source in protocol['sources'].items():
 with tempfile.TemporaryDirectory() as d:
  root=Path(d);(root/'DisclosureState.ets').write_text(source)
  b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
  raw=json.loads(b.run_memory(root,'context','--query',protocol['query'],'--json').stdout)
  compact=json.loads(b.run_memory(root,'context','--query',protocol['query'],'--compact','--json').stdout)
  symbols=json.loads(b.run_memory(root,'list','--type','code-symbol','--limit','100','--json').stdout)
  edges=json.loads(b.run_memory(root,'list','--type','memory-edge','--limit','100','--json').stdout)
  results.append({'modifier':modifier,'source':source,'query':protocol['query'],'raw':raw,'compact':compact,'symbols':symbols,'edges':edges})
(p/sys.argv[1]).write_text(json.dumps(results,indent=2,ensure_ascii=False))
for r in results:print(r['modifier'],[(a.get('symbol'),a.get('record_type')) for a in r['raw']['query_handoff']['code_anchors']])
