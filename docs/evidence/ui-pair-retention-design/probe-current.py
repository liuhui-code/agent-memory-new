# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(ROOT))
from tools.agent_memory_runtime.benchmark_workspace import materialized_workspace
pack=json.loads((ROOT/'docs/eval/system-capability-cases.json').read_text());case=next(c for c in pack['cases']if c['id']=='context-cross-component-preview');q=case['query_variants'][0]['description']
with tempfile.TemporaryDirectory(prefix='pair-current-')as t,materialized_workspace(ROOT/'docs/eval/fixtures/system-capability',case)as project:
 def cli(*args,trace=False):
  command=[sys.executable,str(ROOT/'tools/agent_memory.py')]
  if trace:command=[sys.executable,str(D/'trace-current-cli.py'),str(D/'current-fixed-original-trace.json'),str(ROOT/'tools/agent_memory.py')]
  r=subprocess.run([*command,*args,'--project',str(project),'--memory-home',str(Path(t)/'memory')],capture_output=True,text=True);
  if r.returncode:
   (D/'current-fixed-error.txt').write_text(r.stderr);r.check_returncode()
  return json.loads(r.stdout)if '--json'in args else r.stdout
 cli('init');cli('learn-path','--path','.','--json');result=cli('context','--query',q,'--compact','--json',trace=True)
 (D/'current-fixed-original-compact.json').write_text(json.dumps(result,indent=2,ensure_ascii=False));print([a['file_path']for a in result['query_handoff']['code_anchors']])
