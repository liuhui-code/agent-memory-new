import pathlib,json,subprocess,shutil
p=pathlib.Path(__file__).resolve().parent;h=p/'final-home';shutil.copytree(p/'seed',h);out=p/'final';out.mkdir(exist_ok=False);commands=[]
def run(name,args):
 full=['python3','-B',str(p.parent/'repo/tools/agent_memory.py'),*args,'--project',str(p/'source'),'--memory-home',str(h)];r=subprocess.run(full,capture_output=True,text=True);(out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr);commands.append({'name':name,'args':full,'rc':r.returncode});(out/'commands.json').write_text(json.dumps(commands,indent=2))
 if r.returncode:raise SystemExit('STOP '+name)
run('installed-before-refresh',['list','--type','code-file','--limit','100','--json'])
run('learn',['learn-path','--path','src','--json'])
run('list',['list','--type','code-file','--limit','100','--json'])
for name,query in json.loads((p/'protocol.json').read_text())['queries']:run(name,['context','--query',query,'--json'])
