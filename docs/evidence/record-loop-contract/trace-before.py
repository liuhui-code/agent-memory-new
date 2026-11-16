# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import sys,runpy,json,copy
from pathlib import Path
out=Path(sys.argv.pop(1));entry=sys.argv[1];sys.argv=sys.argv[1:];sys.path.insert(0,str(Path(entry).resolve().parents[1]));sys.path.insert(0,str(Path(entry).resolve().parent));rows=[]
def profile(frame,event,arg):
 if event=='return' and frame.f_code.co_name in {'focus_callable_anchors','rank_callables','focus_code_candidates'}:
  rows.append(copy.deepcopy({'function':frame.f_code.co_name,'query':frame.f_locals.get('query'),'anchors':frame.f_locals.get('anchors'),'items':frame.f_locals.get('items'),'evidence':frame.f_locals.get('evidence'),'path_activated':frame.f_locals.get('path_activated'),'returned':arg,'return_line':frame.f_lineno}))
sys.setprofile(profile)
try:runpy.run_path(entry,run_name='__main__')
finally:
 sys.setprofile(None);out.write_text(json.dumps(rows,indent=2,ensure_ascii=False))
