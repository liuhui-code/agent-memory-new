# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import hashlib,json,sqlite3,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tests.agent_memory_test_base import AgentMemoryTestBase
OUT=Path(__file__).resolve().parent
protocol=json.loads((ROOT/'docs/eval/owner-audit-current/render-protocol.json').read_text())
b=AgentMemoryTestBase(); reports=[]
for variant in ('consumed','discarded'):
 with tempfile.TemporaryDirectory(prefix='render-value-') as d:
  project=Path(d)/'source';project.mkdir()
  sources=dict(protocol['sources'])
  if variant=='discarded':
   sources['MessageSurface.ets']=sources['MessageSurface.ets'].replace('Column() { Text(this.plainBody()) }','this.plainBody(); Column() { Text(this.content) }')
  for name,source in sources.items():(project/name).write_text(source)
  setup=[]
  for args in [('init',),('learn-path','--path','.','--json')]:
   r=b.run_memory(project,*args);setup.append({'args':r.args,'stdout':r.stdout,'stderr':r.stderr})
  results=[]
  for name,q,required,excluded in protocol['queries'][:4 if variant=='consumed' else 1]:
   raw=json.loads(b.run_memory(project,'context','--query',q,'--json').stdout)
   compact=json.loads(b.run_memory(project,'context','--query',q,'--compact','--json').stdout)
   paths=[a['file_path'] for a in compact['query_handoff']['code_anchors']]
   results.append({'name':name,'query':q,'paths':paths,'frozen_oracle_pass':set(required)<=set(paths) and not set(excluded)&set(paths) if variant=='consumed' else None,'raw':raw,'compact':compact})
  dbs=list(b.memory_home(project).rglob('memory.db'));assert len(dbs)==1
  con=sqlite3.connect(dbs[0]);con.row_factory=sqlite3.Row
  tables={row[0] for row in con.execute("select name from sqlite_master where type='table'")}
  records={t:[dict(r) for r in con.execute('select * from '+t)] for t in sorted(tables) if t in {'records','edges'}}
  report={'variant':variant,'sources':sources,'sha256':{n:hashlib.sha256(s.encode()).hexdigest() for n,s in sources.items()},'setup':setup,'results':results,'database':records}
  (OUT/(variant+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
  print(variant,[(r['name'],r['paths'],r['frozen_oracle_pass']) for r in results], 'tables',tables)
