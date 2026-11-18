from pathlib import Path
import json,sys,subprocess,shutil,copy
b=Path(__file__).resolve().parent;r=b.parent/'repo';p=json.loads((b/'protocol.json').read_text());o=b/'final-controls';o.mkdir(exist_ok=True);commands=[];results=[]
for group in ['positive_queries','negative_queries']:
 for i,q in enumerate(p[group]):
  docs=[]
  for arm,script in [('before',b/'disabled.py'),('after',r/'tools/agent_memory.py')]:
   stem=f'{group}-{i}-{arm}';h=o/(stem+'-home');shutil.copytree(b/'seed',h)
   cmd=[sys.executable,'-B',str(script),'context','--project',str(b/'source'),'--memory-home',str(h),'--query',q,'--compact','--json'];x=subprocess.run(cmd,capture_output=True,text=True);assert x.returncode==0,x.stderr
   (o/(stem+'.json')).write_text(x.stdout);(o/(stem+'.stderr')).write_text(x.stderr);docs.append(json.loads(x.stdout));commands.append(dict(group=group,index=i,arm=arm,command=cmd,rc=x.returncode))
  a,d=docs;restore=copy.deepcopy(d)
  for key in ['code_anchors','source_excerpt_policy']:restore['query_handoff'][key]=a['query_handoff'][key]
  restore['output_budget']=a['output_budget'];assert restore==a
  if group=='negative_queries':assert a==d
  results.append(dict(group=group,index=i,before=a['output_budget'],after=d['output_budget'],unchanged=a==d,all_old_evidence_unchanged=restore==a,added=d['query_handoff']['code_anchors'][len(a['query_handoff']['code_anchors']):]))
(o/'commands.json').write_text(json.dumps(commands,indent=2));(o/'results.json').write_text(json.dumps(results,indent=2));print('40 CLI outputs; old evidence preserved; all negatives unchanged')
