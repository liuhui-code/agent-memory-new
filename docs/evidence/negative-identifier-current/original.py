# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,tempfile
from pathlib import Path
OUT=Path(__file__).resolve().parent;root=Path(sys.argv[1]);phase=sys.argv[2]
with tempfile.TemporaryDirectory(prefix='negative-original-') as d:
 manager=Path(d)/'manager';manager.mkdir();home=Path(d)/'memory'
 def cli(*a):
  p=subprocess.run([sys.executable,str(root/'tools/agent_memory.py'),*a,'--project',str(manager),'--memory-home',str(home)],text=True,capture_output=True,check=True);return p.stdout
 cli('init')
 result=json.loads(cli('eval-context-capability','--cases',str(root/'docs/eval/system-capability-cases.json'),'--source',str(root/'docs/eval/fixtures/system-capability'),'--case-id','context-arkts-ui-operation-owner','--json'))
 (OUT/(phase+'-original.json')).write_text(json.dumps(result,indent=2))
 print(phase,result['summary'])
