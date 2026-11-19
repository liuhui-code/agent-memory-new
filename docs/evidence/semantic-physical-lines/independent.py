from pathlib import Path
import subprocess,json
O=Path(__file__).resolve().parent; R=O.parent/'repo'
source="export class QueuePolicy {\n  label: string = `Queue\u2029policy`\n  permits(items: string[]): boolean {\n    if (items.length > 5) { return false }\n    return true\n  }\n}\n"
query='Locate QueuePolicy.permits size guard source.'
root=O/'queue';root.mkdir(exist_ok=True);(root/'QueuePolicy.ts').write_text(source)
(O/'INDEPENDENT-FREEZE.json').write_text(json.dumps(dict(source=source,query=query),indent=2))
for label,runtime in [('baseline',O/'baseline-runtime'),('candidate',R)]:
 cli=['python','-B',str(runtime/'tools/agent_memory.py')];tail=['--project',str(root),'--memory-home',str(O/('queue-'+label+'-memory'))]
 for cmd in [['init'],['learn-path','--path','.']]:
  p=subprocess.run(cli+cmd+tail,capture_output=True,text=True);assert p.returncode==0,p.stderr
 p=subprocess.run(cli+['context','--query',query,'--compact','--json']+tail,capture_output=True,text=True);assert p.returncode==0,p.stderr
 (O/('queue-'+label+'.json')).write_text(p.stdout)
 d=json.loads(p.stdout);print(label,[(a['symbol'],a.get('source_ranges'))for a in d['query_handoff']['code_anchors']])
