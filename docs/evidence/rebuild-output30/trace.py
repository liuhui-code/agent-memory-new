import json,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.storage import resolve_project,connect
from tools.agent_memory_runtime.query_collect import collect_matches_with_audit
from tools.agent_memory_runtime.query_output_loop_selection import qualify_output_loop
p=Path(__file__).parent;spec=json.loads((p/'independent-protocol.json').read_text());b=AgentMemoryTestBase()
with tempfile.TemporaryDirectory()as d:
 root=Path(d)
 for name,source in spec['sources'].items():(root/name).write_text(source)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 project=resolve_project(str(root),str(b.memory_home(root)));q=spec['queries'][0]['query'];items=collect_matches_with_audit(project,q).matches['wiki_matches']
 with connect(project)as conn:rows=[dict(r)for r in conn.execute('SELECT * FROM code_symbols')];files=[dict(r)for r in conn.execute('SELECT * FROM code_files')]
 (p/'trace.json').write_text(json.dumps(dict(items=items,rows=rows,files=files),indent=2))
 print([(x['kind'],x['file_path'])for x in items]);print([(x['symbol'],x['semantic_adapter'],x['start_line'],x['end_line'])for x in rows]);print(qualify_output_loop(project,q,items))
