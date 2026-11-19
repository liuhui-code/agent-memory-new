from pathlib import Path
import json,subprocess,shutil
B=Path(__file__).resolve().parent.parent;O=Path(__file__).resolve().parent;R=B/'repo';S=O/'source';S.mkdir(exist_ok=True)
paths=['src/entities/ProductRecord.ets','src/pages/ProductSearchPage.ets','src/services/ProductSearchService.ets']
for p in paths:
 f=S/p;f.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(B/'original13/source'/p,f)
qs=['Locate ProductRecord fields.','Locate ProductRecord fields. Do not return page handlers.','Locate ProductRecord fields, not page handlers.','Locate the ProductRecord entity definition and fields.','Locate the SQL parameter owner and page that renders product search results.']
(O/'FREEZE.json').write_text(json.dumps({'sources':paths,'queries':qs,'scope':'Exploratory independent Development public-output probe; no modification of original gate inputs or claims of original repair.'},indent=2));base=['python','-B',str(R/'tools/agent_memory.py')];tail=['--project',str(S),'--memory-home',str(O/'memory')]
for cmd in [['init'],['learn-path','--path','.']]:
 r=subprocess.run(base+cmd+tail,capture_output=True,text=True);assert r.returncode==0,r.stderr
for i,q in enumerate(qs):
 for mode in ['raw','compact']:
  r=subprocess.run(base+['context','--query',q,'--json']+tail+(['--compact']if mode=='compact'else[]),capture_output=True,text=True);(O/f'{i}-{mode}.json').write_text(r.stdout);(O/f'{i}-{mode}.stderr').write_text(r.stderr);d=json.loads(r.stdout);print(i,mode,[(a['file_path'],a.get('symbol'))for a in d['query_handoff']['code_anchors']])
