import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];D=Path(__file__).resolve().parent;p=json.loads((D/'controls.json').read_text());phase=sys.argv[1];E=R.parent/('disclosure-lexical-controls-'+phase);root=E/'project';home=E/'memory';root.mkdir(parents=True);commands=[]
for n,s in p['sources'].items():(root/n).write_text(s)
def run(args):
 cmd=[sys.executable,str(R/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',str(home)];r=subprocess.run(cmd,cwd=R,text=True,capture_output=True);commands.append(dict(command=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout if args[0]=='init' else json.loads(r.stdout)
run(['init']);run(['learn-path','--path','.','--json']);files=run(['list','--type','code-file','--limit','100','--json']);out=[]
for q in p['queries']:out.append(dict(query=q,raw=run(['context','--query',q,'--json']),compact=run(['context','--query',q,'--compact','--json'])))
(D/('controls-'+phase+'.json')).write_text(json.dumps(dict(files=files,queries=out),ensure_ascii=False,indent=2)+'\n');(D/('controls-'+phase+'-commands.json')).write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
for f in files:print(f['file_path'],f['summary'])
