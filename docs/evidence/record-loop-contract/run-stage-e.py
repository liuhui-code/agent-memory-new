"""Fixed13 + pre-frozen explicit-log after; no learn, source or query edits."""
import json,subprocess,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];D=Path(__file__).parent
p=json.loads((D/'POSITIVE-ONLY-PROTOCOL.json').read_text());out=D/'stage-e-public.json';assert not out.exists()
rows=[];commands=[]
for co in p['cohorts']:
 project=ROOT.parent/'record-loop-fixed-before'/co['id']/'source';home=project.parent/'memory'
 for name,digest in p['source_hashes'][co['id']].items():assert hashlib.sha256((project/name).read_bytes()).hexdigest()==digest
 cases=list(co['queries'])
 if co['id']=='old-source-relation':cases+=[dict(id='explicit-log-control',query='Locate AfterIteration.summarize and the console log source for chunk.')]
 for case in cases:
  row=dict(cohort=co['id'],case=case)
  for mode in ('raw','compact'):
   cmd=[sys.executable,str(ROOT/'tools/agent_memory.py'),'context','--project',str(project),'--memory-home',str(home),'--query',case['query'],'--json']+(['--compact']if mode=='compact'else[])
   r=subprocess.run(cmd,text=True,capture_output=True,cwd=ROOT);commands.append(dict(command=cmd,returncode=r.returncode,stderr=r.stderr));(D/'stage-e-commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert r.returncode==0,r.stderr;row[mode]=json.loads(r.stdout)
  rows.append(row);out.write_text(json.dumps(rows,indent=2)+'\n');print(co['id'],case['id'],[a['file_path']for a in row['compact']['query_handoff']['code_anchors']],row['compact']['output_budget'],flush=True)
