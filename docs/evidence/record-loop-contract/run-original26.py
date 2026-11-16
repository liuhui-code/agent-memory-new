import json,subprocess,sys,tempfile,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];protocol=json.loads((D/'original26-final-protocol.json').read_text())
case=ROOT/protocol['case_file'];assert hashlib.sha256(case.read_bytes()).hexdigest()==protocol['case_file_sha256']
source=ROOT/'docs/eval/fixtures/system-capability'
assert {str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()}==protocol['source_hashes']
assert not(D/'original26-final.json').exists()
with tempfile.TemporaryDirectory(prefix='record-loop-original26-')as temp:
 project=Path(temp)/'manager';project.mkdir();home=Path(temp)/'memory'
 def cli(*args):
  cmd=[sys.executable,str(ROOT/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(home)]
  r=subprocess.run(cmd,text=True,capture_output=True);assert r.returncode==0,r.stderr;return r.stdout
 cli('init')
 result=json.loads(cli('eval-context-capability','--cases',str(case),'--source',str(source),'--case-id','context-shared-record-aggregation-owner','--json'))
 (D/'original26-final.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(result['summary'])
