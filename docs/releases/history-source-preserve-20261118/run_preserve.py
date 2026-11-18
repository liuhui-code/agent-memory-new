import pathlib,json,subprocess,shutil
p=pathlib.Path(__file__).resolve().parent;out=p/'preserve-correct';out.mkdir(exist_ok=False);cmds=[]
for name,query in json.loads((p/'protocol.json').read_text())['queries']:
 h=p/('preserve-correct-home-'+name);shutil.copytree(p/'seed',h);args=['python3','-B',str(p.parent/'repo/tools/agent_memory.py'),'context','--project',str(p/'source'),'--memory-home',str(h),'--query',query,'--compact','--preserve-selected-source-anchors','--compact-token-budget','2000','--json'];r=subprocess.run(args,capture_output=True,text=True);(out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr);cmds.append({'name':name,'args':args,'rc':r.returncode});(out/'commands.json').write_text(json.dumps(cmds,indent=2))
 if r.returncode:raise SystemExit('STOP '+name)
 d=json.loads(r.stdout);h=d['query_handoff'];pr=h.get('callable_evidence',{}).get('primary') or {};print(name,pr.get('symbol'),[(x.get('file_path'),x.get('symbol')) for x in h['code_anchors']],d['output_budget'])
