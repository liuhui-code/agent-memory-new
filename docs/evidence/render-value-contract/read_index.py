# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sqlite3,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from tests.agent_memory_test_base import AgentMemoryTestBase
OUT=Path(__file__).resolve().parent;b=AgentMemoryTestBase()
for variant in ('consumed','discarded'):
 sources=json.loads((OUT/(variant+'.json')).read_text())['sources']
 with tempfile.TemporaryDirectory(prefix='render-index-') as d:
  project=Path(d)/'source';project.mkdir()
  for n,s in sources.items():(project/n).write_text(s)
  b.run_memory(project,'init');b.run_memory(project,'learn-path','--path','.','--json')
  dbs=list(b.memory_home(project).rglob('memory.db'));assert len(dbs)==1
  con=sqlite3.connect(dbs[0]);con.row_factory=sqlite3.Row
  result={t:[dict(r) for r in con.execute('select * from '+t)] for t in ('code_symbols','memory_edges')}
  (OUT/(variant+'-index.json')).write_text(json.dumps(result,indent=2))
