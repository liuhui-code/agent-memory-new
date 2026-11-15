# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,tempfile,sys
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=Path(sys.argv[1]).resolve();phase=sys.argv[2];p=json.loads((D/'protocol-v2.json').read_text())
with tempfile.TemporaryDirectory(prefix='command-binding-redo-')as tmp:
 root=Path(tmp)/'source';root.mkdir()
 for name,source in p['sources'].items():(root/name).write_text(source)
 commands=[]
 def run(*args):
  cmd=[sys.executable,str(ROOT/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',tmp+'/memory']
  r=subprocess.run(cmd,capture_output=True,text=True,check=True);commands.append({'command':cmd,'returncode':r.returncode,'stderr':r.stderr});return json.loads(r.stdout)if'--json'in args else r.stdout
 setup=[run('init'),run('learn-path','--path','.')]
 results=[]
 for q in p['queries']:
  raw=run('context','--query',q['query'],'--json');compact=run('context','--query',q['query'],'--compact','--json')
  observed=[a['file_path']for a in compact['query_handoff']['code_anchors']]
  results.append({'query':q,'raw':raw,'compact':compact,'observed':observed,'pass':observed==q['expected']})
 out={'setup':setup,'results':results,'commands':commands};(D/(phase+'.json')).write_text(json.dumps(out,indent=2));print([(r['observed'],r['pass'])for r in results])
