from pathlib import Path
import json,subprocess,hashlib
O=Path(__file__).resolve().parent;R=O.parent/'repo';S=O/'standard-source';S.mkdir()
for r in json.loads((O/'materialized-files.json').read_text()):
 data=(O.parent/'original13/source'/r['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==r['sha256'];p=S/r['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
H=O/'explicit-memory'
def run(args):
 p=subprocess.run(['python','-B',str(R/'tools/agent_memory.py'),*args,'--project',str(S),'--memory-home',str(H)],capture_output=True,text=True);assert p.returncode==0,p.stderr;return p.stdout
run(['init']);run(['wiki-index'])
for n in (1,3):
 q=json.loads((O/f'captured-{n}.json').read_text())['query'];out=run(['context','--query',q,'--compact','--compact-token-budget','2000','--preserve-selected-source-anchors','--json']);(O/f'explicit-{n}.json').write_text(out);x=json.loads(out);print(n,x['output_budget'],[(a['file_path'],[(e['start_line'],e['end_line'],e.get('truncated'))for e in a.get('source_excerpts',[])])for a in x['query_handoff']['code_anchors']],flush=True)
