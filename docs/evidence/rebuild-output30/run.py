# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from tests.agent_memory_test_base import AgentMemoryTestBase
p=Path(__file__).parent;protocol=json.loads((p/'independent-protocol.json').read_text());b=AgentMemoryTestBase();result=[]
with tempfile.TemporaryDirectory(prefix='rebuild-output30-')as d:
 root=Path(d)
 for name,source in protocol['sources'].items():(root/name).write_text(source)
 setup=[b.run_memory(root,'init').stdout,b.run_memory(root,'learn-path','--path','.').stdout]
 for case in protocol['queries']:
  raw=json.loads(b.run_memory(root,'context','--query',case['query'],'--json').stdout)
  compact=json.loads(b.run_memory(root,'context','--query',case['query'],'--compact','--json').stdout)
  paths=[a['file_path']for a in compact['query_handoff']['code_anchors']]
  result.append(dict(case=case,raw=raw,compact=compact,required_retained=case['required']in paths,forbidden_retained=sorted(set(paths)&set(case['forbidden']))))
(p/(sys.argv[1]+'.json')).write_text(json.dumps(dict(setup=setup,results=result),ensure_ascii=False,indent=2))
print([(r['required_retained'],r['forbidden_retained'])for r in result])
