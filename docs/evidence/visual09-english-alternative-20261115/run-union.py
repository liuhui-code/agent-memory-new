# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(ROOT))
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_background_source import parse_background_source
from tools.agent_memory_runtime.query_render_recall import parse_render_request
b=AgentMemoryTestBase();results=[]
for c in json.loads((D/'union-protocol.json').read_text())['cases']:
 with tempfile.TemporaryDirectory(prefix='visual09-alternative-') as tmp:
  project=Path(tmp)/'source';project.mkdir()
  for name,source in c['sources'].items():(project/name).write_text(source)
  b.run_memory(project,'init');b.run_memory(project,'learn-path','--path','.','--json')
  raw=json.loads(b.run_memory(project,'context','--query',c['query'],'--json').stdout)
  compact=json.loads(b.run_memory(project,'context','--query',c['query'],'--compact','--json').stdout)
  anchors=compact['query_handoff']['code_anchors'];paths={a['file_path'] for a in anchors}
  expected_bodies={n:'\n'.join(s.splitlines()[2:-1]) for n,s in c['sources'].items() if ' build() {' in s}
  complete={a['file_path'] for a in anchors for e in a.get('source_excerpts',[]) if not e.get('truncated') and e.get('content')==expected_bodies.get(a['file_path'])}
  authorized=parse_render_request(c['query']) is not None
  passed=(not authorized) if c['mode']=='no-alternative-authority' else (set(c['required'])<=paths and set(c['required'])<=complete and not set(c['forbidden'])&paths)
  r=dict(name=c['name'],passed=passed,paths=sorted(paths),complete_build_paths=sorted(complete),render_request_recognized=authorized,background_witness={n:parse_background_source(s) for n,s in c['sources'].items()},raw=raw,compact=compact)
  results.append(r);print(c['name'],passed,sorted(paths),'complete',sorted(complete),flush=True)
(D/(sys.argv[1]+'-union-public.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2))
