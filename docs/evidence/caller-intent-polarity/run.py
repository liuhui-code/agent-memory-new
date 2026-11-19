from pathlib import Path
import json,subprocess
B=Path(__file__).resolve().parent.parent;O=Path(__file__).resolve().parent;R=B/'repo';src=O/'source';src.mkdir(exist_ok=True)
p=json.load(open(R/'docs/eval/indirect-caller-current/protocol.json'))
for n,s in p['sources'].items():(src/n).write_text(s)
qs=['Find ModalBridge implementation.','Find ModalBridge implementation. Do not return actual caller context.','Find ModalBridge implementation, not the actual caller context.','Find the actual caller of ModalBridge.finish.','Find the actual caller of ModalBridge.finish, not the controller implementation.']
(O/'FREEZE.json').write_text(json.dumps({'source':str(R/'docs/eval/indirect-caller-current/protocol.json'),'queries':qs,'hypothesis':'Negated caller role must not activate caller-only focus; positive caller requests retained. Public CLI exploratory Development; no original acceptance claim.'},indent=2))
base=['python','-B',str(R/'tools/agent_memory.py')];tail=['--project',str(src),'--memory-home',str(O/'memory')]
for cmd in [['init'],['learn-path','--path','.']]:
 r=subprocess.run(base+cmd+tail,capture_output=True,text=True);assert r.returncode==0,r.stderr
for i,q in enumerate(qs):
 c=base+['context','--query',q,'--json']+tail;r=subprocess.run(c,capture_output=True,text=True);(O/f'{i}.json').write_text(r.stdout);(O/f'{i}.stderr').write_text(r.stderr);print(i,r.returncode)
 if r.returncode==0:
  d=json.loads(r.stdout);print([(a.get('file_path'),a.get('source'),a.get('symbol'))for a in d['query_handoff']['code_anchors']]);print(d['query_handoff'].get('callable_evidence'))
