# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,tempfile,os
from pathlib import Path
folder=Path(__file__).parent.resolve();p=json.loads((folder/'protocol.json').read_text());out={}
for cohort,files in p['cohorts'].items():
 with tempfile.TemporaryDirectory() as d:
  root=Path(d)/'source';root.mkdir()
  for name in files:
   f=root/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(p['sources'][name])
  def run(label,*args):
   env=dict(os.environ,TRACE_FILE=str(folder/(cohort+'-'+label+'-trace.json')))
   r=subprocess.run(['python',str(folder/'trace-cli.py'),*args,'--project',str(root),'--memory-home',d+'/memory'],env=env,capture_output=True,text=True,check=True)
   return json.loads(r.stdout) if '--json' in args else r.stdout
  run('init','init');run('learn','learn-path','--path',str(root))
  out[cohort]={}
  for q in p['queries']:
   out[cohort][q['id']]={mode:run(q['id']+'-'+mode,'context','--query',q['query'],*flags,'--json') for mode,flags in [('raw',[]),('compact',['--compact'])]}
   print(cohort,q['id'],flush=True)
  (folder/'before.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
