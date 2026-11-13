# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import importlib.util,json,subprocess,sys,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fixture',ROOT/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
project=ROOT/'upgrade-fixture';project.mkdir(exist_ok=True)
for k,v in m.FILES.items():
 p=project/k;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(v)
old=ROOT.parent/'canonical-contract-investigation';new=ROOT.parent/'capability-owner-investigation';memory=ROOT/'upgrade-memory'
def call(repo,*args):
 c=[sys.executable,str(repo/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(memory)]
 r=subprocess.run(c,cwd=repo,text=True,capture_output=True);assert r.returncode==0,r.stderr
 return {'command':c,'stdout':r.stdout}
rows=[call(old,'init'),call(old,'learn-path','--path','.','--json')]
def snapshot():
 db=next(memory.glob('projects/*/memory.db'))
 with sqlite3.connect(db) as connection:
  connection.row_factory=sqlite3.Row
  return {'user_version':connection.execute('pragma user_version').fetchone()[0],
   'schema':[(r[0],r[1]) for r in connection.execute("select name,sql from sqlite_master where type='table' order by name")],
   'symbols':[dict(r) for r in connection.execute('select symbol_key,file_path,symbol,start_line,end_line,source_digest,semantic_adapter,callable_roles from code_symbols order by symbol_key')]}
old_snapshot=snapshot()
query=m.QUERIES[0]
rows+=[call(old,'context','--query',query,'--compact','--json'),call(new,'context','--query',query,'--compact','--json')]
rows+=[call(new,'learn-path','--path','.','--json'),call(new,'context','--query',query,'--compact','--json')]
(ROOT/'index-upgrade-symbols.json').write_text(json.dumps({'before':old_snapshot,'after':snapshot()},indent=2))
(ROOT/'index-upgrade.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
for i in (2,3,5):print(i,[a['file_path'] for a in json.loads(rows[i]['stdout'])['query_handoff']['code_anchors']])
