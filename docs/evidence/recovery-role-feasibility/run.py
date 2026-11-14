# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];phase=sys.argv[1];W=ROOT.parent/'recovery-role-execution';W.mkdir(exist_ok=True)
p=json.loads((D/'protocol.json').read_text());out=[]
for f in p['families']:
 project=W/(phase+'-'+f['id']);project.mkdir()
 for name,source in f['sources'].items():
  dest=project/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(source)
 def cli(*args,trace=None):
  cmd=[sys.executable,str(ROOT/'tools/agent_memory.py')]
  if trace:cmd=[sys.executable,str(D/'trace-cli.py'),str(trace),str(ROOT/'tools/agent_memory.py')]
  r=subprocess.run([*cmd,*args,'--project',str(project),'--memory-home',str(project.parent/(project.name+'-memory'))],text=True,capture_output=True)
  if r.returncode:(D/(phase+'-error.txt')).write_text(r.stderr);r.check_returncode()
  return json.loads(r.stdout)if '--json'in args else r.stdout
 cli('init');cli('learn-path','--path','.','--json');symbols=cli('list','--type','code-symbol','--limit','300','--json');edges=cli('list','--type','memory-edge','--limit','1000','--json');(D/(phase+'-edges-'+f['id']+'.json')).write_text(json.dumps(edges,indent=2))
 for c in f['queries']:
  raw=cli('context','--query',c['query'],'--json');trace=D/(phase+'-trace-'+f['id']+'-'+c['id']+'.json');compact=cli('context','--query',c['query'],'--compact','--json',trace=trace)
  out.append({'family':f['id'],'case':c,'symbols':symbols,'raw':raw,'compact':compact,'trace':trace.name});(D/(phase+'-public.json')).write_text(json.dumps(out,indent=2,ensure_ascii=False));print(f['id'],c['id'],[a['file_path']for a in compact['query_handoff']['code_anchors']],flush=True)
