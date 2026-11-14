# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import contextlib,io,json,runpy,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from tools.agent_memory_runtime.benchmark_workspace import materialized_workspace
D=Path(__file__).resolve().parent;p=json.loads((D/'protocol.json').read_text());q=next(v['description'] for v in p['case']['query_variants'] if v['id']=='zh-noise');traces=[]
names={'project_code_exclusions','localization_input','code_anchors','focus_callable_anchors'}
def trace(f,event,arg):
 if event=='return' and f.f_code.co_name in names:
  vals={k:f.f_locals.get(k) for k in ('query','anchors','raw_candidates','raw_logs','path_context','wiki','logs','direct_scores_safe') if k in f.f_locals}
  traces.append(json.loads(json.dumps({'name':f.f_code.co_name,'args':vals,'result':arg},default=str)))
with tempfile.TemporaryDirectory(prefix='negative-memory-') as d, materialized_workspace(ROOT/p['source_project'],p['case']) as root:
 home=Path(d)
 for args in [('init',),('learn-path','--path','.')]:
  r=subprocess.run([sys.executable,str(ROOT/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',str(home)],capture_output=True,text=True,check=True)
 outputs={}
 for compact in (False,True):
  sys.argv=[str(ROOT/'tools/agent_memory.py'),'context','--project',str(root),'--memory-home',str(home),'--query',q,'--json']+(['--compact'] if compact else [])
  out=io.StringIO();sys.setprofile(trace)
  try:
   with contextlib.redirect_stdout(out):
    try:runpy.run_path(str(ROOT/'tools/agent_memory.py'),run_name='__main__')
    except SystemExit as e:
     if e.code not in (None,0):raise
  finally:sys.setprofile(None)
  outputs['compact' if compact else 'raw']=json.loads(out.getvalue())
 (D/'public.json').write_text(json.dumps(outputs,indent=2,ensure_ascii=False))
 (D/'trace.json').write_text(json.dumps(traces,indent=2,ensure_ascii=False))
