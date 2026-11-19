from pathlib import Path
import json,subprocess
O=Path(__file__).resolve().parent;R=O.parent/'repo';P=json.loads((O/'protocol.json').read_text());out=[]
for c in P['cases']:
 root=O/c['id'];root.mkdir();home=O/(c['id']+'-memory')
 for f,s in c['sources'].items():(root/f).write_text(s)
 def run(args):
  p=subprocess.run(['python','-B',str(R/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',str(home)],capture_output=True,text=True);assert p.returncode==0,p.stderr;return json.loads(p.stdout)if '--json'in args else p.stdout
 run(['init']);run(['learn-path','--path',str(root)])
 for q in c['queries']:
  vals={mode:run(['context','--query',q['query'],'--json']+(['--compact','--compact-token-budget','2000','--preserve-selected-source-anchors']if mode=='compact'else[]))for mode in ('raw','compact')};out.append(dict(fixture=c['id'],query=q,outputs=vals));print(c['id'],q['id'],[a['file_path']for a in vals['compact']['query_handoff']['code_anchors']],flush=True)
(O/'baseline.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
