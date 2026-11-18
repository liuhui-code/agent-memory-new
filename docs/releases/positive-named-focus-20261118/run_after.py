import pathlib,json,subprocess,shutil,hashlib
base=pathlib.Path(__file__).resolve().parent
protocol=json.loads((base/'protocol.json').read_text())
project=base/'source';entry=base.parent/'repo/tools/agent_memory.py'
out=base/'after';out.mkdir(exist_ok=False)
commands=[]
for name,query in protocol['queries']:
 home=base/('after-home-'+name);shutil.copytree(base/'seed',home)
 args=['python3','-B',str(entry),'context','--project',str(project),'--memory-home',str(home),'--query',query,'--json']
 r=subprocess.run(args,capture_output=True,text=True)
 (out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr)
 commands.append({'name':name,'args':args,'rc':r.returncode});(out/'commands.json').write_text(json.dumps(commands,indent=2))
 if r.returncode:raise SystemExit('STOP '+name)
for name,q in protocol['queries']:
 d=json.load(open(out/(name+'.stdout')));print(name,[(x['file_path'],x.get('symbol')) for x in d['query_handoff']['code_anchors']])
