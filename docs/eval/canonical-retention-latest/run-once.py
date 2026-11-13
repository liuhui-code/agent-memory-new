# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,tempfile,os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tools.agent_memory_runtime.benchmark_workspace import materialized_workspace
p=Path('docs/eval/canonical-retention-latest');protocol=json.loads((p/'protocol.json').read_text())
assert not (p/'public.json').exists()
pack=json.loads(Path('docs/eval/system-capability-cases.json').read_text());case=protocol['case'];results=[]
with tempfile.TemporaryDirectory() as d, materialized_workspace(Path(pack['project_path']),case) as root:
 for i,args in enumerate([['init'],['learn-path','--path','.','--json'],['context','--query',protocol['variant']['description'],'--json'],['context','--query',protocol['variant']['description'],'--compact','--json']]):
  env=dict(os.environ,TRACE_FILE=str(p/f'trace-{i}.json'))
  command=[sys.executable,str(p/'trace-cli.py'),*args,'--project',str(root),'--memory-home',d+'/memory']
  r=subprocess.run(command,text=True,capture_output=True,env=env)
  results.append({'command':command,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});(p/'public.json').write_text(json.dumps(results,indent=2));assert r.returncode==0
