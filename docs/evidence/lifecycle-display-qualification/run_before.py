import json,sys,subprocess,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[3];D=Path(__file__).resolve().parent;p=json.loads((D/'protocol.json').read_text());E=R.parent/'lifecycle-display-current-before';root=E/'project';home=E/'memory';root.mkdir(parents=True);out={};commands=[]
for n,s in p['sources'].items():
 assert hashlib.sha256(s.encode()).hexdigest()==p['source_hashes'][n];(root/n).write_text(s)
for name,args in [('init',['init']),('learn',['learn-path','--path','.','--json']),('raw',['context','--query',p['query'],'--json']),('compact',['context','--query',p['query'],'--compact','--json'])]:
 cmd=[sys.executable,str(R/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',str(home)];r=subprocess.run(cmd,text=True,capture_output=True,cwd=R);commands.append(dict(command=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;out[name]=r.stdout if name=='init'else json.loads(r.stdout)
(D/'before.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');(D/'before-commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n');print(out['compact']['output_budget']);print([(a['file_path'],a.get('symbol'),[(e.get('symbol'),e['start_line'],e['end_line'])for e in a.get('source_excerpts',[])])for a in out['compact']['query_handoff']['code_anchors']])
