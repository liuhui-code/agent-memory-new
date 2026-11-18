import json,subprocess,concurrent.futures
from pathlib import Path
repo=Path.cwd();root=repo.parent/'command37-current/source';home=repo.parent/'command37-current/seed';out=repo.parent/'excerpt-audit';wanted={'context-combined-commit-owner-precision':'15','context-bounded-cache-eviction-owner':'33','context-command-binding-owner-precision':'37','context-comparison-target-visual-state-owner':'38'}
cases=[]
def walk(x):
 if isinstance(x,dict):
  if x.get('id')in wanted:cases.append(x)
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(json.loads((repo/'docs/eval/system-capability-cases.json').read_text()))
def run(item):
 c,v=item;n=wanted[c['id']]+'-'+v['id'];cmd=['python3','-B','tools/agent_memory.py','context','--project',str(root),'--memory-home',str(home),'--query',v['description'],'--compact','--json'];r=subprocess.run(cmd,capture_output=True,text=True);(out/(n+'.json')).write_text(r.stdout);(out/(n+'.stderr')).write_text(r.stderr)
 if r.returncode:return {'id':n,'error':r.stderr}
 x=json.loads(r.stdout);h=x['query_handoff'];expected=c['oracle']['expected_files'];return {'id':n,'budget':x.get('output_budget'),'primary':h.get('callable_evidence',{}).get('primary'),'targets':[{'path':a['file_path'],'excerpts':a.get('source_excerpts'),'ranges':a.get('source_ranges')}for a in h['code_anchors']if a['file_path']in expected],'oracle':c['oracle']['context_requirements']['required_source_spans']}
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:results=list(pool.map(run,[(c,v)for c in cases for v in c['query_variants']]))
(out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
for r in results:print(r['id'],[(a['path'],[(e.get('start_line'),e.get('end_line'),e.get('truncated'))for e in a['excerpts']])for a in r.get('targets',[])])
