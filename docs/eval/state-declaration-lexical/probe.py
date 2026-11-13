# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from tests.agent_memory_test_base import AgentMemoryTestBase
p=Path('docs/eval/state-declaration-lexical'); protocol=json.loads((p/'protocol.json').read_text()); b=AgentMemoryTestBase(); results=[]
for name, source in protocol['sources'].items():
 with tempfile.TemporaryDirectory() as d:
  root=Path(d); (root/name).write_text(source); commands=[]
  for args in [('init',),('learn-path','--path','.'),('list','--type','code-symbol','--limit','100','--json')]:
   result=b.run_memory(root,*args); commands.append({'args':args,'stdout':result.stdout,'stderr':result.stderr,'returncode':result.returncode})
  symbols=json.loads(commands[-1]['stdout']); results.append({'file':name,'source':source,'commands':commands,'symbols':symbols})
(p/sys.argv[1]).write_text(json.dumps(results,ensure_ascii=False,indent=2))
