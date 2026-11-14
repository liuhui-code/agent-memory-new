import sys,runpy,json,copy
from pathlib import Path
out=Path(sys.argv.pop(1));entry=sys.argv[1];sys.argv=sys.argv[1:];sys.path[:0]=[str(Path(entry).resolve().parent),str(Path(entry).resolve().parents[1])];rows=[]
def profile(frame,event,arg):
 if event=='return' and frame.f_code.co_name in {'bind_recovery_pair','bind_from_rows','valid','accepted_output'} and frame.f_code.co_filename.endswith('query_recovery_pair.py'):
  loc=frame.f_locals
  rows.append(copy.deepcopy({'function':frame.f_code.co_name,'line':frame.f_lineno,'result_type':type(arg).__name__,'result_bool':arg if type(arg)is bool else None,'query':loc.get('query'),'roles':loc.get('roles'),'receipts':loc.get('receipts'),'observed':loc.get('observed'),'certified':sorted(loc.get('certified')or[]),'item':loc.get('item'),'anchors':(loc.get('handoff')or{}).get('code_anchors')}))
sys.setprofile(profile)
try:runpy.run_path(entry,run_name='__main__')
finally:sys.setprofile(None);out.write_text(json.dumps(rows,indent=2))
