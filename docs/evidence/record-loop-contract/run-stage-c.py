"""Producer-only install/merge observation, fixed Stage B13 inputs."""
import json,sys,subprocess,sqlite3,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];D=Path(__file__).resolve().parent;p=json.loads((D/'POSITIVE-ONLY-PROTOCOL.json').read_text());phase=sys.argv[1];assert phase in {'install','merge'}
workspace=ROOT.parent/'record-loop-fixed-before';rows=[];commands=[];indices=[]
assert not (D/('stage-c-'+phase+'-public.json')).exists()
for co in p['cohorts']:
 project=workspace/co['id']/'source';home=workspace/co['id']/'memory'
 for n,h in p['source_hashes'][co['id']].items():assert hashlib.sha256((project/n).read_bytes()).hexdigest()==h
 def call(args,trace=None):
  cli=[str(ROOT/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(home)]
  cmd=[sys.executable,*cli]if trace is None else[sys.executable,str(D/'trace-stage-c.py'),str(trace),*cli]
  r=subprocess.run(cmd,text=True,capture_output=True,cwd=ROOT);commands.append(dict(command=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));(D/('stage-c-'+phase+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n');assert r.returncode==0,r.stderr;return json.loads(r.stdout)
 if phase=='merge':call(['learn-path','--path','.','--json'])
 db=next(home.rglob('memory.db'));c=sqlite3.connect(db);c.row_factory=sqlite3.Row
 indices.append({'cohort':co['id'],'schema':[list(r)for r in c.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name")],'files':[dict(r)for r in c.execute('SELECT * FROM code_files')],'symbols':[dict(r)for r in c.execute('SELECT * FROM code_symbols')]});c.close()
 for case in co['queries']:
  row={'cohort':co['id'],'case':case}
  for form in ['raw','compact']:
   args=['context','--query',case['query'],'--json']+(['--compact']if form=='compact'else[])
   row[form]=call(args,D/('stage-c-'+phase+'-trace-'+co['id']+'-'+case['id']+'-'+form+'.json'))
  rows.append(row);(D/('stage-c-'+phase+'-public.json')).write_text(json.dumps(rows,indent=2)+'\n')
  print(phase,co['id'],case['id'],[a['file_path']for a in row['compact']['query_handoff']['code_anchors']],flush=True)
(D/('stage-c-'+phase+'-index.json')).write_text(json.dumps(indices,indent=2)+'\n')
