# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
protocol=json.loads((ROOT/'docs/evidence/initializer-scope-current/protocol.json').read_text())
selection=[[0,1],[0,1],[0,1,2]]; results={};freeze={}
for scenario,indices in zip(protocol['scenarios'],selection):
 freeze[scenario['id']]={'sources':{n:hashlib.sha256(s.encode()).hexdigest() for n,s in scenario['sources'].items()},'queries':[scenario['queries'][i] for i in indices]}
(OUT/'freeze.json').write_text(json.dumps(freeze,indent=2))
for scenario,indices in zip(protocol['scenarios'],selection):
 with tempfile.TemporaryDirectory(prefix='nested-command-') as d:
  root=Path(d)/'source';root.mkdir()
  for n,s in scenario['sources'].items():(root/n).write_text(s)
  commands=[]
  def run(*a):
   cmd=['python',str(ROOT/'tools/agent_memory.py'),*a,'--project',str(root),'--memory-home',d+'/memory']
   p=subprocess.run(cmd,capture_output=True,text=True,check=True);commands.append({'command':cmd,'returncode':p.returncode,'stderr':p.stderr})
   return json.loads(p.stdout) if '--json' in a else p.stdout
  setup=[run('init'),run('learn-path','--path','.')]
  results[scenario['id']]={'sources':scenario['sources'],'setup':setup,'symbols':run('list','--type','code-symbol','--json'),'queries':{scenario['queries'][i]:run('context','--query',scenario['queries'][i],'--compact','--json') for i in indices},'commands':commands}
(OUT/'public.json').write_text(json.dumps(results,indent=2))
