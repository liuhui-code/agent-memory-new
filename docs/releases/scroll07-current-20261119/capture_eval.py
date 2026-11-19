from pathlib import Path
import sys,runpy,json,hashlib,sqlite3
O=Path(__file__).resolve().parent;R=O.parent/'repo';sys.path.insert(0,str(R/'tools'))
import agent_memory_runtime.context_capability as c
original=c.run_context_query;counter=0

def captured(command,query,workspace,timeout):
 global counter
 counter+=1
 d=original(command,query,workspace,timeout)
 (O/f'captured-{counter}.json').write_text(json.dumps(dict(command=command,query=query,payload=d),ensure_ascii=False,indent=2))
 if counter==1:
  files=[dict(path=p.relative_to(workspace).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in workspace.rglob('*')if p.is_file()];(O/'materialized-files.json').write_text(json.dumps(files,indent=2))
 return d
c.run_context_query=captured
sys.argv=[str(R/'tools/agent_memory.py'),'eval-context-capability','--cases',str(R/'docs/eval/system-capability-cases.json'),'--case-id','context-abstract-scroll-structure','--source',str(O.parent/'original13/source'),'--project',str(O/'captured-project'),'--memory-home',str(O/'captured-memory'),'--json']
runpy.run_path(sys.argv[0],run_name='__main__')
