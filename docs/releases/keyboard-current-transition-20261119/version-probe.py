from pathlib import Path
import json,subprocess,sys,hashlib
O=Path(__file__).resolve().parent;R=O.parent/'repo';src=O/'standard-source'
if not src.exists():
 src.mkdir()
 for r in json.loads((O/'materialized-files.json').read_text()):
  data=(O.parent/'original13/source'/r['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==r['sha256'];p=src/r['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
q=json.loads((O/'captured-3.json').read_text())['query']
for ref in sys.argv[1:]:
 base=O/('version-'+ref);base.mkdir();rt=base/'runtime';rt.mkdir();a=base/'code.tar'
 with a.open('wb')as f:subprocess.run(['git','archive',ref,'tools'],cwd=R,stdout=f,check=True)
 subprocess.run(['tar','-xf',str(a),'-C',str(rt)],check=True);cli=rt/'tools/agent_memory.py';home=base/'memory'
 for label,args in [('init',['init']),('index',['wiki-index']),('compact',['context','--query',q,'--compact','--json']),('raw',['context','--query',q,'--json'])]:
  p=subprocess.run(['python','-B',str(cli),*args,'--project',str(src),'--memory-home',str(home)],capture_output=True,text=True);(base/(label+'.stdout')).write_text(p.stdout);(base/(label+'.stderr')).write_text(p.stderr);assert p.returncode==0,p.stderr
 x=json.loads((base/'compact.stdout').read_text());print(ref,[v['file_path']for v in x['query_handoff']['code_anchors']],x['output_budget'],flush=True)
