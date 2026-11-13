# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tests.agent_memory_test_base import AgentMemoryTestBase
p=Path('docs/eval/named-interface-retention');protocol=json.loads((p/'protocol.json').read_text());b=AgentMemoryTestBase();results=[]
for ambiguous in (False,True):
 with tempfile.TemporaryDirectory() as d:
  root=Path(d);sources=dict(protocol['sources'])
  if ambiguous:sources[protocol['ambiguous_variant']['extra_file']]=protocol['ambiguous_variant']['source']
  for name,source in sources.items():
   f=root/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(source)
  b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
  for case in protocol['queries'][:1] if ambiguous else protocol['queries']:
   raw=json.loads(b.run_memory(root,'context','--query',case['query'],'--json').stdout)
   out=json.loads(b.run_memory(root,'context','--query',case['query'],'--compact','--json').stdout)
   anchors=out['query_handoff']['code_anchors'];paths=[a['file_path'] for a in anchors]
   valid=all('\n'.join(sources[a['file_path']].splitlines()[e['start_line']-1:e['end_line']])==e['content'] for a in anchors for e in a.get('source_excerpts',[]))
   results.append({'id':case['id'],'ambiguous':ambiguous,'query':case['query'],'required':case['required'],'paths':paths,'required_present':set(case['required'] or [])<=set(paths),'source_bytes_valid':valid,'raw':raw,'compact':out})
(p/sys.argv[1]).write_text(json.dumps(results,indent=2,ensure_ascii=False))
for r in results:print(r['id'],r['ambiguous'],r['required_present'],r['paths'])
