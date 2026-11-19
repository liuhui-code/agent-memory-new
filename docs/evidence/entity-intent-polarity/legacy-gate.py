import sys,runpy
from pathlib import Path
R=Path(__file__).resolve().parent.parent/'repo';sys.path.insert(0,str(R/'tools'))
import agent_memory_runtime.query_code_selection as q
# Exact pre-change role-gate implementations only; no retrieval/score stubs.
import subprocess
namespace={'re':q.re}
source=subprocess.check_output(['git','show','HEAD:tools/agent_memory_runtime/query_code_selection.py'],cwd=R,text=True)
for name in ('behavior_owner_query','entity_definition_query'):
 start=source.index('def '+name+'(');end=source.index('\n\ndef ',start);exec(source[start:end],namespace);setattr(q,name,namespace[name])
sys.argv=[str(R/'tools/agent_memory.py'),*sys.argv[1:]];runpy.run_path(sys.argv[0],run_name='__main__')
