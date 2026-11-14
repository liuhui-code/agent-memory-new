# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];phase=sys.argv[1];W=ROOT.parent/'builder-consumer-execution';W.mkdir(exist_ok=True)
p=json.loads((D/'protocol.json').read_text());results=[]
def cli(repo,project,*args,trace=None):
 command=[sys.executable,str(repo/'tools/agent_memory.py')]
 if trace:command=[sys.executable,str(D/'trace-cli.py'),str(repo/'tools/agent_memory.py'),str(trace)]
 r=subprocess.run([*command,*args,'--project',str(project),'--memory-home',str(project.parent/(project.name+'-memory'))],text=True,capture_output=True,check=True)
 return json.loads(r.stdout)if '--json'in args else r.stdout
for family in p['families']:
 project=W/(phase+'-'+family['id']);project.mkdir()
 for name,source in family['sources'].items():(project/name).write_text(source)
 cli(ROOT,project,'init');cli(ROOT,project,'learn-path','--path','.','--json')
 symbols=cli(ROOT,project,'list','--type','code-symbol','--limit','300','--json')
 for case in family['cases']:
  trace=D/(phase+'-trace-'+family['id']+'-'+case['id']+'.json')
  raw=cli(ROOT,project,'context','--query',case['query'],'--json',trace=trace)
  compact=cli(ROOT,project,'context','--query',case['query'],'--compact','--json')
  row={'family':family['id'],'case':case,'symbols':symbols,'raw':raw,'compact':compact,'trace':trace.name};results.append(row)
  (D/(phase+'-public.json')).write_text(json.dumps(results,indent=2,ensure_ascii=False))
  print(family['id'],case['id'],[a['file_path']for a in compact['query_handoff']['code_anchors']],flush=True)
project=W/'old-index'
if phase=='before':
 project.mkdir()
 for name,source in p['families'][0]['sources'].items():(project/name).write_text(source)
 old=ROOT.parent/'builder-consumer-old-index';cli(old,project,'init');cli(old,project,'learn-path','--path','.','--json')
oldresult={'symbols':cli(ROOT,project,'list','--type','code-symbol','--limit','300','--json'),'cases':[]}
for case in p['families'][0]['cases']:
 oldresult['cases'].append({'case':case,'compact':cli(ROOT,project,'context','--query',case['query'],'--compact','--json')})
(D/(phase+'-old-index.json')).write_text(json.dumps(oldresult,indent=2,ensure_ascii=False))
