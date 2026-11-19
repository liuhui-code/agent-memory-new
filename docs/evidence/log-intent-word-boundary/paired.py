from pathlib import Path
import json,subprocess,shutil
O=Path(__file__).resolve().parent;B=O.parent;R=B/'repo';qs=json.load(open(O/'FREEZE.json'))['queries'];seed=O/'seed';shutil.copytree(O/'memory',seed);summary=[]
for arm in ['legacy','current']:
 for i,q in enumerate(qs):
  for mode in ['raw','compact']:
   home=O/f'{arm}-{i}-{mode}-home';shutil.copytree(seed,home);c=['python','-B',str(O/'legacy-intent.py')if arm=='legacy'else str(R/'tools/agent_memory.py'),'context','--project',str(O/'source'),'--memory-home',str(home),'--query',q,'--json']+(['--compact']if mode=='compact'else[]);r=subprocess.run(c,capture_output=True,text=True);(O/f'{arm}-{i}-{mode}.json').write_text(r.stdout);(O/f'{arm}-{i}-{mode}.stderr').write_text(r.stderr);assert r.returncode==0,r.stderr
for i,q in enumerate(qs):
 for mode in ['raw','compact']:
  a=json.load(open(O/f'legacy-{i}-{mode}.json'));b=json.load(open(O/f'current-{i}-{mode}.json'));summary.append(dict(query=i,mode=mode,equal=a==b,before_intent=a.get('memory_intent_v2',a['memory_intent']),after_intent=b.get('memory_intent_v2',b['memory_intent']),before_refs=a['query_handoff']['experience_refs'],after_refs=b['query_handoff']['experience_refs']))
(O/'paired-summary.json').write_text(json.dumps(summary,indent=2));print([(r['query'],r['mode'],r['equal'],r['after_intent'])for r in summary])
