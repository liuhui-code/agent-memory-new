# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
s=json.loads((ROOT/'docs/evidence/initializer-scope-current/protocol.json').read_text())['scenarios'][2]
with tempfile.TemporaryDirectory(prefix='nested-raw-') as d:
 p=Path(d)/'source';p.mkdir()
 for n,v in s['sources'].items():(p/n).write_text(v)
 def run(*a):
  r=subprocess.run(['python',str(ROOT/'tools/agent_memory.py'),*a,'--project',str(p),'--memory-home',d+'/memory'],text=True,capture_output=True,check=True)
  return json.loads(r.stdout) if '--json' in a else r.stdout
 result={'setup':[run('init'),run('learn-path','--path','.')],'public':run('context','--query',s['queries'][1],'--json')}
 (OUT/'declared-discard-raw.json').write_text(json.dumps(result,indent=2))
