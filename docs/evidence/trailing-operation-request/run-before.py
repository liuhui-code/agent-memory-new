# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import dataclasses,hashlib,json,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.semantic_ecma import parse_source
D=Path(__file__).resolve().parent;p=json.loads((D/'protocol.json').read_text());b=AgentMemoryTestBase();rows=[]
with tempfile.TemporaryDirectory(prefix='typography-request-') as d:
 root=Path(d)
 for name,s in p['sources'].items():(root/name).write_text(s)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 for c in p['queries']:
  raw=json.loads(b.run_memory(root,'context','--query',c['query'],'--json').stdout)
  compact=json.loads(b.run_memory(root,'context','--query',c['query'],'--compact','--json').stdout)
  paths=[a['file_path'] for a in compact['query_handoff']['code_anchors']]
  passed=(set(c.get('required',[]))<=set(paths) and not(set(c.get('excluded',[]))&set(paths)))if 'required'in c else None
  rows.append({'id':c['id'],'query':c['query'],'paths':paths,'passed_frozen_path_check':passed,'raw':raw,'compact':compact});print(c['id'],paths,passed)
 (D/'public-before.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
observed=[]
for c in p['source_controls']:
 source=c.get('sources')or('@Component\nexport struct Control {\n build() {\n'+c['body']+'\n }\n}\n')
 with tempfile.TemporaryDirectory(prefix='trailing-source-')as d:
  root=Path(d);path=root/'Control.ets';path.write_text(source);r=parse_source(SimpleNamespace(root=root),path,path.read_bytes(),'ArkTS',True)
  observed.append({'id':c['id'],'source':source,'digest':hashlib.sha256(path.read_bytes()).hexdigest(),'entities':[dataclasses.asdict(v)for v in r.entities],'mechanisms':[dataclasses.asdict(v)for v in r.mechanisms],'gaps':r.gaps,'expected_proposed_contract':c['expected']})
(D/'source-before.json').write_text(json.dumps(observed,indent=2))
