# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Observe unchanged ranked callable return values; never alter runtime inputs."""
import json,runpy,sys
from pathlib import Path
runtime,out,*args=sys.argv[1:];rows=[]
def observe(frame,event,arg):
 if event=='return' and frame.f_code.co_name=='rank_callables' and frame.f_code.co_filename.endswith('query_hierarchical_localization.py'):
  rows.append({'query':frame.f_locals.get('query'),'rows':arg})
 return observe
sys.argv=[runtime,*args];sys.path.insert(0,str(Path(runtime).parent));sys.setprofile(observe)
try:runpy.run_path(runtime,run_name='__main__')
finally:
 sys.setprofile(None);Path(out).write_text(json.dumps(rows,indent=2,ensure_ascii=False))
