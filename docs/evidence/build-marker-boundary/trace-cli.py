# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy,json,runpy,sys
from pathlib import Path
runtime,out,*args=sys.argv[1:];rows=[]
WATCH={'structural_boundary_query','preserve_structural_boundary_neighbors','focus_code_candidates','collect_graph_neighbor_matches','promote_neighbor','builder_anchors'}
def observe(frame,event,arg):
 if event=='return' and frame.f_code.co_name in WATCH and 'agent_memory_runtime' in frame.f_code.co_filename:
  keys=('query','focused','recalled','wiki_matches','edges','origin','neighbor','edge','reverse','matched')
  rows.append({'function':frame.f_code.co_name,'return_line':frame.f_lineno,'returned':copy.deepcopy(arg),**{k:copy.deepcopy(frame.f_locals.get(k))for k in keys}})
 return observe
sys.argv=[runtime,*args];sys.path.insert(0,str(Path(runtime).parent));sys.setprofile(observe)
try:runpy.run_path(runtime,run_name='__main__')
finally:
 sys.setprofile(None);Path(out).write_text(json.dumps(rows,indent=2,ensure_ascii=False))
