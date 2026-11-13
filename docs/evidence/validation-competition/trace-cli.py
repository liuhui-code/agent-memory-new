# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import sys,runpy,json,os
from pathlib import Path
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tools'))
names={'focus_code_candidates','strongest_owner_contract_candidates','strongest_semantic_behavior_candidates','strongest_method_evidence_candidates','strongest_structural_candidates','preserve_salient_evidence_candidates','preserve_structural_boundary_neighbors','diverse_code_matches','focus_callable_anchors'}
rows=[]
def safe(v):
 if isinstance(v,dict):return {k:safe(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [safe(x) for x in v]
 return v if isinstance(v,(str,int,float,bool,type(None))) else str(v)
def trace(frame,event,arg):
 if event=='return' and frame.f_code.co_name in names:
  rows.append({'function':frame.f_code.co_name,'result':safe(arg),'locals':safe(frame.f_locals)})
sys.setprofile(trace)
try:runpy.run_path('tools/agent_memory.py',run_name='__main__')
finally:
 sys.setprofile(None);Path(os.environ['TRACE_FILE']).write_text(json.dumps(rows,ensure_ascii=False,indent=2))
