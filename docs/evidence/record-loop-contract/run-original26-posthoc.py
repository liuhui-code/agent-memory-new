import json,subprocess,sys,tempfile,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=Path('/workspace/scratch/dcdb41e16594/record-loop-attribution-base');protocol=json.loads((D/'original26-final-protocol.json').read_text())
case=ROOT/protocol['case_file'];assert hashlib.sha256(case.read_bytes()).hexdigest()==protocol['case_file_sha256']
source=ROOT/'docs/eval/fixtures/system-capability'
assert {str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()}==protocol['source_hashes']
assert not(D/'original26-posthoc-base.json').exists()
(D/'original26-posthoc-environment.json').write_text(json.dumps({'baseline_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'clean_status':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),'python':sys.executable,'cwd':str(ROOT),'cli':str(ROOT/'tools/agent_memory.py'),'kind':'posthoc attribution, not prospective before'},indent=2)+'\n')
with tempfile.TemporaryDirectory(prefix='record-loop-posthoc-base-')as temp:
 project=Path(temp)/'manager';project.mkdir();home=Path(temp)/'memory'
 def cli(*args):
  cmd=[sys.executable,str(ROOT/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(home)]
  r=subprocess.run(cmd,text=True,capture_output=True,cwd=ROOT,env={k:v for k,v in __import__('os').environ.items() if k!='PYTHONPATH'});assert r.returncode==0,r.stderr;return r.stdout
 cli('init')
 result=json.loads(cli('eval-context-capability','--cases',str(case),'--source',str(source),'--case-id','context-shared-record-aggregation-owner','--json'))
 (D/'original26-posthoc-base.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(result['summary'])
