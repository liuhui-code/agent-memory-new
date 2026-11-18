import pathlib, json, subprocess, shutil, hashlib
base=pathlib.Path(__file__).resolve().parent
protocol=json.loads((base/'protocol.json').read_text())
project=base/'source'; project.mkdir(exist_ok=False)
for path,content in protocol['sources'].items():
 p=project/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
entry=base.parent/'repo/tools/agent_memory.py'
seed=base/'seed'
steps=[]
def run(label,args):
 r=subprocess.run(['python3','-B',str(entry),*args],capture_output=True,text=True)
 (base/(label+'.stdout')).write_text(r.stdout);(base/(label+'.stderr')).write_text(r.stderr)
 steps.append({'label':label,'args':args,'rc':r.returncode}); (base/'commands.json').write_text(json.dumps(steps,indent=2))
 if r.returncode: raise SystemExit('STOP '+label)
 return r
run('init',['init','--project',str(project),'--memory-home',str(seed)])
run('learn',['learn-path','--project',str(project),'--memory-home',str(seed),'--path','src','--json'])
for name,query in protocol['queries']:
 home=base/('home-'+name);shutil.copytree(seed,home)
 run(name,['context','--project',str(project),'--memory-home',str(home),'--query',query,'--json'])
print(json.dumps(steps,indent=2))
