from pathlib import Path
import json,subprocess,shutil
O=Path(__file__).resolve().parent;B=O.parent;R=B/'repo';qs=json.load(open(O/'FREEZE.json'))['queries']+json.load(open(O/'additional-controls-freeze.json'));summary=[];seed=O/'frozen-seed';shutil.copytree(O/'memory',seed)
for arm in ['legacy','current']:
 for i,q in enumerate(qs):
  for mode in ['raw','compact']:
   home=O/f'fresh-{arm}-{i}-{mode}-home';shutil.copytree(seed,home)
   c=['python','-B',str(O/'legacy-gate.py')if arm=='legacy'else str(R/'tools/agent_memory.py'),'context','--project',str(O/'source'),'--memory-home',str(home),'--query',q,'--json']+(['--compact']if mode=='compact'else[])
   r=subprocess.run(c,capture_output=True,text=True);(O/f'fresh-{arm}-{i}-{mode}.json').write_text(r.stdout);(O/f'fresh-{arm}-{i}-{mode}.stderr').write_text(r.stderr);assert r.returncode==0,r.stderr
for i,q in enumerate(qs):
 for mode in ['raw','compact']:
  a=json.load(open(O/f'fresh-legacy-{i}-{mode}.json'));b=json.load(open(O/f'fresh-current-{i}-{mode}.json'));summary.append({'query':i,'mode':mode,'exact_equal':a==b,'before':[a['file_path']for a in a['query_handoff']['code_anchors']],'after':[a['file_path']for a in b['query_handoff']['code_anchors']]})
(O/'fresh-pairs-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
