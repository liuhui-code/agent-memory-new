from copy import deepcopy
import json,tempfile
from pathlib import Path
from unittest.mock import patch
from tests.archive_create_write_test_support import cli,snapshot_database,restore_database
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
D=Path(__file__).resolve().parent/'fixtures'
P=json.loads((D/'command_table.json').read_text());Q=P['cases'][0]['query']

def prepare(root,cohort='single',sources=None):
 source=Path(root)/'source';source.mkdir()
 for name,text in (sources or P['cohorts'][cohort]['sources']).items():(source/name).write_text(text)
 project=resolve_project(str(source),str(Path(root)/'memory'));cli(project,'init');cli(project,'learn-path','--path','.','--json')
 return project

def ordinary(project,query=Q):
 pools=[]
 def capture(_p,_q,baseline,pool):pools.append(deepcopy(pool));return baseline
 with patch('tools.agent_memory_runtime.query_command_table_selection.bind_command_table_context',side_effect=capture):
  raw=build_context_facade(project).execute(query);compact=compact_context(raw)
 assert len(pools)==1
 return deepcopy(dict(raw)),compact,pools[0]
