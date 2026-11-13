# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.text import query_tokens
b=AgentMemoryTestBase(); e=Path('docs/eval/load-topic-expansion-20261114')
p=json.loads((e/'protocol.json').read_text()); results=[]
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 for name,source in p['sources'].items():(root/name).write_text(source)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.', '--json')
 for q in p['queries']:
  raw=json.loads(b.run_memory(root,'context','--query',q['query'],'--json').stdout)
  out=json.loads(b.run_memory(root,'context','--query',q['query'],'--compact','--json').stdout)
  paths=[a['file_path'] for a in out['query_handoff']['code_anchors']]
  results.append({'case':q,'tokens':query_tokens(q['query']),'paths':paths,'pass':paths==[q['expected']],'raw':raw,'output':out})
(e/sys.argv[1]).write_text(json.dumps(results,ensure_ascii=False,indent=2))
for r in results:print(r['case']['query'],r['pass'],r['paths'])
