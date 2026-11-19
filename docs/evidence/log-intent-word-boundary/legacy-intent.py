import sys,runpy,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent.parent/'repo';sys.path.insert(0,str(R/'tools'))
import agent_memory_runtime.query_intent_contract as q
source=(Path(__file__).resolve().parent/'legacy-intent-function.py').read_text();exec(source,q.__dict__)
sys.argv=[str(R/'tools/agent_memory.py'),*sys.argv[1:]];runpy.run_path(sys.argv[0],run_name='__main__')
