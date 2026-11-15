# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(ROOT))
from tests.agent_memory_test_base import AgentMemoryTestBase
phase=sys.argv[1];p=json.loads((D/'protocol.json').read_text());b=AgentMemoryTestBase()
with tempfile.TemporaryDirectory(prefix='rebuild09-independent-')as tmp:
 project=Path(tmp)/'source';project.mkdir()
 for name,source in p['sources'].items():(project/name).write_text(source)
 setup=[]
 for args in [('init',),('learn-path','--path','.','--json')]:
  r=b.run_memory(project,*args);setup.append(dict(args=r.args,stdout=r.stdout,stderr=r.stderr))
 results=[]
 for name,q,expected in p['queries']:
  raw=json.loads(b.run_memory(project,'context','--query',q,'--json').stdout)
  compact=json.loads(b.run_memory(project,'context','--query',q,'--compact','--json').stdout)
  paths={a['file_path']for a in compact['query_handoff']['code_anchors']}
  results.append(dict(name=name,query=q,expected=expected,paths=sorted(paths),passed=paths==set(expected),raw=raw,compact=compact))
 (D/(phase+'-independent.json')).write_text(json.dumps(dict(setup=setup,results=results),ensure_ascii=False,indent=2))
 print(phase,'independent',[(r['name'],r['passed'],r['paths'])for r in results],flush=True)
with tempfile.TemporaryDirectory(prefix='rebuild09-original-')as tmp:
 project=Path(tmp)/'manager';project.mkdir();home=Path(tmp)/'memory'
 def cli(*args):return subprocess.run([sys.executable,str(ROOT/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(home)],capture_output=True,text=True,check=True).stdout
 cli('init')
 r=json.loads(cli('eval-context-capability','--cases',str(ROOT/'docs/eval/system-capability-cases.json'),'--source',str(ROOT/'docs/eval/fixtures/system-capability'),'--case-id',p['original_case'],'--json'))
 (D/(phase+'-original09.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2));print(phase,'original',r['summary'],flush=True)
