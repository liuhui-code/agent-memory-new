# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parents[2]))
from tests.agent_memory_test_base import AgentMemoryTestBase
p=json.loads((D/(sys.argv[2] if len(sys.argv)>2 else 'protocol.json')).read_text());b=AgentMemoryTestBase();out={}
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)/'source';root.mkdir()
 for name,source in p['sources'].items():(root/name).write_text(source)
 b.run_memory(root,'init')
 out['entry']=json.loads(b.run_memory(root,'learn-entry','--entry',p['entry'],'--depth',str(p['depth']),'--json').stdout)
 out['files']=json.loads(b.run_memory(root,'list','--type','code-file','--limit','100','--json').stdout)
 out['edges']=json.loads(b.run_memory(root,'list','--type','memory-edge','--limit','100','--json').stdout)
 out['context']=json.loads(b.run_memory(root,'context','--query',p['query'],'--json').stdout)
 out['pass']=out['entry']['files']==p['expected_files']
 # Separate memory archive, same sources, depth=0 must not follow anything.
 mem=Path(tmp)/'zero-memory';b.run_memory(root,'init',memory_home=mem)
 out['depth_zero']=json.loads(b.run_memory(root,'learn-entry','--entry',p['entry'],'--depth','0','--json',memory_home=mem).stdout)
(D/sys.argv[1]).write_text(json.dumps(out,indent=2))
print(out['entry']['files'],out['pass']);print(out['depth_zero']['files'])
