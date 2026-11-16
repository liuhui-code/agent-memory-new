"""Self-contained synthetic inputs; produce fresh ordinary data, never saved traces."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from unittest.mock import patch
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.storage import resolve_project

ROOT=Path(__file__).resolve().parents[1]

def fixture():
    return json.loads((ROOT/'tests/fixtures/archive_create_write.json').read_text())

def cli(project,*args):
    command=[sys.executable,str(ROOT/'tools/agent_memory.py'),*args,
             '--project',str(project.root),'--memory-home',str(project.memory_home)]
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    if result.returncode:
        raise AssertionError(f'CLI failed: {command!r}\n{result.stdout}\n{result.stderr}')
    return result.stdout

def prepare(root,cohort):
    source=Path(root)/'source';source.mkdir()
    for name,text in fixture()['cohorts'][cohort]['sources'].items():
        (source/name).write_bytes(text.encode('utf-8'))
    project=resolve_project(str(source),str(Path(root)/'memory'))
    cli(project,'init');cli(project,'learn-path','--path','.','--json')
    return project

def ordinary_context(project,query):
    pools=[]
    def ordinary(_project,_query,baseline,pool):
        pools.append(deepcopy(pool))
        return baseline
    with patch('tools.agent_memory_runtime.query_archive_create_write_selection.bind_archive_create_write_context',side_effect=ordinary):
        raw=build_context_facade(project).execute(query)
        compact=compact_context(raw)
    if len(pools)!=1:
        raise AssertionError(f'Expected one original archive binding boundary, got {len(pools)}')
    return deepcopy(dict(raw)),deepcopy(compact),pools[0]

def snapshot_database(project):
    saved=sqlite3.connect(':memory:')
    with sqlite3.connect(project.db_path) as connection:
        connection.backup(saved)
    return saved

def restore_database(project,saved):
    with sqlite3.connect(project.db_path) as connection:
        saved.backup(connection)
