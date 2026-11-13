# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_typed_contract import classify_contract
from tools.agent_memory_runtime.query_behavior_concepts import behavior_marker_terms
from tools.agent_memory_runtime.text import query_tokens
b=AgentMemoryTestBase();e=Path('docs/eval/error-topic-investigation-20261114');p=json.loads((e/'protocol.json').read_text());results=[]
with tempfile.TemporaryDirectory() as t:
 root=Path(t)
 for name,src in p['sources'].items():(root/name).write_text(src)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.', '--json')
 for case in p['queries']:
  raw=json.loads(b.run_memory(root,'context','--query',case['query'],'--json').stdout)
  out=json.loads(b.run_memory(root,'context','--query',case['query'],'--compact','--json').stdout)
  paths=[a['file_path'] for a in out['query_handoff']['code_anchors']]
  source='\n'.join(e['content'] for a in out['query_handoff']['code_anchors'] for e in a.get('source_excerpts',[]))
  results.append({'case':case,'paths':paths,'pass':paths==[case['expected']] and case['body'] in source,'contract':classify_contract(case['query']),'markers':behavior_marker_terms(case['query']),'tokens':query_tokens(case['query']),'intent':out.get('memory_intent'),'intent_source':out.get('memory_intent_source'),'raw':raw,'output':out})
(e/(sys.argv[1] if len(sys.argv)>1 else 'independent.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2))
for r in results:print(r['case']['query'],r['pass'],r['paths'])
