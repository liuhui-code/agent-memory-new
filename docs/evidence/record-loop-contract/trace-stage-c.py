import sys,runpy,json,copy
from pathlib import Path
out=Path(sys.argv.pop(1));entry=sys.argv[1];sys.argv=sys.argv[1:];sys.path.insert(0,str(Path(entry).resolve().parents[1]));sys.path.insert(0,str(Path(entry).resolve().parent));rows=[]
def profile(frame,event,arg):
 if event=='call' and frame.f_code.co_name=='qualify_context_trials':
  rows.append(copy.deepcopy({'event':'qualifier_entry','query':frame.f_locals.get('query'),'gated':frame.f_locals.get('gated')}))
 if event=='return' and frame.f_code.co_name=='focus_code_candidates':
  rows.append(copy.deepcopy({'event':'focus_return','query':frame.f_locals.get('query'),'items':frame.f_locals.get('items'),'returned':arg}))
sys.setprofile(profile)
try:runpy.run_path(entry,run_name='__main__')
finally:
 sys.setprofile(None);out.write_text(json.dumps(rows,indent=2,ensure_ascii=False))
