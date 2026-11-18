from pathlib import Path
import runpy,sys
r=Path(__file__).resolve().parent.parent/'repo';sys.path.insert(0,str(r/'tools'))
import agent_memory_runtime.context_sql_reading as sql
sql.append_sql_reading=lambda project,original,payload:payload
sys.argv=[str(r/'tools/agent_memory.py'),*sys.argv[1:]];runpy.run_path(sys.argv[0],run_name='__main__')
