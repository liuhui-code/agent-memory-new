import pathlib,json,shutil,subprocess,sys
b=pathlib.Path('/workspace/scratch/dcdb41e16594/concrete-resume-20261119');o=b/'recall-audit13/body-controls-final';o.mkdir(exist_ok=True);protocol=json.loads((b/'default-field-followup/protocol.json').read_text());results=[]
runner="import sys,runpy;sys.path.insert(0,sys.argv[1]+'/tools');import agent_memory_runtime.context_graph_field_body as f;from agent_memory_runtime.context_graph_field_followup import append_graph_field_followup;f.append_graph_field_display=lambda p,o,d,**kw:append_graph_field_followup(p,o,d);p=sys.argv.pop(1)+'/tools/agent_memory.py';sys.argv[0]=p;runpy.run_path(p,run_name='__main__')"
for n,c in protocol['controls'].items():
 for mode,flags in [('default',['--compact']),('explicit1500',['--compact','--compact-token-budget','1500']),('plain2000',['--compact','--compact-token-budget','2000']),('preserve2000',['--compact','--compact-token-budget','2000','--preserve-selected-source-anchors']),('raw',[])]:
  for arm in ['before','after']:
   tag=f'{n}-{mode}-{arm}';home=o/(tag+'-memory');shutil.copytree(b/'default-field-followup'/n/'seed',home)
   cmd=([sys.executable,'-c',runner,str(b/'repo')] if arm=='before' else [sys.executable,str(b/'repo/tools/agent_memory.py')])+['context','--query',c['query'],'--project',str(b/'default-field-followup'/n/'source'),'--memory-home',str(home),'--json',*flags]
   p=subprocess.run(cmd,capture_output=True,text=True);(o/(tag+'.json')).write_text(p.stdout);(o/(tag+'.stderr')).write_text(p.stderr);results.append(dict(tag=tag,cmd=cmd,rc=p.returncode))
(o/'commands.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print('done',len(results), 'fail',sum(x['rc']!=0 for x in results))
