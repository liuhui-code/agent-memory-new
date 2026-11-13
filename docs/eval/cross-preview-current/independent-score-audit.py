# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Read-only runtime tracing of the already frozen natural query, no new queries."""
import json, os, subprocess, sys, tempfile
from pathlib import Path
D=Path('docs/eval/cross-preview-current').resolve()
for protocol in ['independent-protocol.json','prop-equivalence-protocol.json']:
 p=json.loads((D/protocol).read_text()); label=protocol.removesuffix('-protocol.json')
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp)/'source';root.mkdir()
  for name,text in p['sources'].items():(root/name).write_text(text)
  def call(*args,trace=False):
   env=dict(os.environ,TRACE_FILE=str(D/(label+'-score-trace.json')))
   cli=D/'graph-trace-cli.py' if trace else Path('tools/agent_memory.py').resolve()
   r=subprocess.run([sys.executable,str(cli),*args,'--project',str(root),'--memory-home',tmp+'/memory'],capture_output=True,text=True,check=True,env=env)
   return json.loads(r.stdout) if '--json' in args else r.stdout
  call('init');call('learn-path','--path','.')
  result=call('context','--query',p['queries'][0]['text'],'--json',trace=True)
  (D/(label+'-score-public.json')).write_text(json.dumps(result,indent=2))
