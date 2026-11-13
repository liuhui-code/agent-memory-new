# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import sys,os,json,runpy
from pathlib import Path
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tools'))
names={'focus_code_candidates','preserve_structural_boundary_neighbors','preserve_salient_evidence_candidates','diverse_code_matches','admitted_log_owners','focus_callable_anchors','path_scoped_code_anchors','rank_callables'}
rows=[]
def safe(v):
 if isinstance(v,dict):return {k:safe(x)for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [safe(x)for x in v]
 return v if isinstance(v,(str,int,float,bool,type(None)))else str(v)
def trace(frame,event,arg):
 if event=='return'and frame.f_code.co_name in names:rows.append({'function':frame.f_code.co_name,'input':safe(frame.f_locals),'result':safe(arg)})
sys.setprofile(trace)
try:runpy.run_path('tools/agent_memory.py',run_name='__main__')
finally:
 sys.setprofile(None);Path(os.environ['TRACE_FILE']).write_text(json.dumps(rows,indent=2))
