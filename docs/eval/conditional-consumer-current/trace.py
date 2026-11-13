# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import sys,json,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
sys.path.insert(0,str(REPO))
from tools.agent_memory_runtime.benchmark_workspace import materialized_workspace
pack=json.loads((REPO/'docs/eval/system-capability-cases.json').read_text())
ids={'context-touch-access-safety-owner':'zh-noise'}
for case in pack['cases']:
 if case['id'] not in ids:continue
 q=next(v['description'] for v in case['query_variants'] if v['id']==ids[case['id']])
 with materialized_workspace(REPO/pack['project_path'],case) as workspace:
  commands=[]
  for args in [('init',),('learn-path','--path','.','--json'),('context','--query',q,'--json'),('context','--query',q,'--compact','--json')]:
   cmd=[sys.executable,str(REPO/'tools/agent_memory.py'),*args,'--project',str(workspace),'--memory-home',str(Path('/tmp')/'touch-current-trace-memory')]
   r=subprocess.run(cmd,cwd=REPO,text=True,capture_output=True);commands.append({'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
  (ROOT/(case['id']+'-clean.json')).write_text(json.dumps(commands,indent=2,ensure_ascii=False))
