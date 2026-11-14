# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import contextlib,io,json,runpy,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from tests.agent_memory_test_base import AgentMemoryTestBase
OUT=Path(__file__).resolve().parent; p=json.loads((ROOT/'docs/eval/indirect-caller-current/protocol.json').read_text()); b=AgentMemoryTestBase(); traces=[]
NAMES={'collect_bounded_caller_owners','focus_code_candidates','diverse_code_matches'}
def profile(frame,event,arg):
 if event=='return' and frame.f_code.co_name in NAMES:
  traces.append({'name':frame.f_code.co_name,'query':frame.f_locals.get('query'),'items':frame.f_locals.get('items'),'result':arg})
with tempfile.TemporaryDirectory(prefix='caller-direction-') as d:
 root=Path(d)
 for n,s in p['sources'].items():(root/n).write_text(s)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 sys.argv=[str(ROOT/'tools/agent_memory.py'),'context','--project',str(root),'--memory-home',str(b.memory_home(root)),'--query',p['queries'][2][1],'--json']
 stdout=io.StringIO();sys.setprofile(profile)
 try:
  with contextlib.redirect_stdout(stdout):
   try:runpy.run_path(str(ROOT/'tools/agent_memory.py'),run_name='__main__')
   except SystemExit as e:
    if e.code not in (None,0):raise
 finally:sys.setprofile(None)
 (OUT/'traced-public.json').write_text(stdout.getvalue())
 (OUT/'trace.json').write_text(json.dumps(traces,indent=2,default=str))
