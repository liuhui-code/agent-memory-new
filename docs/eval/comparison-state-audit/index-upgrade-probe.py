# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[3];D=Path(__file__).resolve().parent;B=R.parent/'state-modifier-baseline'
p=json.loads((D/'modifier-protocol.json').read_text());results=[]
with tempfile.TemporaryDirectory() as t:
 root=Path(t)/'source';root.mkdir();home=Path(t)/'memory';(root/'DisclosureState.ets').write_text(p['sources']['private'])
 def run(repo,args):
  cmd=[sys.executable,str(repo/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',str(home)]
  r=subprocess.run(cmd,text=True,capture_output=True,cwd=repo)
  if r.returncode:raise RuntimeError(r.stderr)
  return {'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
 results.append({'stage':'old-learn','outputs':[run(B,['init']),run(B,['learn-path','--path','.','--json'])]})
 for stage,repo in [('old',B),('installed-no-learn',R),('after-merge-learn',R)]:
  outputs=[]
  if stage=='after-merge-learn':outputs.append(run(R,['learn-path','--path','.','--json']))
  for kind in ['code-symbol','memory-edge']:outputs.append(run(repo,['list','--type',kind,'--limit','100','--json']))
  outputs.append(run(repo,['context','--query',p['query'],'--compact','--json']))
  results.append({'stage':stage,'outputs':outputs})
(D/'index-upgrade.json').write_text(json.dumps(results,indent=2))
for stage in results[1:]:
 symbols=json.loads(next(x['stdout'] for x in stage['outputs'] if '--type' in x['command'] and 'code-symbol' in x['command']))
 edges=json.loads(next(x['stdout'] for x in stage['outputs'] if '--type' in x['command'] and 'memory-edge' in x['command']))
 print(stage['stage'],[(s['symbol'],s['qualified_name']) for s in symbols if s['symbol_type']=='state'],[(e['relation'],e['target_id']) for e in edges if e['relation'] in {'reads_state','writes_state'}])
