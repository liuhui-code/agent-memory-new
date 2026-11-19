import json,subprocess,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parent/'repo'
queries=['Locate the BulletinRecord entity definition.','Locate BulletinPanel.cleanBody source.','Locate the BulletinPanel rendering owner rather than the BulletinRecord data entity.','Find the string "BulletinRecord data entity" in source.','Locate both BulletinRecord and BulletinPanel.cleanBody source.','Locate the data entity that calls BulletinPanel.cleanBody.']
s=json.dumps(queries,indent=2);(O/'controls.json').write_text(s);(O/'controls.sha256').write_text(hashlib.sha256(s.encode()).hexdigest())
out=[]
for q in queries:
 p=subprocess.run(['python','-B',str(R/'tools/agent_memory.py'),'context','--query',q,'--json','--compact','--project',str(O/'Bulletin'),'--memory-home',str(O/'Bulletin-memory')],capture_output=True,text=True);assert p.returncode==0,p.stderr;x=json.loads(p.stdout);out.append({'query':q,'output':x});print(q,[a['file_path']for a in x['query_handoff']['code_anchors']])
(O/'controls-before.json').write_text(json.dumps(out,indent=2))
