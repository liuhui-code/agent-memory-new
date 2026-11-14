import sys,runpy,time,json
from pathlib import Path
out=Path(sys.argv.pop(1));entry=sys.argv[1];sys.argv=sys.argv[1:];sys.path.insert(0,str(Path(entry).resolve().parent));sys.path.insert(0,str(Path(entry).resolve().parents[1]));counts={};start=time.perf_counter()
def profile(frame,event,arg):
 if event=='call' and frame.f_code.co_name in {'collect_matches_with_audit','record_context_use','record_query_miss_if_empty','_context_pass','_compact_context'}:
  name=frame.f_code.co_name;counts[name]=counts.get(name,0)+1
sys.setprofile(profile)
try:runpy.run_path(entry,run_name='__main__')
finally:
 sys.setprofile(None);out.write_text(json.dumps({'calls':counts,'elapsed_seconds':time.perf_counter()-start},indent=2))
