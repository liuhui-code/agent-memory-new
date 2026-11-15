import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];D=Path(__file__).resolve().parent;p=json.loads((D/'protocol.json').read_text());E=R.parent/'disclosure-lexical-readonly';root=E/'project';home=E/'memory';root.mkdir(parents=True);out={};commands=[]
for n,s in p['sources'].items():(root/n).write_text(s)
for name,args in [('init',['init']),('learn',['learn-path','--path','.','--json']),('raw',['context','--query',p['query'],'--json']),('compact',['context','--query',p['query'],'--compact','--json'])]:
 cmd=[sys.executable,str(R/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',str(home)];r=subprocess.run(cmd,cwd=R,text=True,capture_output=True);commands.append(dict(command=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0;out[name]=r.stdout if name=='init' else json.loads(r.stdout)
(D/'before.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');(D/'commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
for row in out['raw']['wiki_matches']:print(row.get('file_path'),row.get('summary'),row.get('score'))
