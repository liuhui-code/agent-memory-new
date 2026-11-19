import json,subprocess
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parent/'repo';out=[]
for c in json.loads((O/'protocol.json').read_text())['cases']:
 for q in c['queries']:
  p=subprocess.run(['python','-B',str(R/'tools/agent_memory.py'),'context','--query',q['query'],'--json','--compact','--project',str(O/c['id']),'--memory-home',str(O/(c['id']+'-memory'))],capture_output=True,text=True);assert p.returncode==0,p.stderr;x=json.loads(p.stdout);out.append(dict(fixture=c['id'],query=q,output=x));print(c['id'],q['id'],x['output_budget']['estimated_tokens'],[(a['file_path'],[(e['start_line'],e['end_line'],e['truncated'])for e in a.get('source_excerpts',[])])for a in x['query_handoff']['code_anchors']],flush=True)
(O/'after.json').write_text(json.dumps(out,indent=2))
controls=[]
for q in json.loads((O/'controls.json').read_text()):
 p=subprocess.run(['python','-B',str(R/'tools/agent_memory.py'),'context','--query',q,'--json','--compact','--project',str(O/'Bulletin'),'--memory-home',str(O/'Bulletin-memory')],capture_output=True,text=True);assert p.returncode==0,p.stderr;controls.append(dict(query=q,output=json.loads(p.stdout)))
(O/'controls-after.json').write_text(json.dumps(controls,indent=2))
