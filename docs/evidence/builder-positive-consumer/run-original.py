# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2]
with tempfile.TemporaryDirectory(prefix='builder-consumer-original-')as temp:
 project=Path(temp)/'manager';project.mkdir();home=Path(temp)/'memory'
 def cli(*args):return subprocess.run([sys.executable,str(ROOT/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(home)],capture_output=True,text=True,check=True).stdout
 cli('init')
 result=json.loads(cli('eval-context-capability','--cases',str(ROOT/'docs/eval/system-capability-cases.json'),'--source',str(ROOT/'docs/eval/fixtures/system-capability'),'--case-id','context-builder-layout-source-focus','--json'))
 (D/'final842-original23.json').write_text(json.dumps(result,indent=2,ensure_ascii=False));print(result['summary'])
