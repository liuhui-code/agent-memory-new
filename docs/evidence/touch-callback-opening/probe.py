# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tests.agent_memory_test_base import AgentMemoryTestBase
b=AgentMemoryTestBase();p=Path(__file__).parent;protocol=json.loads((p/'protocol.json').read_text())
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    for name,source in protocol['sources'].items():(root/name).write_text(source)
    b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.', '--json')
    out={'symbols':json.loads(b.run_memory(root,'list','--type','code-symbol','--limit','100','--json').stdout),'queries':{}}
    for q in protocol['queries']:
        out['queries'][q['query']]={mode:json.loads(b.run_memory(root,'context','--query',q['query'],*flags,'--json').stdout)for mode,flags in [('raw',[]),('compact',['--compact'])]}
    (p/'before.json').write_text(json.dumps(out,indent=2))
    for r in out['symbols']:
        if r.get('symbol')=='onTouch':print(r)
