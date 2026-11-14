import json
from pathlib import Path
from types import SimpleNamespace
from tools.agent_memory_runtime.query_recovery_pair import bind_from_rows,valid,accepted_output,current_sources
from tools.agent_memory_runtime.context_compact import _compact_context
D=Path('docs/evidence/recovery-role-feasibility');x=json.loads((D/'after899-public.json').read_text())[0]
data=x['raw'];rows=x['symbols'];p=SimpleNamespace(root=Path(data['project_path']),project_id=data['project_id']);h=bind_from_rows(p,data['query'],data['query_handoff'],rows,[r for r in rows if r['symbol_type']=='class']);print('type',type(h).__name__,'valid',valid(h,h['code_anchors'],data['query']))
base=_compact_context(data);cand=_compact_context({**data,'query_handoff':h});print('accepted',accepted_output(h,base,cand),'budget',cand['output_budget']);old=base['query_handoff'];new=cand['query_handoff']
for k in ['log_keywords','log_anchors','path_context','relation_hints']:print(k,old.get(k)==new.get(k))
for a in old['code_anchors']:
 matches=[b for b in new['code_anchors'] if b['file_path']==a['file_path']];print('normal',a['file_path'],len(matches), matches==[a]);
 if matches:
  for k in set(a)|set(matches[0]):
   if a.get(k)!=matches[0].get(k):print('diff',k,a.get(k),matches[0].get(k))
(D/'after899-internal-projection.json').write_text(json.dumps({'baseline':base,'candidate':cand},indent=2))
