# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];BASE=Path(sys.argv[1]);p=json.loads((D/'protocol.json').read_text())
with tempfile.TemporaryDirectory(prefix='tail-activation-') as d:
 project=Path(d)/'project';project.mkdir();home=Path(d)/'memory'
 for name,s in p['sources'].items():(project/name).write_text(s)
 def cli(repo,*args):
  r=subprocess.run([sys.executable,str(repo/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(home)],capture_output=True,text=True,check=True)
  return json.loads(r.stdout) if '--json' in args else r.stdout
 cli(BASE,'init');cli(BASE,'learn-path','--path','.','--json')
 before=cli(BASE,'list','--type','code-symbol','--json')
 code_only=cli(ROOT,'list','--type','code-symbol','--json')
 assert before==code_only
 learn=cli(ROOT,'learn-path','--path','.','--json')
 after=cli(ROOT,'list','--type','code-symbol','--json')
 (D/'producer-activation.json').write_text(json.dumps({'before':before,'code_only':code_only,'learn':learn,'after':after},indent=2))
 print('rows',len(before),len(after));print('keys',list(after[0]));print('beforebuild',[x for x in before if x.get('symbol')=='build']);print('afterbuild',[x for x in after if x.get('symbol')=='build'])
