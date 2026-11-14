# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(ROOT))
from tools.agent_memory_runtime.benchmark_workspace import materialized_workspace
pack=json.loads((ROOT/'docs/eval/system-capability-cases.json').read_text());case=next(c for c in pack['cases']if c['id']=='context-lifecycle-persistence-owner-precision')
(D/'case-frozen.json').write_text(json.dumps(case,indent=2,ensure_ascii=False))
with tempfile.TemporaryDirectory(prefix='lifecycle-prerequisite-')as t,materialized_workspace(ROOT/'docs/eval/fixtures/system-capability',case)as project:
 def cli(*args,trace=None):
  cmd=[sys.executable,str(ROOT/'tools/agent_memory.py')]
  if trace:cmd=[sys.executable,str(D/'trace-cli.py'),str(trace),str(ROOT/'tools/agent_memory.py')]
  r=subprocess.run([*cmd,*args,'--project',str(project),'--memory-home',str(Path(t)/'memory')],text=True,capture_output=True)
  if r.returncode:(D/'run-error.txt').write_text(r.stderr);r.check_returncode()
  return json.loads(r.stdout)if '--json'in args else r.stdout
 cli('init');cli('learn-path','--path','.','--json');rows=[]
 for variant in case['query_variants']:
  if variant['id']=='original':continue
  q=variant['description'];raw=cli('context','--query',q,'--json');compact=cli('context','--query',q,'--compact','--json',trace=D/(variant['id']+'-trace.json'))
  rows.append({'variant':variant,'raw':raw,'compact':compact});(D/'current-public.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False));print(variant['id'],[a['file_path']for a in compact['query_handoff']['code_anchors']],flush=True)
