# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import sys,json,tempfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tests.agent_memory_test_base import AgentMemoryTestBase
p=Path('docs/eval/same-file-explicit-pair');proto=json.loads((p/'protocol.json').read_text());assert hashlib.sha256((p/'protocol.json').read_bytes()).hexdigest()==(p/'protocol.sha256').read_text().strip()
b=AgentMemoryTestBase();out=[]
with tempfile.TemporaryDirectory() as t:
 root=Path(t)
 for f,s in proto['sources'].items():(root/f).write_text(s)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 for q in proto['queries']:
  raw=json.loads(b.run_memory(root,'context','--query',q['query'],'--json').stdout);compact=json.loads(b.run_memory(root,'context','--query',q['query'],'--compact','--json').stdout)
  body='\n'.join(e['content'] for a in compact['query_handoff']['code_anchors'] for e in a.get('source_excerpts',[]))
  missing=[s for s in q['fragments'] if s not in body];out.append({'id':q['id'],'query':q['query'],'missing':missing,'raw':raw,'compact':compact});print(q['id'],missing,compact['query_handoff'].get('callable_evidence'))
(p/'before.json').write_text(json.dumps(out,indent=2))
