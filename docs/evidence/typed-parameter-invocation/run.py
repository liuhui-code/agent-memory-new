# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tests.agent_memory_test_base import AgentMemoryTestBase
b=AgentMemoryTestBase();e=Path('docs/evidence/typed-parameter-invocation');p=json.loads((e/'protocol.json').read_text());out={}
for name,files in p['cohorts'].items():
 with tempfile.TemporaryDirectory() as t:
  root=Path(t)
  for f in files:(root/f).write_text(p['sources'][f])
  b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.', '--json')
  out[name]={mode:json.loads(b.run_memory(root,'context','--query',p['query'],*flags,'--json').stdout) for mode,flags in [('raw',[]),('compact',['--compact'])]}
  print(name,out[name]['raw']['query_handoff'].get('callable_evidence'),flush=True)
(e/'before.json').write_text(json.dumps(out,indent=2))
