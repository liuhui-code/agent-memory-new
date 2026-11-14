import sys,runpy,json,copy
from pathlib import Path
out=Path(sys.argv.pop(1));entry=sys.argv[1];sys.argv=sys.argv[1:];sys.path[:0]=[str(Path(entry).resolve().parent),str(Path(entry).resolve().parents[1])];rows=[]
def profile(frame,event,arg):
 if event=='return' and frame.f_code.co_name in {'bind_render_context','enrich_render_context'}:
  loc=frame.f_locals
  rows.append(copy.deepcopy({'function':frame.f_code.co_name,'line':frame.f_lineno,'result_type':type(arg).__name__,'paths':loc.get('paths'),'parsed':loc.get('parsed'),'baseline_anchors':(loc.get('baseline',{}).get('query_handoff')or{}).get('code_anchors'),'trial_anchors':(loc.get('trial',{}).get('query_handoff')or{}).get('code_anchors')}))
sys.setprofile(profile)
try:runpy.run_path(entry,run_name='__main__')
finally:sys.setprofile(None);out.write_text(json.dumps(rows,indent=2))
