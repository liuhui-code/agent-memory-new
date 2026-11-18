import pathlib,json,subprocess,shutil
p=pathlib.Path(__file__).resolve().parent
for mode,entry in [('compact-before',p/'baseline-runtime/tools/agent_memory.py'),('compact-after',p.parent/'repo/tools/agent_memory.py')]:
 out=p/mode;out.mkdir(exist_ok=False);cmds=[]
 for name,query in json.loads((p/'protocol.json').read_text())['queries']:
  home=p/(mode+'-home-'+name);shutil.copytree(p/'seed',home);args=['python3','-B',str(entry),'context','--project',str(p/'source'),'--memory-home',str(home),'--query',query,'--compact','--json'];r=subprocess.run(args,capture_output=True,text=True);(out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr);cmds.append({'name':name,'args':args,'rc':r.returncode});(out/'commands.json').write_text(json.dumps(cmds,indent=2))
  if r.returncode:raise SystemExit('STOP '+mode+name)
for name,_ in json.loads((p/'protocol.json').read_text())['queries']:
 b=json.loads((p/'compact-before'/f'{name}.stdout').read_text());a=json.loads((p/'compact-after'/f'{name}.stdout').read_text());print(name,b['output_budget'],a['output_budget']);bh,ah=b['query_handoff'],a['query_handoff'];print('anchors unchanged',bh['code_anchors']==ah['code_anchors'],'primary same',bh['callable_evidence']['primary']==ah['callable_evidence']['primary'],'alternatives',ah['callable_evidence']['alternatives'])
