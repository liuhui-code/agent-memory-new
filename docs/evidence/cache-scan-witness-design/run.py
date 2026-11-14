# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];phase=sys.argv[1];W=ROOT.parent/'cache-template-execution';W.mkdir(exist_ok=True)
p=json.loads((D/'protocol.json').read_text());project=W/phase;project.mkdir();out=[]
for name,source in p['sources'].items():(project/name).write_text(source)
def cli(*args,trace=None):
 cmd=[sys.executable,str(ROOT/'tools/agent_memory.py')]
 if trace:cmd=[sys.executable,str(D/'trace-cli.py'),str(trace),str(ROOT/'tools/agent_memory.py')]
 r=subprocess.run([*cmd,*args,'--project',str(project),'--memory-home',str(W/(phase+'-memory'))],text=True,capture_output=True)
 if r.returncode:(D/(phase+'-error.txt')).write_text(r.stderr);r.check_returncode()
 return json.loads(r.stdout)if '--json'in args else r.stdout
cli('init');cli('learn-path','--path','.','--json');symbols=cli('list','--type','code-symbol','--limit','300','--json')
for c in p['queries']:
 raw=cli('context','--query',c['query'],'--json',trace=D/(phase+'-raw-trace-'+c['id']+'.json'));compact=cli('context','--query',c['query'],'--compact','--json',trace=D/(phase+'-compact-trace-'+c['id']+'.json'))
 out.append({'case':c,'symbols':symbols,'raw':raw,'compact':compact});(D/(phase+'-public.json')).write_text(json.dumps(out,indent=2,ensure_ascii=False));print(c['id'],[a['file_path']for a in compact['query_handoff']['code_anchors']],flush=True)
