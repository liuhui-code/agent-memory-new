import json,subprocess,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parent/'repo';source=O.parent/'rather05-scope';queries=[]
for name in ('Bulletin','Invoice'):
 for kind,q in [('positive',f'Locate both {name}Record and {name}Panel.cleanBody source.'),('negative',f'Locate {name}Panel.cleanBody rather than {name}Record.'),('comparison',f'Locate {name}Panel.cleanBody compared with {name}Record.'),('quoted',f'Find the string "{name}Record and {name}Panel.cleanBody" in source.')]:queries.append(dict(name=name,kind=kind,query=q))
s=json.dumps(queries,indent=2);(O/'protocol.json').write_text(s);(O/'protocol.sha256').write_text(hashlib.sha256(s.encode()).hexdigest());out=[]
for row in queries:
 p=subprocess.run(['python','-B',str(R/'tools/agent_memory.py'),'context','--query',row['query'],'--json','--compact','--project',str(source/row['name']),'--memory-home',str(source/(row['name']+'-memory'))],capture_output=True,text=True);assert p.returncode==0,p.stderr;x=json.loads(p.stdout);out.append(dict(**row,output=x));print(row['name'],row['kind'],[a['file_path']for a in x['query_handoff']['code_anchors']],flush=True)
(O/'before.json').write_text(json.dumps(out,indent=2))
