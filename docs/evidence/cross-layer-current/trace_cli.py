# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,os,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
NAMES={'focus_code_candidates','preserve_salient_evidence_candidates','callable_evidence','focus_callable_anchors','rank_callables','build_callable_passage_portfolio','load_file_callables'}
events=[]
def observer(frame,event,arg):
    if event=='return'and frame.f_code.co_name in NAMES and 'agent_memory_runtime'in frame.f_code.co_filename:
        events.append({'function':frame.f_code.co_name,'file':Path(frame.f_code.co_filename).name,'result':arg})
sys.argv=[str(ROOT/'tools/agent_memory.py'),*sys.argv[1:]];sys.path.insert(0,str(ROOT/'tools'));sys.setprofile(observer)
try:runpy.run_path(str(ROOT/'tools/agent_memory.py'),run_name='__main__')
finally:
    sys.setprofile(None);Path(os.environ['TRACE_OUT']).write_text(json.dumps(events,default=str,indent=2))
