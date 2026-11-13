# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import sys,runpy,json,os
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
sys.path.insert(0,str(Path.cwd()/"tools"))
names={'collect_graph_neighbor_matches','component_lineage_candidates','boost_match','promote_neighbor','focus_code_candidates','preserve_salient_evidence_candidates','preserve_structural_boundary_neighbors','diverse_code_matches','focus_callable_anchors'}
rows=[]
def shrink(v):
 if isinstance(v,dict):return {k:shrink(x) for k,x in v.items() if k in {'file_path','symbol','record_type','score','reasons','summary','method_evidence','callable_roles','behavior_markers','source_range'}}
 if isinstance(v,(list,tuple)):return [shrink(x) for x in v]
 return v if isinstance(v,(str,int,float,bool,type(None))) else str(v)
def trace(frame,event,arg):
 if event=='return' and frame.f_code.co_name in names:
  if frame.f_code.co_name=='callable_behavior_hints':
   e=frame.f_locals.get('entity');p=str(getattr(e,'file_path',''))
   if 'AccountSettingsPage' not in p:return
  if frame.f_code.co_name == 'promote_neighbor':
   rows.append({'function':'promote_neighbor','origin':str(frame.f_locals.get('origin')),'neighbor':str(frame.f_locals.get('neighbor')),'score':frame.f_locals.get('score'),'matched':str(frame.f_locals.get('matched')),'edge':frame.f_locals.get('edge')});return
  rows.append({'function':frame.f_code.co_name,'result':shrink(arg),'query':frame.f_locals.get('query'),'input':shrink(frame.f_locals.get('items',frame.f_locals.get('entity')))})
sys.setprofile(trace)
try:runpy.run_path('tools/agent_memory.py',run_name='__main__')
finally:
 sys.setprofile(None)
 Path(os.environ['TRACE_FILE']).write_text(json.dumps(rows,indent=2))
