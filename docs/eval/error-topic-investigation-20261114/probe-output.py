# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,sys,os
from pathlib import Path
sys.path.insert(0,str(Path(os.environ.get('RUNTIME_REPO',Path.cwd()))))
from tests.agent_memory_test_base import AgentMemoryTestBase
b=AgentMemoryTestBase();e=Path('docs/eval/error-topic-investigation-20261114');p=json.loads((e/'explicit-output-protocol.json').read_text());rows=[]
for scenario in p['scenarios']:
 with tempfile.TemporaryDirectory() as t:
  root=Path(t)/'fixture';root.mkdir()
  for name,source in scenario['sources'].items():(root/name).write_text(source)
  b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.', '--json')
  for case in scenario['queries']:
   d=json.loads(b.run_memory(root,'context','--query',case['query'],'--compact','--json').stdout)
   paths=[a['file_path'] for a in d['query_handoff']['code_anchors']]
   body='\n'.join(e['content'] for a in d['query_handoff']['code_anchors'] for e in a.get('source_excerpts',[]))
   rows.append({'case':case,'paths':paths,'pass':paths==[case['expected']] and case['body'] in body,'output':d})
(e/sys.argv[1]).write_text(json.dumps(rows,ensure_ascii=False,indent=2))
for r in rows:print(r['case']['expected'],r['case']['query'],r['pass'],r['paths'])
