# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(ROOT))
from tools.agent_memory_runtime.benchmark_workspace import materialized_workspace
p=json.loads((D/'original-protocol.json').read_text());pack=json.loads((ROOT/'docs/eval/system-capability-cases.json').read_text());case=next(x for x in pack['cases']if x['id']==p['case_id']);result={}
with tempfile.TemporaryDirectory(prefix='builder-zh-original-')as t, materialized_workspace(ROOT/p['source'],case)as project:
 def cli(*args,trace=None):
  command=[sys.executable,str(ROOT/'tools/agent_memory.py')]
  if trace:command=[sys.executable,str(D/'trace-original-final.py'),str(ROOT/'tools/agent_memory.py'),str(D/trace)]
  r=subprocess.run([*command,*args,'--project',str(project),'--memory-home',str(Path(t)/'memory')],capture_output=True,text=True,check=True)
  return json.loads(r.stdout)if '--json'in args else r.stdout
 cli('init');result['learn']=cli('learn-path','--path','.','--json')
 result['symbols']=cli('list','--type','code-symbol','--limit','1000','--json')
 result['raw']=cli('context','--query',p['query'],'--json',trace='phase-r-original-raw-trace.json')
 result['compact']=cli('context','--query',p['query'],'--compact','--json',trace='phase-r-original-compact-trace.json')
 (D/'phase-r-original-diagnostic.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
 print([a['file_path']for a in result['compact']['query_handoff']['code_anchors']])
